from flask import Flask, render_template, request, jsonify, send_file, abort
import os
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps, ImageEnhance
from datetime import datetime

app = Flask(__name__)

# ---------------------------
# STORAGE CONFIG
# ---------------------------
TOTES = {}  # live data
LABEL_DIR = os.path.join(app.root_path, "labels")
os.makedirs(LABEL_DIR, exist_ok=True)


# ---------------------------
# IMAGE PROCESSING
# ---------------------------
def process_image(img, size):
    # Convert to grayscale
    img = img.convert("L")

    # Increase clarity
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)

    # Resize to panel size
    img = ImageOps.fit(img, size, method=Image.LANCZOS)

    # Convert to 1-bit BW
    img = img.point(lambda x: 0 if x < 150 else 255, "1")

    return img


# ---------------------------
# DASHBOARD UI
# ---------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ---------------------------
# ESP → SERVER: LIVE UPDATE
# ---------------------------
@app.route("/api/iot/update", methods=["POST"])
def iot_update():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "invalid JSON"}), 400

    tote_id = data.get("tote_id")
    if not tote_id:
        return jsonify({"error": "tote_id missing"}), 400

    temp = data.get("temperature")
    humidity = data.get("humidity")
    lux = data.get("lux")

    loc_block = data.get("location", {})
    lat = loc_block.get("lat")
    lon = loc_block.get("lon")

    location_label = data.get("location_label", "Unknown")
    status = data.get("status", "normal")

    # SERVER REAL-TIME TIMESTAMP
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    TOTES[tote_id] = {
        "id": tote_id,
        "temperature": temp,
        "humidity": humidity,
        "lux": lux,
        "status": status,

        # For card display and map
        "location": {
            "lat": lat,
            "lon": lon,
            "label": location_label
        },

        # Backward compatibility for your card code
        "coords": f"{lat},{lon}" if lat and lon else "",

        # For "Last Updated"
        "last_updated": last_updated
    }

    return jsonify({"ok": True})


# ---------------------------
# DASHBOARD → FETCH LIVE DATA
# ---------------------------
@app.route("/iot/live")
def live():
    return jsonify(TOTES)


# ---------------------------
# UPLOAD LABEL (FOR ESP + DASHBOARD)
# ---------------------------
@app.route("/upload_label/<tote_id>", methods=["POST"])
def upload_label(tote_id):
    if "file" not in request.files:
        return jsonify({"error": "file missing"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    img = Image.open(file.stream).convert("RGB")

    # Save PNG (for dashboard)
    png_path = os.path.join(LABEL_DIR, f"{tote_id}.png")
    img.save(png_path, "PNG")

    # Save BMP for ESP
    bmp_path = os.path.join(LABEL_DIR, f"{tote_id}.bmp")

    # 800×480 for 7.5-inch ESP panels
    processed = process_image(img, (800, 480))
    processed.save(bmp_path, "BMP")

    return jsonify({"ok": True})


# ---------------------------
# SERVE LABEL PNG
# ---------------------------
@app.route("/label/<tote_id>.png")
def get_label_png(tote_id):
    path = os.path.join(LABEL_DIR, f"{tote_id}.png")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/png")


# ---------------------------
# SERVE RAW BMP FOR ESP
# ---------------------------
@app.route("/label_raw/<tote_id>.bmp")
def get_label_raw(tote_id):
    path = os.path.join(LABEL_DIR, f"{tote_id}.bmp")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/bmp")


# ---------------------------
# ESP → FETCH LATEST LABEL VERSION
# ---------------------------
@app.route("/api/tote/<tote_id>/image", methods=["GET"])
def api_tote_image(tote_id):
    bmp_path = os.path.join(LABEL_DIR, f"{tote_id}.bmp")

    if not os.path.exists(bmp_path):
        return jsonify({
            "update_available": False,
            "image_url": "",
            "version": ""
        })

    version = str(int(os.path.getmtime(bmp_path)))

    base = request.url_root.rstrip("/")
    rel = f"/label_raw/{tote_id}.bmp"

    return jsonify({
        "update_available": True,
        "image_url": base + rel + f"?v={version}",
        "version": version
    })


# ---------------------------
# RUN (LOCAL DEV ONLY)
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True)
