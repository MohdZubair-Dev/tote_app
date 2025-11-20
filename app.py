from flask import Flask, render_template, request, jsonify, send_file, abort
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Store live tote data
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

    except:
        return "normal"


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

    # Extract values
    temp = data.get("temperature")
    humidity = data.get("humidity")
    lux = data.get("lux")

    loc_block = data.get("location", {})
    lat = loc_block.get("lat")
    lon = loc_block.get("lon")
    location_label = data.get("location_label") or "Unknown"

    # Compute server-side status
    status = compute_status(temp, humidity, lux)

    TOTES[tote_id] = {
        "id": tote_id,
        "name": tote_id,
        "temp": temp,
        "humidity": humidity,
        "lux": lux,
        "status": status,
        "location": location_label,
        "coords": f"{lat},{lon}" if lat and lon else ""
    }

    return jsonify({"ok": True})


# ---------------------------
# API: Dashboard GET live data
# ---------------------------
@app.route("/iot/live")
def live():
    return jsonify(TOTES)


# ---------------------------
# LABEL UPLOAD
# ---------------------------
@app.route("/upload_label/<tote_id>", methods=["POST"])
def upload_label(tote_id):
    if "file" not in request.files:
        return jsonify({"error": "file missing"}), 400

    f = request.files["file"]
    filename = secure_filename(f"{tote_id}.png")
    path = os.path.join(LABEL_DIR, filename)
    f.save(path)
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


if __name__ == "__main__":
    app.run(debug=True)
