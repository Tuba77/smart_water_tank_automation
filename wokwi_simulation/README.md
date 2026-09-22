# Wokwi Hardware Simulation — Smart Water Tank

This simulates the ESP32 side of your BOM (ESP32 DevKit V1 + pressure sensor +
ultrasonic level sensor + relay + buzzer) inside your browser, and sends
readings to your real Flask backend over the internet — no physical hardware
needed yet.

## Sensor substitution note (for your report)

Wokwi doesn't have a BMP280 part, so this uses its closest simulated
equivalent: the **BMP180** (same Bosch family, same I2C interface, same
wiring). Mention this substitution in your report. On the real board, this
becomes a two-line change: swap `Adafruit_BMP085.h`/`Adafruit_BMP085` for
`Adafruit_BMP280.h`/`Adafruit_BMP280` — the wiring and the rest of the code
are unchanged.

## Why you need a public backend URL

Wokwi's simulated ESP32 WiFi ("Wokwi-GUEST") really does reach the internet
from your browser — but it can't reach `127.0.0.1` on your laptop, because
that's not on the public internet. You have two options:

**Option A — ngrok (quick, good for a demo/viva)**
```bash
# in a terminal, with your Flask backend already running on port 5000:
ngrok http 5000
```
Copy the `https://xxxx.ngrok-free.app` URL it gives you.

**Option B — deploy the backend (more permanent)**
Deploy `app.py` to Render, PythonAnywhere, Railway, etc. and use that public URL.

Either way, paste the URL into `sketch.ino`:
```cpp
const char* BACKEND_URL = "https://YOUR-PUBLIC-BACKEND-URL/api/reading";
```

## Running it

1. Go to [wokwi.com](https://wokwi.com) → **New Project** → **ESP32**.
2. Replace the default `diagram.json` with the one in this folder.
3. Replace the default `sketch.ino` with the one in this folder.
4. Open the **Library Manager** (left sidebar) and add **Adafruit BMP085
   Library** — or just drop in `libraries.txt` from this folder, Wokwi reads
   it automatically.
5. Edit `BACKEND_URL` in the sketch (see above).
6. Click **▶ Start Simulation**. Open the Serial Monitor to watch it connect
   to WiFi and start POSTing readings — you should see `POST -> 201` every
   2 seconds.
7. Open your dashboard (`http://127.0.0.1:5000` or wherever it's hosted) —
   it should now show live data coming from the simulated ESP32 instead of
   `simulate_hardware.py`.

## Testing alerts during the simulation

Click on the **HC-SR04** in the diagram to drag its distance slider down
(simulates the tank draining) — watch the level drop and the pump/relay
switch on past 30%. Click the **BMP180** to push its pressure slider to the
extremes — watch the buzzer and the dashboard's warning/critical badges
trigger. Great for a live viva demo since you don't have to wait for real
water to drain.

## Files in this folder

| File | Purpose |
|---|---|
| `diagram.json` | Wokwi circuit: ESP32 + BMP180 + HC-SR04 + relay + buzzer |
| `sketch.ino` | Arduino firmware — reads sensors, controls pump/buzzer, posts to backend |
| `libraries.txt` | Tells Wokwi which Arduino library to auto-install |
| `wokwi.toml` | Only needed if you use the Wokwi VS Code extension instead of wokwi.com |

## Going from simulation to real hardware later

Nothing on the backend or dashboard changes. On the real ESP32:
- Swap the BMP180 library calls for `Adafruit_BMP280`
- Swap `WIFI_SSID`/`WIFI_PASSWORD` for your real WiFi
- Everything else in `sketch.ino` — sensor math, pump logic, the HTTP POST
  to `/api/reading` — works as-is.
