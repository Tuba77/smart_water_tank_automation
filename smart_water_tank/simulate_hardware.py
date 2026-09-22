"""
Smart Water Tank — Simulated Hardware (stand-in for the ESP32)
----------------------------------------------------------------
Mimics the BMP280 (pressure) + ultrasonic (level) sensors described in the
components list, and posts readings to the Flask backend exactly the way a
real ESP32 would over WiFi. When the real hardware is ready, this script is
replaced by Arduino/C++ firmware doing an HTTP POST to the same endpoint —
nothing on the backend or dashboard side needs to change.

Run this alongside app.py:
    python simulate_hardware.py
"""

import time
import random
import requests

BACKEND_URL = "http://127.0.0.1:5000/api/reading"
SEND_INTERVAL_SECONDS = 2

# --- simulated tank physics -------------------------------------------------
# Level drifts down (consumption/demand) and gets refilled when the pump
# kicks on, instead of pure random jitter, so the trend on the dashboard
# actually looks like a tank behaving.
state = {
    "level": 70.0,       # start at 70%
    "pump_on": False,
}

PUMP_ON_BELOW = 30.0
PUMP_OFF_ABOVE = 90.0
DRAIN_RATE = 0.6         # % per tick when pump is off (demand/usage)
FILL_RATE = 2.2          # % per tick when pump is on (refilling)

ANOMALY_CHANCE = 0.04    # ~4% of ticks simulate a leak/blockage/spike


def next_level():
    if state["level"] < PUMP_ON_BELOW:
        state["pump_on"] = True
    elif state["level"] > PUMP_OFF_ABOVE:
        state["pump_on"] = False

    if state["pump_on"]:
        state["level"] += FILL_RATE + random.uniform(-0.3, 0.3)
    else:
        state["level"] -= DRAIN_RATE + random.uniform(-0.2, 0.2)

    state["level"] = max(0.0, min(100.0, state["level"]))
    return state["level"]


def next_pressure(level, anomaly):
    # Pressure roughly tracks level + pump activity, plus sensor noise.
    base = 20 + (level * 0.45)
    if state["pump_on"]:
        base += 8

    if anomaly == "spike":
        base += random.uniform(25, 45)       # e.g. blockage
    elif anomaly == "drop":
        base -= random.uniform(15, 25)       # e.g. leak

    noise = random.uniform(-2.5, 2.5)
    return max(0.0, min(100.0, base + noise))


def maybe_anomaly():
    if random.random() < ANOMALY_CHANCE:
        return random.choice(["spike", "drop"])
    return None


def main():
    print(f"Simulated ESP32 sending readings to {BACKEND_URL}")
    print("Ctrl+C to stop.\n")

    while True:
        anomaly = maybe_anomaly()
        level = next_level()
        pressure = next_pressure(level, anomaly)
        pump_status = "ON" if state["pump_on"] else "OFF"

        payload = {
            "level": round(level, 2),
            "pressure": round(pressure, 2),
            "pump_status": pump_status,
        }

        try:
            res = requests.post(BACKEND_URL, json=payload, timeout=3)
            tag = f" [{anomaly.upper()}]" if anomaly else ""
            print(f"level={payload['level']:5.1f}%  pressure={payload['pressure']:5.1f}PSI  "
                  f"pump={pump_status}{tag}  -> {res.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Could not reach backend ({e}). Is app.py running?")

        time.sleep(SEND_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
