"""
Smart Water Tank Automation — Backend
--------------------------------------
Receives sensor readings (from simulate_hardware.py today, a real ESP32
tomorrow — the HTTP contract is identical either way), keeps a rolling
history in memory, applies pump/status logic, and serves it all to the
dashboard.

Endpoints:
  POST /api/reading   <- sensor/simulator pushes a new reading here
  GET  /api/latest     -> most recent reading (what the dashboard polls)
  GET  /api/history     -> last N readings (for charts/log/export)
  GET  /                -> serves the dashboard itself
  GET  /health           -> simple liveness check
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from collections import deque
from datetime import datetime
import os

app = Flask(__name__, static_folder="static")
CORS(app)  # allow the dashboard to be hosted separately if needed

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HISTORY_MAXLEN = 500          # how many readings to keep in memory
LEVEL_PUMP_ON_BELOW = 30.0    # pump kicks in below this level (%)
LEVEL_PUMP_OFF_ABOVE = 90.0   # pump switches off above this level (%)

LEVEL_CRITICAL_LOW = 10.0
LEVEL_WARNING_LOW = 25.0
PRESSURE_CRITICAL_HIGH = 80.0
PRESSURE_CRITICAL_LOW = 10.0
PRESSURE_WARNING_HIGH = 65.0

# ---------------------------------------------------------------------------
# In-memory store (swap for a real DB later without changing the API)
# ---------------------------------------------------------------------------
history = deque(maxlen=HISTORY_MAXLEN)
pump_state = {"status": "OFF"}


def classify_status(level: float, pressure: float) -> str:
    if pressure > PRESSURE_CRITICAL_HIGH or pressure < PRESSURE_CRITICAL_LOW or level < LEVEL_CRITICAL_LOW:
        return "critical"
    if pressure > PRESSURE_WARNING_HIGH or level < LEVEL_WARNING_LOW:
        return "warning"
    return "normal"


def decide_pump_status(level: float) -> str:
    """Simple hysteresis so the pump doesn't flicker on/off near a single threshold."""
    if level < LEVEL_PUMP_ON_BELOW:
        pump_state["status"] = "ON"
    elif level > LEVEL_PUMP_OFF_ABOVE:
        pump_state["status"] = "OFF"
    return pump_state["status"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/reading", methods=["POST"])
def post_reading():
    data = request.get_json(force=True, silent=True) or {}

    try:
        level = float(data["level"])
        pressure = float(data["pressure"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "reading must include numeric 'level' and 'pressure'"}), 400

    # Simulator/hardware may optionally report its own pump state; otherwise
    # the backend decides, so this also works if the ESP32 sends raw sensor
    # values only.
    pump_status = data.get("pump_status") or decide_pump_status(level)
    status = classify_status(level, pressure)
    timestamp = datetime.now().strftime("%H:%M:%S")

    reading = {
        "level": round(level, 2),
        "pressure": round(pressure, 2),
        "pump_status": pump_status,
        "status": status,
        "timestamp": timestamp,
    }
    history.append(reading)

    return jsonify({"ok": True, "reading": reading}), 201


@app.route("/api/latest", methods=["GET"])
def get_latest():
    if not history:
        return jsonify({
            "level": 0, "pressure": 0, "pump_status": "OFF",
            "status": "normal", "timestamp": datetime.now().strftime("%H:%M:%S"),
        })
    return jsonify(history[-1])


@app.route("/api/history", methods=["GET"])
def get_history():
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit, HISTORY_MAXLEN))
    return jsonify(list(history)[-limit:])


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "up", "readings_stored": len(history)})


@app.route("/")
def serve_dashboard():
    return send_from_directory(app.static_folder, "dashboard.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
