# Integration Service Configuration
## E-Waste Recycling System — Step 3: Port Isolation

Generated: 2026-08-29 | No business logic was changed.

---

## Component 1 — Shehan (AI Waste Assessment)

| Item | Value |
|---|---|
| **Component Name** | Component 1 — AI Waste Assessment |
| **Owner** | Shehan |
| **Backend Port** | 8001 |
| **Frontend Port** | None (no web frontend — reserved for future addition) |
| **Database / Storage** | No database. CSV logs written locally on Raspberry Pi |
| **MQTT** | Not used |
| **IoT Hardware** | Load Cell → HX711 → Arduino UNO → USB Serial → Raspberry Pi; ESP32-CAM → Wi-Fi |

### Environment Variables (component-1/component_1/backend/.env)

| Variable | Default Value | Description |
|---|---|---|
| SERIAL_PORT | /dev/ttyACM0 | Arduino UNO USB serial port |
| BAUD_RATE | 9600 | Serial baud rate |
| CAMERA_URL | http://10.156.150.180/capture | ESP32-CAM capture endpoint — update to your camera IP |
| GENERAL_BACKEND_URL | http://localhost:8001/waste/predict | General waste API |
| EWASTE_BACKEND_URL | http://localhost:8001/ewaste/analyze | E-waste API |

### Start Commands

`ash
# Backend (run on the machine hosting the AI models)
cd component-1/component_1/backend
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8001

# Raspberry Pi data acquisition script (run on the Pi)
cd component-1/component_1/raspberry_pi
python weight_camera.py
`

### Changes Made

- requirements.txt: Added python-dotenv
- .env.example: Created (template with all configurable values)
- .env: Created (copy of .env.example — update CAMERA_URL with real Pi network IP before running)
- weight_camera.py: Replaced 4 hardcoded values (SERIAL_PORT, BAUD_RATE, CAMERA_URL,
  GENERAL_BACKEND_URL, EWASTE_BACKEND_URL) with os.getenv() calls that load from .env.
  Original IPs preserved as fallback defaults. No camera or AI logic was changed.

---

## Component 2 — Sanjula (Toxic Gas Detection)

| Item | Value |
|---|---|
| **Component Name** | Component 2 — Toxic Gas Detection |
| **Owner** | Sanjula |
| **Backend Port** | 8002 |
| **Frontend Port** | 5174 |
| **Database / Storage** | SQLite: component2_ewaste_gas.db (separate from Component 3) |
| **MQTT Broker** | HiveMQ Cloud: 8c22931e95374473bea07f2ce5b65093.s1.eu.hivemq.cloud |
| **MQTT Port** | 8883 (TLS) |
| **MQTT Topic** | ewaste/esp32/sensors |
| **IoT Hardware** | ESP32 + MQ-2 / MQ-7 / MQ-135 / DHT22 + LCD + LEDs + Buzzer |

### Environment Variables (component-2/backend/.env)

| Variable | Default Value | Description |
|---|---|---|
| DATABASE_URL | sqlite+aiosqlite:///./component2_ewaste_gas.db | SQLite database path |
| MQTT_BROKER | 8c22931e95374473bea07f2ce5b65093.s1.eu.hivemq.cloud | HiveMQ Cloud host |
| MQTT_PORT | 8883 | MQTT TLS port |
| MQTT_TOPIC | ewaste/esp32/sensors | Sensor data topic |
| MQTT_USER | hivemq.webclient.1786954284059 | MQTT username |
| MQTT_PASSWORD | (see .env) | MQTT password |
| JWT_SECRET_KEY | ewaste-gas-detection-super-secret-key-2024 | JWT signing key |
| DEFAULT_API_KEY | esp32-device-key-001 | ESP32 device API key |

### Start Commands

`ash
# Backend
cd component-2/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002

# Frontend
cd component-2/frontend
npm install
npm run dev
# Runs on http://localhost:5174
`

