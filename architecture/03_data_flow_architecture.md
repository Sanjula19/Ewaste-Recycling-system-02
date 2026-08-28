# 03 — Data Flow Architecture

## 3.1 End-to-End Data Flow Overview

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    COMPLETE DATA FLOW                                     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ┌──────────────────────────────────────────────────────────────────┐     ║
║  │ STEP 1: SENSOR DATA ACQUISITION                                  │     ║
║  │                                                                  │     ║
║  │  [Air Sample]                                                    │     ║
║  │      │                                                           │     ║
║  │      ▼                                                           │     ║
║  │  [MQ-2][MQ-7][MQ-135][MQ-303][MQ-136]  ←  Analog voltage read  │     ║
║  │      │                                                           │     ║
║  │      ▼                                                           │     ║
║  │  [DHT22] → Temperature + Humidity (for calibration)             │     ║
║  │      │                                                           │     ║
║  │      ▼                                                           │     ║
║  │  [ESP32 ADC] → 12-bit ADC reading (0–4095)                      │     ║
║  │      │                                                           │     ║
║  │      ▼                                                           │     ║
║  │  Voltage → Resistance (Rs) → Rs/R0 → ppm (via datasheet curve)  │     ║
║  └───────────────────────────────────┬──────────────────────────────┘     ║
║                                      │                                    ║
║  ┌───────────────────────────────────▼──────────────────────────────┐     ║
║  │ STEP 2: MQTT PUBLISH                                             │     ║
║  │                                                                  │     ║
║  │  JSON Payload:                                                   │     ║
║  │  {                                                               │     ║
║  │    "device_id": "esp32_node_01",                                 │     ║
║  │    "timestamp": "2026-07-31T13:52:00Z",                         │     ║
║  │    "sensors": {                                                  │     ║
║  │      "mq2_ppm": 45.3,                                           │     ║
║  │      "mq7_ppm": 12.1,                                           │     ║
║  │      "mq135_ppm": 8.7,                                          │     ║
║  │      "mq303_ppm": 0.02,                                         │     ║
║  │      "mq136_ppm": 0.5                                           │     ║
║  │    },                                                            │     ║
║  │    "environment": {                                              │     ║
║  │      "temperature_c": 28.4,                                     │     ║
║  │      "humidity_pct": 65.2                                       │     ║
║  │    }                                                             │     ║
║  │  }                                                               │     ║
║  │                                                                  │     ║
║  │  Topic: ewaste/sensor/esp32_node_01/readings                    │     ║
║  │  QoS: 1 (at-least-once delivery)                                │     ║
║  └───────────────────────────────────┬──────────────────────────────┘     ║
║                                      │ MQTT over TLS (port 8883)          ║
║  ┌───────────────────────────────────▼──────────────────────────────┐     ║
║  │ STEP 3: HIVEMQ CLOUD BROKER                                      │     ║
║  │                                                                  │     ║
║  │  Receives → Stores briefly → Forwards to subscribers             │     ║
║  └───────────────────────────────────┬──────────────────────────────┘     ║
║                                      │ MQTT Subscribe                     ║
║  ┌───────────────────────────────────▼──────────────────────────────┐     ║
║  │ STEP 4: FASTAPI BACKEND — MQTT SUBSCRIBER                        │     ║
║  │                                                                  │     ║
║  │  ┌─────────────────────────────────────────┐                    │     ║
║  │  │ mqtt_service.py (async listener)        │                    │     ║
║  │  │   → Parse JSON payload                  │                    │     ║
║  │  │   → Validate with Pydantic              │                    │     ║
║  │  │   → Enqueue for processing              │                    │     ║
║  │  └──────────────┬──────────────────────────┘                    │     ║
║  │                 │                                                │     ║
║  │         ┌───────┴────────────────────────┐                      │     ║
║  │         │         │                      │                      │     ║
║  │         ▼         ▼                      ▼                      │     ║
║  │   [ML Service] [Threshold]  [Firebase Writer]                   │     ║
║  └──────────┬────────┬───────────────────────────────────────────-─┘     ║
║             │        │                                                    ║
║  ┌──────────▼────┐ ┌─▼────────────────────────────────────────────┐      ║
║  │ STEP 5: ML   │ │ STEP 6: WHO THRESHOLD ENGINE                 │      ║
║  │ INFERENCE    │ │                                               │      ║
║  │              │ │  For each gas:                                │      ║
║  │ Load RF.pkl  │ │  ppm_reading vs who_limit                     │      ║
║  │              │ │                                               │      ║
║  │ Feature vec: │ │  ratio = reading / limit                      │      ║
║  │ [mq2, mq7,  │ │                                               │      ║
║  │  mq135,     │ │  ratio < 0.5   → GREEN (Safe)                 │      ║
║  │  mq303,     │ │  0.5 ≤ r < 1.0 → YELLOW (Caution)            │      ║
║  │  mq136,     │ │  ratio ≥ 1.0   → RED (Danger)                 │      ║
║  │  temp, hum] │ │                                               │      ║
║  │              │ │  Overall system risk = max(individual risks)  │      ║
║  │ Output:      │ └────────────────┬─────────────────────────────-┘      ║
║  │  gas_class   │                  │                                     ║
║  │  confidence% │ ┌────────────────▼────────────────────────────────┐    ║
║  └──────┬───────┘ │ STEP 7: KNOWLEDGE BASE QUERY                   │    ║
║         │         │                                                 │    ║
║         │         │  gas_class → lookup device_hazards.json        │    ║
║         │         │                                                 │    ║
║         │         │  Returns:                                       │    ║
║         │         │  {                                              │    ║
║         │         │    "source_device": "CRT Monitor",             │    ║
║         │         │    "health_risks": ["Brain damage", ...],      │    ║
║         │         │    "actions": ["Evacuate", "Wear RPE", ...]    │    ║
║         │         │  }                                              │    ║
║         │         └───────────────────────────────────────────────-┘    ║
║         │                         │                                      ║
║  ┌──────▼─────────────────────────▼───────────────────────────────┐      ║
║  │ STEP 8: ALERT ASSEMBLY + STORAGE                                │      ║
║  │                                                                 │      ║
║  │  Assemble unified alert object:                                 │      ║
║  │  {                                                              │      ║
║  │    timestamp, device_id,                                        │      ║
║  │    gas_detected: "Mercury Vapor",                               │      ║
║  │    gas_class_confidence: 0.94,                                  │      ║
║  │    readings: {mq2_ppm, mq7_ppm, ...},                          │      ║
║  │    risk_level: "RED",                                           │      ║
║  │    exceeded_by_pct: 80,                                         │      ║
║  │    source_device: "CRT Monitor",                                │      ║
║  │    health_risks: [...],                                         │      ║
║  │    actions: [...]                                               │      ║
║  │  }                                                              │      ║
║  │                                                                 │      ║
║  │  → Write to Firebase RT DB (live feed for dashboard)           │      ║
║  │  → Write to PostgreSQL (historical record)                     │      ║
║  │  → Trigger hardware alert via MQTT (LED/Buzzer command)        │      ║
║  └─────────────────────────────────────────────────────────────────┘      ║
║                                │                                          ║
║  ┌─────────────────────────────▼───────────────────────────────────┐      ║
║  │ STEP 9: FRONTEND DISPLAY                                        │      ║
║  │                                                                 │      ║
║  │  Firebase SDK → Live gas gauge updates every 5 sec             │      ║
║  │  REST API     → Historical data on Page 3                      │      ║
║  │  REST API     → ML metrics on Page 4                           │      ║
║  └─────────────────────────────────────────────────────────────────┘      ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## 3.2 Data Timing and Frequency

