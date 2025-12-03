from flask import Flask, render_template, request, jsonify, send_file, abort
import os
from werkzeug.utils import secure_filename
from PIL import Image, ImageFilter

app = Flask(__name__)

# ----------------------------------------------------------------------
# IN-MEMORY TOTE STATE
# ----------------------------------------------------------------------
TOTES = {}

LABEL_DIR = os.path.join(app.root_path, "labels")
os.makedirs(LABEL_DIR, exist_ok=True)

# ----------------------------------------------------------------------
# DISPLAY CONFIG PER TOTE
#   - Edit this mapping based on which tote uses which panel.
#   - 4.2" V2 : 400 x 300
#   - 7.5" V2 : 800 x 480
# ----------------------------------------------------------------------
DISPLAY_CONFIG = {
    "TOTE001": (400, 300),  # 4.2" V2 example
    "TOTE002": (800, 480),  # 7.5" V2 example
    # Add more:
    # "TOTE003": (800, 480),
    # "TOTE004": (400, 300),
}


def get_display_size_for_tote(tote_id: str):
    """Return (width, height) for this tote's display."""
    return DISPLAY_CONFIG.get(tote_id, (400, 300))  # default 4.2" if unknown


# ----------------------------------------------------------------------
# STATUS COMPUTATION
# ----------------------------------------------------------------------
def compute_status(temp, humidity, lux):
    try:
        if temp is not None:
            t = float(temp)
            if t < -5 or t > 60:
                return "critical"
            if t < 0 or t > 25:
                return "warning"

        if humidity is not None:
            h = float(humidity)
            if h > 90:
                return "critical"
            if h > 70:
                return "warning"

        if lux is not None:
            lx = float(lux)
            if lx > 1000:
                return "critical"
            if lx >= 300:
                return "warning"

        return "normal"

    except Exception:
        return "normal"


# ----------------------------------------------------------------------
# DASHBOARD
# ----------------------------------------------------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ----------------------------------------------------------------------
# DEVICE UPDATE API
# ----------------------------------------------------------------------
@app.route("/api/iot/update", methods=["POST"])
def iot_update():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "invalid JSON"}), 400

    tote_id = data.get("tote_id") or data.get("id")
    if not tote_id:
        return jsonify({"error": "tote_id is required"}), 400

    temp = data.get("temperature")
    humidity = data.get("humidity")
    lux = data.get("lux")

    loc = data.get("location", {}) or {}
    lat = loc.get("lat")
    lon = loc.get("lon")

    location_label = data.get("location_label") or "Unknown"
    status = data.get("status") or compute_status(temp, humidity, lux)

    TOTES[tote_id] = {
        "id": tote_id,
        "name": tote_id,
        "temp": temp,
        "humidity": humidity,
        "lux": lux,
        "status": status,
        "location": location_label,
        "coords": f"{lat},{lon}" if lat is not None and lon is not None else ""
    }

    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# LIVE DATA FOR DASHBOARD
# ----------------------------------------------------------------------
@app.route("/iot/live")
def live():
    return jsonify(TOTES)


# ----------------------------------------------------------------------
# IMAGE PREP HELPERS
# ----------------------------------------------------------------------
def fit_and_sharpen_for_display(img: Image.Image, target_w: int, target_h: int):
    """
    - Keep aspect ratio
    - Letterbox into target_w x target_h
    - Convert to grayscale
    - Apply a light sharpen
    """
    # Ensure RGB first
    img = img.convert("RGB")
    src_w, src_h = img.size

    # Compute scale to fit inside target while keeping aspect
    scale = min(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    # High quality resize
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Create white canvas and center the resized image
    canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    canvas.paste(img_resized, (offset_x, offset_y))

    # Grayscale + sharpen a bit
    gray = canvas.convert("L")
    gray = gray.filter(ImageFilter.SHARPEN)

    return canvas, gray


def to_1bit_bmp(gray_img: Image.Image, threshold: int = 180):
    """
    Convert grayscale image to crisp 1-bit black/white using a fixed threshold.
    """
    bw = gray_img.point(lambda x: 0 if x < threshold else 255, mode="1")
    return bw


# ----------------------------------------------------------------------
# LABEL UPLOAD (PNG + 1-BIT BMP PER DISPLAY RESOLUTION)
# ----------------------------------------------------------------------
@app.route("/upload_label/<tote_id>", methods=["POST"])
def upload_label(tote_id):

    if "file" not in request.files:
        return jsonify({"error": "file missing"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    filename_png = secure_filename(f"{tote_id}.png")
    filename_bmp = secure_filename(f"{tote_id}.bmp")

    path_png = os.path.join(LABEL_DIR, filename_png)
    path_bmp = os.path.join(LABEL_DIR, filename_bmp)

    target_w, target_h = get_display_size_for_tote(tote_id)

    try:
        img = Image.open(file.stream)

        # Prepare images for this tote's display
        canvas_rgb, canvas_gray = fit_and_sharpen_for_display(img, target_w, target_h)

        # Save PNG preview for dashboard
        canvas_rgb.save(path_png, format="PNG")

        # Make crisp 1-bit BMP for e-ink
        bw_1bit = to_1bit_bmp(canvas_gray)
        bw_1bit.save(path_bmp, format="BMP")

    except Exception as exc:
        print("Error converting label:", exc)
        file.seek(0)
        file.save(path_png)

    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# FETCH PNG FOR DASHBOARD
# ----------------------------------------------------------------------
@app.route("/label/<tote_id>.png")
def get_label(tote_id):
    path = os.path.join(LABEL_DIR, f"{tote_id}.png")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/png")


# ----------------------------------------------------------------------
# ESP32: IMAGE METADATA (WITH VERSIONING)
# ----------------------------------------------------------------------
@app.route("/api/tote/<tote_id>/image", methods=["GET"])
def api_tote_image(tote_id):
    bmp_path = os.path.join(LABEL_DIR, f"{tote_id}.bmp")

    if not os.path.exists(bmp_path):
        return jsonify({"update_available": False, "image_url": ""})

    version = int(os.path.getmtime(bmp_path))
    base = request.url_root.rstrip("/")
    rel = f"/label_raw/{tote_id}.bmp?v={version}"

    return jsonify({
        "update_available": True,
        "image_url": base + rel
    })


# ----------------------------------------------------------------------
# ESP32: FETCH RAW BMP (1-BIT, CORRECT SIZE)
# ----------------------------------------------------------------------
@app.route("/label_raw/<tote_id>.bmp")
def get_label_raw(tote_id):
    path = os.path.join(LABEL_DIR, f"{tote_id}.bmp")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/bmp")


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
