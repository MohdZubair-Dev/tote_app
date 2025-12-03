from flask import Flask, render_template, request, jsonify, send_file, abort
import os
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)

# Store live tote data in memory (latest snapshot per tote)
TOTES = {}

LABEL_DIR = os.path.join(app.root_path, "labels")
os.makedirs(LABEL_DIR, exist_ok=True)


# ---------------------------
# HELPER: decide tote status
# ---------------------------
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


# ---------------------------
# DASHBOARD UI
# ---------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ---------------------------
# API: IoT device POST update
# ---------------------------
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

    loc_block = data.get("location", {}) or {}
    lat = loc_block.get("lat")
    lon = loc_block.get("lon")

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


# ---------------------------
# API: Dashboard GET live data
# ---------------------------
@app.route("/iot/live")
def live():
    return jsonify(TOTES)


# ---------------------------
# LABEL UPLOAD  (UPDATED!)
# ---------------------------
@app.route("/upload_label/<tote_id>", methods=["POST"])
def upload_label(tote_id):
    """
    Upload a label image for a tote.

    - Saves a PNG version for dashboard
    - Saves a *1-bit monochrome BMP* version for ESP32 e-ink display
    """
    if "file" not in request.files:
        return jsonify({"error": "file missing"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    filename_png = secure_filename(f"{tote_id}.png")
    filename_bmp = secure_filename(f"{tote_id}.bmp")

    path_png = os.path.join(LABEL_DIR, filename_png)
    path_bmp = os.path.join(LABEL_DIR, filename_bmp)

    try:
        # Load original upload
        img = Image.open(file.stream)

        # Save PNG for dashboard (full quality)
        img_rgb = img.convert("RGB")
        img_rgb.save(path_png, format="PNG")

        # ----- 1-BIT BMP FOR ESP32 -----
        # Convert image to black/white
        img_bw = img.convert("1")

        # Resize to 400x300 (4.2" V2 resolution)
        img_bw = img_bw.resize((400, 300))

        # Save as MONOCHROME BMP (1-bit)
        img_bw.save(path_bmp, format="BMP")

    except Exception as exc:
        print("Error converting label:", exc)
        # Save input for debugging
        file.seek(0)
        file.save(path_png)

    return jsonify({"ok": True})


# ---------------------------
# DASHBOARD PNG FETCH
# ---------------------------
@app.route("/label/<tote_id>.png")
def get_label(tote_id):
    path = os.path.join(LABEL_DIR, f"{tote_id}.png")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/png")


# ---------------------------
# API: ESP32 asks for label update
# ---------------------------
@app.route("/api/tote/<tote_id>/image", methods=["GET"])
def api_tote_image(tote_id):
    bmp_path = os.path.join(LABEL_DIR, f"{tote_id}.bmp")
    if not os.path.exists(bmp_path):
        return jsonify({"update_available": False, "image_url": ""})

    base = request.url_root.rstrip("/")
    rel = f"/label_raw/{tote_id}.bmp"
    return jsonify({"update_available": True, "image_url": base + rel})


# ---------------------------
# RAW BMP FETCH FOR ESP32
# ---------------------------
@app.route("/label_raw/<tote_id>.bmp")
def get_label_raw(tote_id):
    path = os.path.join(LABEL_DIR, f"{tote_id}.bmp")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="image/bmp")


if __name__ == "__main__":
    app.run(debug=True)
