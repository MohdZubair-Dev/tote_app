import requests
import random
import time

API = "http://127.0.0.1:5000/iot/update"   # or your deployed API URL
TOTE_ID = "TOTE001"

def random_status(temp):
    """
    Simulate status logic:
    normal   = safe
    warning  = borderline
    critical = overheating
    """
    if temp < 10:
        return "normal"
    elif 10 <= temp < 30:
        return "warning"
    else:
        return "critical"

def random_payload():
    temp = round(random.uniform(-10, 80), 1)
    lux  = random.randint(0, 250)
    battery = random.randint(20, 100)

    return {
        "tote_id": TOTE_ID,
        "temperature": temp,
        "lux": lux,
        "battery": battery,
        "status": random_status(temp),
        "location": {
            "lat": round(40.70 + random.uniform(-0.02, 0.02), 6),
            "lon": round(-74.00 + random.uniform(-0.02, 0.02), 6)
        },
        "timestamp": time.time()
    }

while True:
    data = random_payload()
    try:
        r = requests.post(API, json=data)
        print("Sent:", data, "Response:", r.status_code)
    except Exception as e:
        print("Error:", e)

    time.sleep(5)  # send every 5 seconds