### Changes Made

- backend/app/config.py: database_url default changed from ewaste_gas.db to component2_ewaste_gas.db
- frontend/vite.config.js: server.port changed 5173 → 5174; proxy target changed 8000 → 8002
- backend/.env: Created (locks in Component 2's own database name and MQTT config)

---

## Component 3 — Wisu (Smart Process Optimization)

| Item | Value |
|---|---|
| **Component Name** | Component 3 — Smart Process Optimization |
| **Owner** | Wisu |
| **Backend Port** | 8003 |
| **Frontend Port** | 3000 (Create React App default — no conflict) |
| **Database / Storage** | SQLite: component3_ewaste_gas.db (separate from Component 2) |
| **MQTT Broker** | HiveMQ Cloud: 8c22931e95374473bea07f2ce5b65093.s1.eu.hivemq.cloud |
| **MQTT Port** | 8883 (TLS) |
| **MQTT Topic** | ewaste/esp32/sensors |
| **IoT Hardware** | Same physical ESP32 sensor array as Component 2 (read-only, separate subscriber) |

### MQTT Note

Component 2 and Component 3 both subscribe to the same physical MQTT topic (ewaste/esp32/sensors).
This is valid MQTT behavior — a broker delivers the same message to all subscribers independently.
Each component writes received readings to its own separate SQLite file.
The physical MQTT topic and ESP32 firmware were NOT changed.

### Environment Variables (component-3/backend/.env and component-3/frontend/.env)

| Variable | Default Value | Description |
|---|---|---|
| DATABASE_URL | sqlite+aiosqlite:///./component3_ewaste_gas.db | SQLite database (C3 only) |
| APP_NAME | E-Waste Smart Process Optimization | Identifies this backend in logs |
| MQTT_BROKER | 8c22931e95374473bea07f2ce5b65093.s1.eu.hivemq.cloud | HiveMQ Cloud host |
| MQTT_PORT | 8883 | MQTT TLS port |
| MQTT_TOPIC | ewaste/esp32/sensors | Sensor data topic |
| MQTT_USER | hivemq.webclient.1786954284059 | MQTT username |
| MQTT_PASSWORD | (see .env) | MQTT password |
| JWT_SECRET_KEY | ewaste-process-optimization-secret-key-2024 | Different key from C2 |
| REACT_APP_API_BASE_URL | http://localhost:8003 | Frontend → backend URL (CRA) |

### Start Commands

`ash
# Backend
cd component-3/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003

# Frontend
cd component-3/frontend
npm install
npm start
# Runs on http://localhost:3000
`

### Changes Made

- backend/app/config.py: app_name changed to "E-Waste Smart Process Optimization";
  database_url default changed from ewaste_gas.db to component3_ewaste_gas.db
- frontend/src/services/api.js: BASE_URL changed from hardcoded http://127.0.0.1:8000
  to process.env.REACT_APP_API_BASE_URL || http://127.0.0.1:8003
- backend/.env: Created (Component 3's own database name, MQTT config, distinct JWT key)
- frontend/.env: Created (sets REACT_APP_API_BASE_URL=http://localhost:8003 for CRA)

---

## Component 4 — Mayashi (Predictive Economic Valuation)

| Item | Value |
|---|---|
| **Component Name** | Component 4 — Predictive Economic Valuation & Strategic Disposition |
| **Owner** | Mayashi |
| **Backend Port** | 8004 |
| **Frontend Port** | 5175 |
| **Database / Storage** | InfluxDB (optional, metal_prices bucket) — falls back to CSV if unavailable |
| **MQTT** | Not used (uses HTTP REST for ESP32 communication) |
| **IoT Hardware** | ESP32 DevKit V1 + TCS34725 colour sensor + IR obstacle sensor + HC-SR04 + Servos (partial) |

### Environment Variables (component-4/frontend/.env and backend .env)

| Variable | Default Value | Description |
|---|---|---|
| VITE_API_BASE_URL | http://localhost:8004 | Frontend → backend URL (Vite/browser) |
| INFLUXDB_URL | http://localhost:8086 | InfluxDB server (optional) |
| INFLUXDB_TOKEN | (set in .env) | InfluxDB auth token |
| INFLUXDB_ORG | ewaste_org | InfluxDB organisation name |
| INFLUXDB_BUCKET | metal_prices | InfluxDB bucket name |

### Start Commands

`ash
# Backend
cd component-4/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8004

# Frontend
cd component-4/frontend
npm install
npm run dev
# Runs on http://localhost:5175
`

### Changes Made

- frontend/vite.config.js: server.port changed 5173 → 5175
- frontend/.env: Created with VITE_API_BASE_URL=http://localhost:8004
- frontend/.env.example: Updated port reference from 8000 to 8004

---

## Final Port Map

| Component | Owner | Backend | Frontend | Database | MQTT |
|---|---|---|---|---|---|
| Component 1 | Shehan | 8001 | (none) | CSV on Pi | None |
| Component 2 | Sanjula | 8002 | 5174 | component2_ewaste_gas.db | ewaste/esp32/sensors |
| Component 3 | Wisu | 8003 | 3000 | component3_ewaste_gas.db | ewaste/esp32/sensors |
| Component 4 | Mayashi | 8004 | 5175 | InfluxDB / CSV fallback | None (HTTP REST) |

---

## Files Changed (9 files total)

### Component 1 (3 files)
1. component-1/component_1/backend/requirements.txt — Added python-dotenv
2. component-1/component_1/backend/.env.example — NEW: environment template
3. component-1/component_1/backend/.env — NEW: active configuration
4. component-1/component_1/raspberry_pi/weight_camera.py — Replaced hardcoded IPs/port with os.getenv()

### Component 2 (3 files)
5. component-2/backend/app/config.py — database_url default: ewaste_gas.db → component2_ewaste_gas.db
6. component-2/frontend/vite.config.js — port: 5173 → 5174; proxy target: 8000 → 8002
7. component-2/backend/.env — NEW: database and MQTT configuration

### Component 3 (4 files)
8. component-3/backend/app/config.py — app_name updated; database_url: ewaste_gas.db → component3_ewaste_gas.db
9. component-3/frontend/src/services/api.js — BASE_URL: hardcoded 8000 → env-var-backed 8003
10. component-3/backend/.env — NEW: database and MQTT configuration
11. component-3/frontend/.env — NEW: REACT_APP_API_BASE_URL=http://localhost:8003

### Component 4 (3 files)
12. component-4/frontend/vite.config.js — port: 5173 → 5175
13. component-4/frontend/.env — NEW: VITE_API_BASE_URL=http://localhost:8004
14. component-4/frontend/.env.example — Updated port from 8000 to 8004

---

## Remaining Conflicts / Notes

1. MQTT SHARED TOPIC (C2 and C3): Both components subscribe to ewaste/esp32/sensors on the same
   HiveMQ Cloud broker. This is intentional valid MQTT fanout — the physical sensor has one topic.
   Each component stores data independently in its own SQLite file. No conflict at runtime.

2. COMPONENT 1 CAMERA IP: CAMERA_URL in .env still defaults to the original Pi network IP
   (10.156.150.180). Update this in component-1/component_1/backend/.env before running on
   a different network.

3. COMPONENT 1 NO FRONTEND: No web frontend exists. Port reserved for future addition.

4. COMPONENT 4 INFLUXDB: Optional. If not running, backend degrades gracefully to CSV data.
   Backend runs fully without InfluxDB.

5. COMPONENT 1 LARGE MODEL FILES MISSING: resnet50_waste_type_final.keras and
   resnet50_condition_final.keras must be placed in component-1/component_1/backend/models/
   before the backend can start.
