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
    """
    Simple server-side safeguard so even if device doesn't send a status,
    we can derive one from the sensor values.
    """
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
    """
    This is the ONLY API your tote/device needs to call.
    Example JSON from device / update_data.py:

    {
      "tote_id": "TOTE001",
      "temperature": 23.5,
      "humidity": 55,
      "lux": 120,
      "status": "normal",   # optional – server can compute
      "location": {
        "lat": 12.9716,
        "lon": 77.5946
      },
      "location_label": "Bengaluru Warehouse A",  # optional
      "timestamp": 1733202321
    }
    """
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "invalid JSON"}), 400

    tote_id = data.get("tote_id") or data.get("id")
    if not tote_id:
        return jsonify({"error": "tote_id is required"}), 400

    # Extract values
    temp = data.get("temperature")
    humidity = data.get("humidity")
    lux = data.get("lux")

    # Location block from device
    loc_block = data.get("location", {}) or {}
    lat = loc_block.get("lat")
    lon = loc_block.get("lon")

    # Optional human-friendly label from device
    location_label = data.get("location_label") or "Unknown"

    # Device may send its own status; otherwise compute
    status = data.get("status") or compute_status(temp, humidity, lux)

    # Build one consolidated record used by the dashboard + map
    TOTES[tote_id] = {
        "id": tote_id,
        "name": tote_id,
        "temp": temp,
        "humidity": humidity,
        "lux": lux,
        "status": status,
        "location": location_label,
        # map uses this "lat,lon" string
        "coords": f"{lat},{lon}" if lat is not None and lon is not None else ""
    }

    return jsonify({"ok": True})


# ---------------------------
# API: Dashboard GET live data
# ---------------------------
@app.route("/iot/live")
def live():
    """
    Used by dashboard.js to render:
      - KPI cards
      - Tote cards
      - Map markers
    """
    return jsonify(TOTES)


# ---------------------------
# LABEL UPLOAD
# ---------------------------
@app.route("/upload_label/<tote_id>", methods=["POST"])
def upload_label(tote_id):
    """Upload a label image for a tote.

    - Saves a PNG version for the web dashboard at /label/<tote_id>.png
    - Saves a BMP version for ESP32 clients at   /label_raw/<tote_id>.bmp
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
        # Normalize and convert to RGB so we have a clean base image
        img = Image.open(file.stream)
        img = img.convert("RGB")

        # Save PNG for the dashboard / browser
        img.save(path_png, format="PNG")

        # Save BMP (uncompressed) for ESP32 side to decode easily
        img.save(path_bmp, format="BMP")
    except Exception as exc:
        # Fallback: just save what we got as PNG
        file.seek(0)
        file.save(path_png)

    return jsonify({"ok": True})


# ---------------------------
# LABEL FETCH
# ---------------------------
@app.route("/label/<tote_id>.png")
def get_label(tote_id):
    path = os.path.join(LABEL_DIR, f"{tote_id}.png")
    if not os.path.exists(path):
        abort(404)

    return send_file(path, mimetype="image/png")

# ---------------------------
# API: Tote image for ESP32 clients
# ---------------------------
@app.route("/api/tote/<tote_id>/image", methods=["GET"])
def api_tote_image(tote_id):
    """Small JSON for ESP32 clients.

    Returns whether a label image exists for this tote and, if so,
    an absolute URL to a BMP image that the ESP32 can download.
    """
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
    # For local testing
    app.run(debug=True)
