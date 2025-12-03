import requests
import random
import time

#API = "https://tote-app.onrender.com/api/iot/update"
API = "http://127.0.0.1:5000/api/iot/update"
TOTE_ID = "TOTE001"

def random_payload():
    temperature = round(random.uniform(21, 23), 1)
    humidity    = round(random.uniform(20, 95), 1)
    lux         = random.randint(0, 1200)

    # Random movement in a 0.02° box
    lat = round(12.9716 + random.uniform(-0.02, 0.02), 6)
    lon = round(77.5946 + random.uniform(-0.02, 0.02), 6)

    return {
        "tote_id": TOTE_ID,

        # core sensors
        "temperature": temperature,
        "humidity": humidity,
        "lux": lux,

        # location block
        "location": {
            "lat": lat,
            "lon": lon
        },

        # readable label
        "location_label": "BLR Warehouse – Section A3",

        # optional timestamp
        "timestamp": time.time()
    }

while True:
    data = random_payload()
    try:
        r = requests.post(API, json=data)
        print("Sent:", data)
        print("Response:", r.status_code, r.text)
    except Exception as e:
        print("Error:", e)

    time.sleep(5)
