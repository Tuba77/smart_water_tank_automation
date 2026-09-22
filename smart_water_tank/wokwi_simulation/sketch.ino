/*
  Smart Water Tank Automation — Wokwi Hardware Simulation
  ---------------------------------------------------------
  Runs on a simulated ESP32 DevKit V1 in Wokwi. Reads a pressure sensor and
  an ultrasonic level sensor, drives a relay (pump) and buzzer, and POSTs
  each reading to the Flask backend — the same /api/reading endpoint that
  simulate_hardware.py (the Python stand-in) already talks to.

  Sensor note: Wokwi doesn't simulate the BMP280 used in the real BOM, so
  this uses its closest supported equivalent, the BMP180 (same Bosch
  family, same I2C wiring). On the real board, swap Adafruit_BMP085.h /
  Adafruit_BMP085 for Adafruit_BMP280.h / Adafruit_BMP280 — pin wiring
  and the rest of this sketch stay the same.

  Required libraries (Wokwi Library Manager / Arduino Library Manager):
    - Adafruit BMP085 Library   (works with BMP180)
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_BMP085.h>

// ---------------------------------------------------------------------------
// CONFIG — edit these two before running
// ---------------------------------------------------------------------------
const char* WIFI_SSID     = "Wokwi-GUEST";   // Wokwi's simulated WiFi (internet access, no password)
const char* WIFI_PASSWORD = "";

// Your Flask backend MUST be publicly reachable (Wokwi's virtual WiFi can't
// reach your laptop's localhost). Use an ngrok tunnel, or deploy to Render/
// PythonAnywhere, then paste the public URL below.
const char* BACKEND_URL = "https://YOUR-PUBLIC-BACKEND-URL/api/reading";

// ---------------------------------------------------------------------------
// PINS
// ---------------------------------------------------------------------------
#define TRIG_PIN   5
#define ECHO_PIN   18
#define RELAY_PIN  26
#define BUZZER_PIN 27

// ---------------------------------------------------------------------------
// TANK CALIBRATION — distance (cm) from the ultrasonic sensor to the water
// surface when the tank is empty vs. full. Adjust to match your tank.
// ---------------------------------------------------------------------------
const float DIST_EMPTY_CM = 20.0;  // sensor-to-surface distance when empty
const float DIST_FULL_CM  = 2.0;   // sensor-to-surface distance when full

// Pump hysteresis thresholds (match app.py's logic)
const float LEVEL_PUMP_ON_BELOW  = 30.0;
const float LEVEL_PUMP_OFF_ABOVE = 90.0;

// Status thresholds (match app.py's classify_status)
const float LEVEL_CRITICAL_LOW    = 10.0;
const float PRESSURE_CRITICAL_HI  = 80.0;
const float PRESSURE_CRITICAL_LO  = 10.0;

Adafruit_BMP085 bmp;
bool pumpOn = false;

const unsigned long SEND_INTERVAL_MS = 2000;
unsigned long lastSend = 0;

// ---------------------------------------------------------------------------
float readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // 30ms timeout
  if (duration == 0) return DIST_EMPTY_CM;          // no echo -> assume empty
  return duration / 58.0;                            // cm
}

float mapFloat(float x, float inMin, float inMax, float outMin, float outMax) {
  return (x - inMin) * (outMax - outMin) / (inMax - inMin) + outMin;
}

float distanceToLevelPercent(float distanceCM) {
  float level = mapFloat(distanceCM, DIST_EMPTY_CM, DIST_FULL_CM, 0.0, 100.0);
  return constrain(level, 0.0, 100.0);
}

// Convert raw barometric pressure (Pa) into the 0-100 "PSI-style" scale the
// dashboard/backend expect, calibrated around normal sea-level pressure.
float pressureToDisplayScale(int32_t pascals) {
  float hpa = pascals / 100.0;
  float display = mapFloat(hpa, 950.0, 1050.0, 0.0, 100.0);
  return constrain(display, 0.0, 100.0);
}

void updatePump(float level) {
  if (level < LEVEL_PUMP_ON_BELOW) pumpOn = true;
  else if (level > LEVEL_PUMP_OFF_ABOVE) pumpOn = false;
  digitalWrite(RELAY_PIN, pumpOn ? HIGH : LOW);
}

void updateBuzzer(float level, float pressure) {
  bool critical = (pressure > PRESSURE_CRITICAL_HI) ||
                  (pressure < PRESSURE_CRITICAL_LO) ||
                  (level < LEVEL_CRITICAL_LOW);
  digitalWrite(BUZZER_PIN, critical ? HIGH : LOW);
}

void sendReading(float level, float pressure) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping send.");
    return;
  }

  HTTPClient http;
  http.begin(BACKEND_URL);
  http.addHeader("Content-Type", "application/json");

  String payload = "{\"level\":" + String(level, 2) +
                    ",\"pressure\":" + String(pressure, 2) +
                    ",\"pump_status\":\"" + (pumpOn ? "ON" : "OFF") + "\"}";

  int code = http.POST(payload);
  Serial.print("POST -> ");
  Serial.print(code);
  Serial.print("  ");
  Serial.println(payload);
  http.end();
}

void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);

  Wire.begin();
  if (!bmp.begin()) {
    Serial.println("BMP180 not found! Check wiring.");
  }

  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println(" connected!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  if (millis() - lastSend >= SEND_INTERVAL_MS) {
    lastSend = millis();

    float distanceCM = readDistanceCM();
    float level = distanceToLevelPercent(distanceCM);
    float pressure = pressureToDisplayScale(bmp.readPressure());

    updatePump(level);
    updateBuzzer(level, pressure);
    sendReading(level, pressure);
  }
}