| Stage | Frequency | Latency Target |
|-------|-----------|---------------|
| Sensor ADC reading | Every 2 sec | <10ms |
| MQTT publish | Every 5 sec | <500ms |
| Backend ML inference | Per message | <200ms |
| Firebase write | Per message | <300ms |
| PostgreSQL write | Per message | <100ms |
| Dashboard refresh | Every 5 sec | <1000ms |
| Hardware LED/Buzzer response | Per alert | <1sec end-to-end |

---

## 3.3 Data Formats

### 3.3.1 MQTT Uplink Payload (ESP32 → Broker)
```json
{
  "device_id": "esp32_node_01",
  "timestamp": "2026-07-31T13:52:00.000Z",
  "sensors": {
    "mq2_ppm":   45.3,
    "mq7_ppm":   12.1,
    "mq135_ppm": 8.7,
    "mq303_ppm": 0.022,
    "mq136_ppm": 0.5
  },
  "environment": {
    "temperature_c": 28.4,
    "humidity_pct":  65.2
  },
  "battery_mv": 3720
}
```

### 3.3.2 ML Inference Request (Internal)
```json
{
  "features": [45.3, 12.1, 8.7, 0.022, 0.5, 28.4, 65.2]
}
```

### 3.3.3 Unified Alert Object (Backend → DB + Dashboard)
```json
{
  "alert_id": "ALT-2026073114521",
  "timestamp": "2026-07-31T14:52:10.123Z",
  "device_id": "esp32_node_01",
  "risk_level": "RED",
  "gas_detected": "Mercury Vapor",
  "gas_confidence_pct": 94.3,
  "readings": {
    "mq2_ppm": 45.3,
    "mq7_ppm": 12.1,
    "mq135_ppm": 8.7,
    "mq303_ppm": 0.022,
    "mq136_ppm": 0.5
  },
  "who_comparison": {
    "gas": "Mercury Vapor",
    "reading_mg_m3": 0.045,
    "who_limit_mg_m3": 0.025,
    "exceeded_by_pct": 80
  },
  "source_device": "CRT Monitor",
  "health_risks": ["Brain damage", "Kidney failure", "Neurological effects"],
  "actions": [
    "Evacuate area immediately",
    "Wear supplied-air respirator",
    "Notify safety officer",
    "Do not handle device"
  ],
  "environment": {
    "temperature_c": 28.4,
    "humidity_pct": 65.2
  }
}
```

### 3.3.4 MQTT Downlink Command (Backend → ESP32)
```json
{
  "command": "set_alert",
  "level": "RED",
  "buzzer_beeps": 5,
  "led_color": "RED",
  "lcd_line1": "MERCURY DETECTED",
  "lcd_line2": "EVACUATE NOW!"
}
```

---

## 3.4 Error Handling in Data Flow

| Failure Point | Handling Strategy |
|---------------|------------------|
| Sensor offline | ESP32 sends `null` for that sensor; backend flags partial reading |
| MQTT broker unreachable | ESP32 retries with exponential backoff (1s, 2s, 4s, 8s) |
| ML inference fails | Backend returns UNKNOWN classification; threshold still runs |
| Firebase write fails | Backend queues locally; retries after 30 sec |
| PostgreSQL write fails | Error logged; alert still sent to Firebase |
| Dashboard API timeout | Frontend shows cached last reading + "Last updated: Xs ago" |
