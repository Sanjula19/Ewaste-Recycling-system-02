# 05 — Communication Architecture

## 5.1 Communication Protocols Overview

```
┌───────────────┐     MQTT/TLS      ┌─────────────┐    MQTT Subscribe   ┌─────────────────┐
│  ESP32 Node   │ ─────────────────► │  HiveMQ     │ ───────────────────► │  FastAPI MQTT   │
│               │ ◄───────────────── │  Cloud      │ ◄─────────────────── │  Subscriber     │
└───────────────┘     MQTT Commands  │  Broker     │    MQTT Publish      └────────┬────────┘
                                     └─────────────┘                               │
                                                                                    │ Internal
                                                                                    │ service calls
                                                                       ┌────────────▼────────────┐
                                                                       │    FastAPI REST API      │
                                                                       │    (HTTP/HTTPS)          │
                                                                       └────────────┬────────────┘
                                                                                    │
                               ┌──────────────┐   Firebase SDK   ┌─────────────────▼──────────┐
                               │  React.js    │ ◄──────────────── │   Firebase Realtime DB     │
                               │  Dashboard   │ ──────────────►   │   (Live data feed)         │
                               │              │                    └────────────────────────────┘
                               │              │   REST/Axios
                               │              │ ◄────────────────  FastAPI REST endpoints
                               └──────────────┘
```

---

## 5.2 MQTT Protocol Design

### 5.2.1 Broker Configuration
| Parameter | Value |
|-----------|-------|
| Broker | HiveMQ Cloud (free tier) |
| Host | `<uuid>.s2.eu.hivemq.cloud` |
| Port | 8883 (MQTT over TLS) |
| Protocol | MQTT v3.1.1 |
| Authentication | Username + Password |
| TLS | Required (CA certificate) |
| QoS Level | 1 (at-least-once) |
| Retain | false (live readings only) |

### 5.2.2 MQTT Topic Structure

```
ewaste/
├── sensor/
│   ├── <device_id>/
│   │   ├── readings         ← ESP32 publishes sensor data
│   │   ├── status           ← ESP32 publishes heartbeat
│   │   └── ack              ← Backend publishes acknowledgement
│   └── broadcast/
│       └── commands         ← Backend broadcasts to all nodes
├── alerts/
│   ├── <device_id>/
│   │   └── trigger          ← Backend sends alert command to ESP32
│   └── broadcast/
│       └── emergency        ← Emergency broadcast to all devices
└── system/
    ├── health               ← System health status
    └── config               ← Configuration updates
```

### 5.2.3 ESP32 Subscribed Topics
```
ewaste/sensor/esp32_node_01/ack
ewaste/alerts/esp32_node_01/trigger
ewaste/sensor/broadcast/commands
ewaste/alerts/broadcast/emergency
```

### 5.2.4 FastAPI Subscribed Topics
```
ewaste/sensor/+/readings     (wildcard: all devices)
ewaste/sensor/+/status       (device heartbeats)
```

---

## 5.3 REST API Design

### 5.3.1 API Base URL
```
Development: http://localhost:8000/api/v1
Production:  https://ewaste-backend.onrender.com/api/v1
```

### 5.3.2 API Endpoints

#### Gas Readings
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/readings/latest` | Get latest reading from all devices |
| GET | `/readings/{device_id}/latest` | Get latest reading from specific device |
| GET | `/readings/{device_id}/history` | Get paginated historical readings |
| GET | `/readings/export` | Export readings as CSV |

#### Alerts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/alerts/` | Get all active alerts |
| GET | `/alerts/{alert_id}` | Get specific alert details |
| PUT | `/alerts/{alert_id}/acknowledge` | Mark alert as acknowledged |
| GET | `/alerts/history` | Get historical alerts |

#### ML Predictions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/predict/classify` | Classify gas from sensor readings |
| GET | `/predict/model-info` | Get ML model metadata + metrics |

#### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/reports/summary` | Get daily/weekly/monthly summary |
| GET | `/reports/model-performance` | Get confusion matrix + metrics |
| GET | `/reports/export/{type}` | Export report (pdf/csv) |

#### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | API health check |
| GET | `/health/mqtt` | MQTT broker connectivity status |
| GET | `/health/db` | Database connectivity status |

### 5.3.3 API Request/Response Format

**POST /predict/classify**
```
Request:
{
  "mq2_ppm":   45.3,
  "mq7_ppm":   12.1,
  "mq135_ppm": 8.7,
  "mq303_ppm": 0.022,
  "mq136_ppm": 0.5,
  "temperature_c": 28.4,
  "humidity_pct": 65.2
}

Response:
{
  "gas_class": "Mercury Vapor",
  "confidence": 0.943,
  "risk_level": "RED",
  "who_comparison": {
    "reading_mg_m3": 0.045,
    "limit_mg_m3": 0.025,
    "exceeded_by_pct": 80
  },
  "source_device": "CRT Monitor",
  "health_risks": ["Brain damage", "Kidney failure"],
  "actions": ["Evacuate immediately", "Wear RPE"],
  "model_version": "rf_v1"
}
```

---

## 5.4 Firebase Realtime Database Communication

### 5.4.1 Firebase Configuration
| Parameter | Value |
|-----------|-------|
| Product | Firebase Realtime Database |
| SDK | Firebase Admin SDK (backend) + Firebase JS SDK (frontend) |
| Auth | Service Account (backend) / Anonymous (frontend) |
| Region | us-central1 |
| Plan | Free tier (1 GB storage, 10 GB/month transfer) |

### 5.4.2 Data Structure in Firebase
```json
{
  "ewaste_system": {
    "devices": {
      "esp32_node_01": {
        "status": "online",
        "last_seen": "2026-07-31T14:52:00Z",
        "current_reading": {
          "timestamp": "2026-07-31T14:52:10Z",
          "mq2_ppm": 45.3,
          "mq7_ppm": 12.1,
          "mq135_ppm": 8.7,
          "mq303_ppm": 0.022,
          "mq136_ppm": 0.5,
          "temperature_c": 28.4,
          "humidity_pct": 65.2,
          "risk_level": "RED",
          "gas_detected": "Mercury Vapor"
        }
      }
    },
    "active_alerts": {
      "ALT-2026073114521": {
        "timestamp": "2026-07-31T14:52:10Z",
        "risk_level": "RED",
        "gas": "Mercury Vapor",
        "device": "esp32_node_01",
        "acknowledged": false
      }
    },
    "system_status": {
      "online": true,
      "last_updated": "2026-07-31T14:52:10Z"
    }
  }
}
```

---

## 5.5 Security Design

| Layer | Security Measure |
|-------|-----------------|
| MQTT | TLS 1.2+, Username/Password auth, per-device credentials |
| REST API | API Key header (`X-API-Key`), CORS restriction to dashboard domain |
| Firebase | Security Rules: read-only for dashboard, write-only via Admin SDK |
| PostgreSQL | Private network (no public exposure), SSL connection |
| ESP32 Credentials | Stored in `config.h` (excluded from git via `.gitignore`) |
| Secrets | `.env` file (never committed), `.env.example` provided |
