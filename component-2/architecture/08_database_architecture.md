# 08 — Database Architecture

## 8.1 Dual-Database Strategy

| Database | Role | Why |
|----------|------|-----|
| **Firebase Realtime DB** | Live data feed to dashboard | Push-based real-time sync; no polling needed; free tier |
| **PostgreSQL** | Historical data, alerts, reports | Relational queries, joins, aggregations, CSV export |
| **JSON files** | Knowledge base (gas → device → hazard) | Simple, no DB overhead, easy to update |

---

## 8.2 PostgreSQL Schema

### Table: `gas_readings`
```sql
CREATE TABLE gas_readings (
    id              SERIAL PRIMARY KEY,
    reading_id      VARCHAR(36) UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
    device_id       VARCHAR(50) NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    mq2_ppm         FLOAT,
    mq7_ppm         FLOAT,
    mq135_ppm       FLOAT,
    mq303_ppm       FLOAT,
    mq136_ppm       FLOAT,
    temperature_c   FLOAT,
    humidity_pct    FLOAT,
    gas_class       VARCHAR(20),   -- ML prediction
    confidence      FLOAT,         -- ML confidence 0.0-1.0
    risk_level      VARCHAR(10),   -- GREEN / YELLOW / RED
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gas_readings_device_id  ON gas_readings(device_id);
CREATE INDEX idx_gas_readings_timestamp  ON gas_readings(timestamp DESC);
CREATE INDEX idx_gas_readings_risk_level ON gas_readings(risk_level);
CREATE INDEX idx_gas_readings_gas_class  ON gas_readings(gas_class);
```

### Table: `alerts`
```sql
CREATE TABLE alerts (
    id                  SERIAL PRIMARY KEY,
    alert_id            VARCHAR(36) UNIQUE NOT NULL,
    reading_id          VARCHAR(36) REFERENCES gas_readings(reading_id),
    device_id           VARCHAR(50) NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    risk_level          VARCHAR(10) NOT NULL,
    gas_detected        VARCHAR(30) NOT NULL,
    gas_confidence      FLOAT NOT NULL,
    who_limit           FLOAT,
    gas_reading         FLOAT,
    unit                VARCHAR(10),
    exceeded_by_pct     FLOAT DEFAULT 0,
    source_device       VARCHAR(100),
    health_risks        TEXT[],         -- PostgreSQL array
    actions             TEXT[],
    acknowledged        BOOLEAN DEFAULT FALSE,
    acknowledged_at     TIMESTAMPTZ,
    acknowledged_by     VARCHAR(50),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_device_id     ON alerts(device_id);
CREATE INDEX idx_alerts_timestamp     ON alerts(timestamp DESC);
CREATE INDEX idx_alerts_risk_level    ON alerts(risk_level);
CREATE INDEX idx_alerts_acknowledged  ON alerts(acknowledged);
```

### Table: `daily_summaries`
```sql
CREATE TABLE daily_summaries (
    id                  SERIAL PRIMARY KEY,
    summary_date        DATE NOT NULL,
    device_id           VARCHAR(50) NOT NULL,
    total_readings      INT DEFAULT 0,
    green_count         INT DEFAULT 0,
    yellow_count        INT DEFAULT 0,
    red_count           INT DEFAULT 0,
    most_detected_gas   VARCHAR(30),
    avg_mq2_ppm         FLOAT,
    avg_mq7_ppm         FLOAT,
    avg_mq135_ppm       FLOAT,
    avg_mq303_ppm       FLOAT,
    avg_mq136_ppm       FLOAT,
    avg_temperature_c   FLOAT,
    avg_humidity_pct    FLOAT,
    max_risk_event_id   VARCHAR(36),
    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(summary_date, device_id)
);
```

### Table: `devices`
```sql
CREATE TABLE devices (
    id          SERIAL PRIMARY KEY,
    device_id   VARCHAR(50) UNIQUE NOT NULL,
    name        VARCHAR(100),
    location    VARCHAR(200),
    installed_at TIMESTAMPTZ,
    is_active   BOOLEAN DEFAULT TRUE,
    last_seen   TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8.3 Firebase Realtime Database Structure

```
/ewaste_system/
│
├── devices/
│   └── esp32_node_01/
│       ├── status:         "online"
│       ├── last_seen:      "2026-07-31T14:52:00Z"
│       └── current_reading/
│           ├── timestamp:      "2026-07-31T14:52:10Z"
│           ├── mq2_ppm:        45.3
│           ├── mq7_ppm:        12.1
│           ├── mq135_ppm:      8.7
│           ├── mq303_ppm:      0.022
│           ├── mq136_ppm:      0.5
│           ├── temperature_c:  28.4
│           ├── humidity_pct:   65.2
│           ├── risk_level:     "RED"
│           └── gas_detected:   "Mercury Vapor"
│
├── active_alerts/
│   └── ALT-2026073114521/
│       ├── timestamp:      "2026-07-31T14:52:10Z"
│       ├── risk_level:     "RED"
│       ├── gas:            "Mercury Vapor"
│       ├── device_id:      "esp32_node_01"
│       ├── source_device:  "CRT Monitor"
│       └── acknowledged:   false
│
└── system_status/
    ├── online:         true
    └── last_updated:   "2026-07-31T14:52:10Z"
