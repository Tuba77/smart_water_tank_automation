# Smart Water Tank Automation — Backend

Flask backend + simulated hardware for the Smart Water Tank dashboard.

## How it fits together

```
simulate_hardware.py  --HTTP POST-->  app.py (Flask)  <--HTTP GET--  dashboard.html
   (stand-in ESP32)                    /api/reading            /api/latest
                                        /api/latest             /api/history
                                        /api/history
```

Later, replace `simulate_hardware.py` with real ESP32 firmware that POSTs
to `/api/reading` the same way — no backend or dashboard changes needed.

## Setup

```bash
pip install -r requirements.txt
```

## Run (two terminals)

**Terminal 1 — backend:**
```bash
python app.py
```
Dashboard opens at http://127.0.0.1:5000

**Terminal 2 — simulated hardware:**
```bash
python simulate_hardware.py
```
This starts posting fake sensor readings every 2 seconds. Watch the
dashboard update live, including occasional simulated anomalies
(pressure spikes / drops) that trigger the warning/critical states.

## API

| Method | Endpoint         | Description                                  |
|--------|------------------|-----------------------------------------------|
| POST   | `/api/reading`   | Push a new reading: `{level, pressure, pump_status?}` |
| GET    | `/api/latest`    | Most recent reading                           |
| GET    | `/api/history`   | Last N readings (`?limit=50`)                 |
| GET    | `/health`        | Liveness check                                 |

## Notes for the report

- **Pump control logic** lives server-side (`decide_pump_status` in
  `app.py`) using hysteresis (ON below 30%, OFF above 90%) so it doesn't
  flicker — this is the "control logic" your components list attributes
  to the ESP32; right now the backend does it, but it's easy to move onto
  the ESP32 itself later if you want edge-side control.
- **Status classification** (normal/warning/critical) is based on
  pressure and level thresholds, matching the dashboard's alert badges
  and event log.
- Currently uses in-memory storage (resets on restart) — swap `history`
  for a SQLite table if you want readings to persist across restarts.
- Deploy the backend (e.g. Render, PythonAnywhere) and point a real ESP32
  at its public URL once hardware is ready.
