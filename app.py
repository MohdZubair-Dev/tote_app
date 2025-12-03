from flask import Flask, render_template, request, jsonify, send_file, abort
import os
from werkzeug.utils import secure_filename
from PIL import Image, ImageFilter
import time

app = Flask(__name__)

# ----------------------------------------------------------------------
# IN-MEMORY TOTE STATE
# ----------------------------------------------------------------------
TOTES = {}

LABEL_DIR = os.path.join(app.root_path, "labels")
os.makedirs(LABEL_DIR, exist_ok=True)

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
# DASHBOARD PAGE
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
        return jsonify({"error": "tote_id missing"}), 400

    temperature = data.get("temperature")
    humidity    = data.get("humidity")
    lux         = data.get("lux")

    loc         = data.get("location", {})
    lat = loc.get("lat")
    lon = loc.get("lon")

    timestamp = data.get("timestamp") or int(time.time())
    status    = compute_status(temperature, humidity, lux)

    # Store EXACTLY the structure dashboard expects
    TOTES[tote_id] = {
        "id": tote_id,
        "name": tote_id,
        "temperature": temperature,
        "humidity": humidity,
        "lux": lux,
        "status": status,
        "location": {
            "lat": lat,
            "lon": lon
        },
        "timestamp": timestamp
    }

    return jsonify({"ok": True, "updated": TOTES[tote_id]})


# ----------------------------------------------------------------------
# DASHBOARD LIVE DATA
# ----------------------------------------------------------------------
@app.route("/iot/live")
def live():
    return jsonify(TOTES)


# ----------------------------------------------------------------------
# E-INK IMAGE CODE (unchanged)
# ----------------------------------------------------------------------
def fit_and_sharpen(img, target_w, target_h):
    img = img.convert("RGB")
    src_w, src_h = img.size

    scale = min(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    resized = img.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    canvas.paste(resized, ((target_w - new_w)//2, (target_h - new_h)//2))

    gray = canvas.convert("L").filter(ImageFilter.SHARPEN)
    return gray


def to_1bit(gray_img, threshold):
    return gray_img.point(lambda x: 0 if x < threshold else 255, "1")


@app.route("/upload_label/<tote_id>", methods=["POST"])
def upload_label(tote_id):
    if "file" not in request.files:
        return jsonify({"error": "file missing"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    path_png     = os.path.join(LABEL_DIR, f"{tote_id}.png")
    path_4in2bmp = os.path.join(LABEL_DIR, f"{tote_id}_4in2.bmp")
    path_7in5bmp = os.path.join(LABEL_DIR, f"{tote_id}_7in5.bmp")

    try:
        img = Image.open(file.stream)
        img.convert("RGB").save(path_png, "PNG")

        TARGETS = [
            ("4in2", 400, 300, 180, path_4in2bmp),
            ("7in5", 800, 480, 170, path_7in5bmp),
        ]

        for _, W, H, THRESH, outpath in TARGETS:
            gray = fit_and_sharpen(img, W, H)
            bw   = to_1bit(gray, THRESH)
            bw.save(outpath, "BMP")

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"ok": True})


@app.route("/label/<tote_id>.png")
def get_label_png(tote_id):
    path = os.path.join(LABEL_DIR, f"{tote_id}.png")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/png")


@app.route("/api/tote/<tote_id>/image", methods=["GET"])
def api_tote_image(tote_id):
    bmp_path = os.path.join(LABEL_DIR, f"{tote_id}.bmp")

    if not os.path.exists(bmp_path):
        return jsonify({
            "update_available": False,
            "image_url": "",
            "version": ""
        })

    # Version = last modified timestamp
    version = str(int(os.path.getmtime(bmp_path)))

    base = request.url_root.rstrip("/")
    rel = f"/label_raw/{tote_id}.bmp"

    return jsonify({
        "update_available": True,
        "image_url": base + rel + f"?v={version}",
        "version": version
    })


@app.route("/label_raw/<filename>")
def get_raw_bmp(filename):
    path = os.path.join(LABEL_DIR, filename)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/bmp")


if __name__ == "__main__":
    app.run(debug=True)