```

---

## 8.4 Knowledge Base JSON Files

### `knowledge_base/gas_profiles.json`
```json
{
  "gas_profiles": {
    "CO": {
      "primary_sensor": "mq7",
      "secondary_sensor": "mq2",
      "typical_ppm_range": [5, 200],
      "color": "#ff6b35",
      "chemical_formula": "CO"
    },
    "MERCURY": {
      "primary_sensor": "mq303",
      "typical_ppm_range": [0.005, 0.5],
      "color": "#c0c0c0",
      "chemical_formula": "Hg"
    }
  }
}
```

### `knowledge_base/device_hazards.json`
```json
{
  "gas_to_device": {
    "CO": {
      "source_devices": ["Printed Circuit Boards (during burning)", "Soldering Process"],
      "health_risks": [
        "Headache and dizziness at 35 ppm",
        "Loss of consciousness at 200 ppm",
        "Fatal within 3 hours at 400 ppm"
      ],
      "actions": [
        "Evacuate area immediately",
        "Ensure fresh air supply",
        "Use CO respirator if re-entry needed",
        "Notify safety officer",
        "Do not re-enter until CO levels confirmed safe"
      ],
      "osha_pel": "50 ppm (8hr TWA)",
      "niosh_rel": "35 ppm (10hr TWA)",
      "who_guideline": "25 ppm (1hr)"
    },
    "MERCURY": {
      "source_devices": ["CRT Monitors", "Flat-screen displays (CCFL backlight)", "Fluorescent lamps"],
      "health_risks": [
        "Neurological damage",
        "Brain damage from chronic exposure",
        "Kidney failure",
        "Respiratory damage"
      ],
      "actions": [
        "Evacuate area immediately",
        "Wear supplied-air respirator (not just a dust mask)",
        "Notify safety officer and environmental health team",
        "Do not handle the device without full PPE",
        "Seal area for professional remediation"
      ],
      "osha_pel": "0.1 mg/m³ (ceiling)",
      "niosh_rel": "0.05 mg/m³",
      "who_guideline": "0.025 mg/m³ (annual average)"
    },
    "H2S": {
      "source_devices": ["Lithium-ion batteries", "Lead-acid batteries", "Soldering materials"],
      "health_risks": [
        "Eye and respiratory irritation at 1-5 ppm",
        "Pulmonary edema at 50-100 ppm",
        "Immediately dangerous to life at 300 ppm"
      ],
      "actions": [
        "Evacuate immediately — H2S rapidly causes unconsciousness",
        "Do not enter to rescue without SCBA",
        "Call emergency services (IDLH: 100 ppm)",
        "Ventilate area from a safe distance"
      ],
      "niosh_idlh": "100 ppm",
      "niosh_ceiling": "1 ppm (10min)"
    },
    "BENZENE": {
      "source_devices": ["Plastic housings during burning", "Cable insulation", "Printed materials on PCBs"],
      "health_risks": [
        "Carcinogen — increases risk of leukemia",
        "Bone marrow damage from chronic exposure",
        "Dizziness and headache at high concentrations"
      ],
      "actions": [
        "Leave area and ventilate",
        "Wear organic vapor respirator",
        "Report to occupational health",
        "Do not continue burning activities"
      ],
      "osha_pel": "1 ppm (8hr TWA)",
      "niosh_rel": "0.1 ppm (lowest feasible)"
    },
    "AMMONIA": {
      "source_devices": ["Nickel-Cadmium batteries", "Nickel-Metal Hydride batteries"],
      "health_risks": [
        "Eye, nose, throat irritation",
        "Pulmonary edema at high levels",
        "Burns to skin and eyes"
      ],
      "actions": [
        "Ventilate area",
        "Wear acid/gas respirator",
        "Flush eyes/skin with water if contact",
        "Isolate leaking batteries"
      ],
      "osha_pel": "50 ppm",
      "niosh_rel": "25 ppm"
    },
    "LPG": {
      "source_devices": ["Capacitors", "Battery packs", "Compressed gas components"],
      "health_risks": [
        "Fire and explosion hazard (LEL: 2.1%)",
        "Asphyxiation in high concentrations",
        "Frostbite from direct contact"
      ],
      "actions": [
        "Eliminate ignition sources immediately",
        "Ventilate area",
        "Evacuate if concentration is rising",
        "Call fire department if source cannot be isolated"
      ],
      "lower_explosive_limit": "2.1% (21000 ppm)"
    },
    "CLEAN": {
      "source_devices": [],
      "health_risks": [],
      "actions": ["Continue normal monitoring"],
      "note": "No hazardous gas detected. System operating normally."
    }
  }
}
```

---

## 8.5 Database Connection Configuration

```python
# db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/ewaste_db"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## 8.6 Data Retention Policy

| Data Type | Retention Period | Storage |
|-----------|-----------------|---------|
| Live readings (Firebase) | Rolling 24 hours | Firebase RT DB |
| All readings (PostgreSQL) | 1 year | PostgreSQL |
| Alerts | Permanent | PostgreSQL |
| Daily summaries | Permanent | PostgreSQL |
| ML training data | Permanent | CSV files in `ml/datasets/` |
