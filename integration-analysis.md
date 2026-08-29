# Integration Analysis — E-Waste Recycling System
> Generated: 2026-08-29 | Read-only analysis — no code was modified.

---

## Component 1 — Shehan (AI Waste Assessment)

**Purpose:** Camera + weight-based AI classification of general waste and e-waste at the physical intake point. Acts as the entry point for the full pipeline.

| Item | Detail |
|---|---|
| **Frontend** | None (no web frontend; local Raspberry Pi dashboard script only) |
| **Frontend Start** | python raspberry_pi/dashboard.py (local Pi script, no browser UI) |
| **Backend** | Python / FastAPI |
| **Backend Start** | cd component_1/backend && uvicorn app:app --host 0.0.0.0 --port 8000 |
| **APIs** | GET /health · POST /waste/predict · POST /ewaste/analyze |
| **Port** | **8000** (backend) |
| **Database / Storage** | No database. Logs to local CSV files on Raspberry Pi (waste_results.csv, ewaste_results.csv) |
| **IoT Hardware** | Load Cell -> HX711 -> Arduino UNO -> USB Serial -> Raspberry Pi; ESP32-CAM -> Wi-Fi -> Raspberry Pi |
| **IoT Communication** | USB Serial (load cell) + HTTP GET (ESP32-CAM at http://<cam-ip>/capture) |
| **Key Dependencies** | fastapi, uvicorn, tensorflow, numpy, pillow, ultralytics (YOLOv8), python-multipart |
| **Environment Variables** | None in .env — camera IP and backend IP are HARDCODED in weight_camera.py |
| **AI Models** | YOLOv8n (e-waste, .pt included); ResNet50 waste-type + condition (.keras, NOT in repo) |
| **README / Docs** | component_1/README.md — well documented, includes integration flow |

---

## Component 2 — Sanjula (Toxic Gas Detection)

**Purpose:** Real-time toxic gas detection via ESP32 + MQ-sensor array. ML-classifies gas type and displays live readings on a React dashboard.

| Item | Detail |
|---|---|
| **Frontend** | React 18 + Vite (JSX) |
| **Frontend Start** | cd frontend && npm run dev (Vite) |
| **Frontend Port** | **5173** (Vite default; proxies /api to localhost:8000) |
| **Backend** | Python / FastAPI |
| **Backend Start** | cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 |
| **APIs** | GET / · GET /api/v1/health · GET /api/v1/mqtt/status · GET /api/v1/readings/latest · GET /api/v1/readings · GET /api/v1/readings/{id} · POST /api/v1/readings/label · POST /api/v1/predict · GET /api/v1/predict/status · GET /api/v1/alerts · GET /api/v1/dashboard/stats · GET /api/v1/dashboard/chart-data · GET /api/v1/trials · GET /api/v1/export |
| **Port** | **8000** (backend) · **5173** (frontend) |
| **Database / Storage** | SQLite (ewaste_gas.db) via SQLAlchemy async (aiosqlite) |
| **IoT Hardware** | ESP32 + MQ-2 / MQ-7 / MQ-135 sensors + DHT22 + LCD (I2C) + LEDs + Buzzer |
| **IoT Communication** | MQTT over TLS port 8883 to HiveMQ Cloud, topic: ewaste/esp32/sensors |
| **Key Dependencies** | fastapi, uvicorn, pydantic-settings, scikit-learn, joblib, numpy, sqlalchemy[asyncio], aiosqlite, paho-mqtt, python-dotenv, httpx, python-multipart |
| **Environment Variables** | DATABASE_URL, MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_TOPIC, CORS_ORIGINS, JWT_SECRET_KEY, DEFAULT_API_KEY |
| **AI Models** | Random Forest (scikit-learn) — single-label and multi-label gas classification |
| **README / Docs** | README.md + architecture/ folder (15-document specification) |

---

## Component 3 — Wisu (Smart Process Optimization)

**Purpose:** Process optimization for waste treatment — moisture-based recycling recommendations, C:N ratios, etc. Backend currently shares identical code with Component 2.

> WARNING: Component 3 backend is byte-for-byte identical to Component 2 backend.
> Both use MQTT topic ewaste/esp32/sensors and SQLite file ewaste_gas.db.
> Running both on same machine at defaults will cause port and data conflicts.

| Item | Detail |
|---|---|
| **Frontend** | React 18 + Create React App (.js files, not .jsx) |
| **Frontend Start** | cd frontend && npm start (react-scripts) |
| **Frontend Port** | **3000** (Create React App default) |
| **Backend** | Python / FastAPI |
| **Backend Start** | cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 |
| **APIs** | Same as Component 2: GET /api/v1/health · GET /api/v1/mqtt/status · GET /api/v1/readings/latest · GET /api/v1/readings · POST /api/v1/readings/label · POST /api/v1/predict · GET /api/v1/dashboard/stats · GET /api/v1/dashboard/chart-data · GET /api/v1/alerts · GET /api/v1/trials · GET /api/v1/export |
| **Port** | **8000** (backend) · **3000** (frontend) |
| **Database / Storage** | SQLite (ewaste_gas.db) — SAME filename as Component 2 |
| **IoT Hardware** | Same ESP32 stack as Component 2 (shared MQTT config) |
| **IoT Communication** | MQTT over TLS to HiveMQ Cloud — IDENTICAL broker, topic, credentials as Component 2 |
| **Key Dependencies** | fastapi, uvicorn, pydantic-settings, scikit-learn, joblib, numpy, sqlalchemy[asyncio], aiosqlite, paho-mqtt, python-dotenv, python-multipart |
| **Environment Variables** | Same as Component 2 |
| **AI Models** | Random Forest (same structure as Component 2) |
| **README / Docs** | README.md (describes full 4-component concept, not Component 3 specifically) |

---

## Component 4 — Mayashi (Predictive Economic Valuation and Strategic Disposition)

**Purpose:** ARIMA/LSTM price forecasting for recovered metals (aluminium, copper, lead, nickel, zinc, steel). Sell/Hold recommendations, tonnage manifests (PDF), IoT routing decisions for physical sorting gates.

| Item | Detail |
|---|---|
| **Frontend** | React 18 + Vite (JSX) — named EcoVision |
| **Frontend Start** | cd frontend && npm run dev (Vite) |
| **Frontend Port** | **5173** (explicitly set in vite.config.js) |
| **Backend** | Python / FastAPI |
| **Backend Start** | cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 |
| **APIs** | GET /api/health · POST /api/forecast/ · GET /api/forecast/supported-metals · POST /api/disposition/ · POST /api/iot/ingest · GET /api/iot/last-scan · POST /api/iot/bin-status · GET /api/iot/bin-status/{bin_id} · GET /api/manifest/summary · GET /api/manifest/cycles · GET /api/manifest/pdf · POST /api/manifest/reset · GET /api/market/overview |
| **Port** | **8000** (backend) · **5173** (frontend) |
| **Database / Storage** | InfluxDB (metal_prices bucket, ewaste_org) for live metal prices — graceful CSV fallback; in-memory manifest ledger |
| **IoT Hardware** | ESP32 DevKit V1 + TCS34725 colour sensor + IR obstacle sensor (FC-51) + HC-SR04 ultrasonic + SG90/MG96R servo gates + LEDs + Buzzer. PARTIAL: colour + IR working; servos/Wi-Fi/HTTP not yet wired. |
| **IoT Communication** | HTTP POST from ESP32 to POST /api/iot/ingest (REST, not MQTT) |
| **Key Dependencies** | fastapi, uvicorn, pydantic, pandas, numpy, scikit-learn, statsmodels (ARIMA), tensorflow (LSTM), requests, python-dotenv, influxdb-client, reportlab (PDF), python-multipart |
| **Environment Variables** | Frontend: VITE_API_BASE_URL. Backend: INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG, INFLUXDB_BUCKET |
| **AI Models** | ARIMA + LSTM per metal: arima_{metal}_model.pkl and lstm_{metal}_model.h5 for 6 metals. All 12 model files present in backend/models/. |
| **README / Docs** | Mayashi-IOT-handoff/SETUP.md + PROJECT_PROGRESS.md + IoT Implementation/ HTML docs |

---

## Proposed Service Map

| Component | Owner | Backend Port | Frontend Port |
|---|---|---|---|
| Component 1 (Shehan) | AI Waste Assessment | 8001 | N/A |
| Component 2 (Sanjula) | Gas Detection | 8002 | 5174 |
| Component 3 (Wisu) | Process Optimization | 8003 | 3000 |
| Component 4 (Mayashi) | Economic Valuation | 8004 | 5175 |

> These ports are PROPOSED ONLY for future integration planning. No code has been changed.

---

## Conflict and Issue Summary

1. PORT CONFLICT: All four backends default to port 8000. Cannot run simultaneously without reassignment.
2. FRONTEND PORT CONFLICT: Component 2 and Component 4 both use Vite port 5173.
3. COMPONENT 3 BACKEND = COPY OF COMPONENT 2: Byte-for-byte identical code. Same MQTT topic, same SQLite filename.
4. MQTT CONFLICT (C2 and C3): Both subscribe to ewaste/esp32/sensors on same HiveMQ broker with same credentials.
5. SQLITE CONFLICT (C2 and C3): Both default to ewaste_gas.db filename.
6. HARDCODED IPs IN COMPONENT 1: CAMERA_URL, GENERAL_BACKEND_URL, EWASTE_BACKEND_URL hardcoded in weight_camera.py.
7. MISSING MODEL FILES IN COMPONENT 1: resnet50_waste_type_final.keras and resnet50_condition_final.keras not in repo.
8. COMPONENT 4 IOT HARDWARE PARTIALLY BUILT: Servos, HC-SR04, LEDs, buzzer, Wi-Fi/HTTP not yet connected.

---

## Integration Data Flow (from Component 1 README)

Physical Item
  -> Component 1 (AI Waste Assessment, port 8001)
       |-> Component 2 (Gas Detection, port 8002)  [parallel]
       +-> Component 4 (Economic Valuation, port 8004)

Component 3 (Process Optimization, port 8003) operates independently.
