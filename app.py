from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import time

app = Flask(__name__)

# Store live IoT data here
live_data = {}


@app.route("/")
def home():
    return render_template("dashboard.html")


# -------------------------------
# LABEL IMAGE
# -------------------------------
@app.route("/label/<tote_png>")
def label_image(tote_png):
    labels_dir = os.path.join(app.static_folder, "labels")
    full_path = os.path.join(labels_dir, tote_png)

    # Serve uploaded label or 404
    if os.path.exists(full_path):
        return send_from_directory(labels_dir, tote_png)
    return ("", 404)


# -------------------------------
# UPLOAD LABEL
# -------------------------------
@app.route("/upload_label/<tote_id>", methods=["POST"])
def upload_label(tote_id):
    if "file" not in request.files:
        return {"message": "No file in request"}, 400

    file = request.files["file"]
    if file.filename == "":
        return {"message": "No file selected"}, 400

    os.makedirs("static/labels", exist_ok=True)
    file.save(f"static/labels/{tote_id}.png")

    return {"message": "Upload successful"}


# -------------------------------
# IOT UPDATE (DEVICE → SERVER)
# -------------------------------
@app.route("/iot/update", methods=["POST"])
def iot_update():
    data = request.json or {}
    tote_id = data.get("tote_id")

    if not tote_id:
        return {"error": "missing tote_id"}, 400

    live_data[tote_id] = {
        "temperature": data.get("temperature"),
        "lux": data.get("lux"),
        "battery": data.get("battery", 100),
        "status": data.get("status", "normal"),
        "location": data.get("location", {}),
        "timestamp": data.get("timestamp", time.time())
    }

    return {"message": "OK"}


# -------------------------------
# DASHBOARD REQUESTS LIVE DATA
# -------------------------------
@app.route("/iot/live")
def iot_live():
    return jsonify(live_data)


if __name__ == "__main__":
    app.run(debug=True)
