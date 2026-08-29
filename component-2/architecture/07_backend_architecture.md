# 07 — Backend Architecture

## 7.1 Backend Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Framework | FastAPI (Python) | Async support, auto-docs, Pydantic validation, fast |
| ASGI Server | Uvicorn | Production-grade async server for FastAPI |
| MQTT Client | aiomqtt (async) | Non-blocking MQTT for FastAPI async context |
| ML Runtime | scikit-learn + joblib | Same library as training → no conversion needed |
| DB ORM | SQLAlchemy (async) | Industry-standard Python ORM |
| DB Migrations | Alembic | Schema versioning for PostgreSQL |
| Validation | Pydantic v2 | Type-safe data models, request/response validation |
| Firebase | firebase-admin | Backend writes to Firebase Realtime DB |
| Config | python-dotenv | Environment variable management |
| Testing | pytest + httpx | API endpoint testing |

---

## 7.2 FastAPI Application Structure

```
backend/app/
├── main.py                    ← App entry, lifespan, middleware, router
├── config.py                  ← All settings from .env
│
├── api/v1/
│   ├── router.py              ← APIRouter aggregator
│   ├── gas_readings.py        ← /readings/* endpoints
│   ├── alerts.py              ← /alerts/* endpoints
│   ├── predictions.py         ← /predict/* endpoints
│   ├── reports.py             ← /reports/* endpoints
│   └── health.py              ← /health endpoint
│
├── services/
│   ├── ml_service.py          ← Model loading + inference
│   ├── mqtt_service.py        ← Async MQTT subscriber loop
│   ├── knowledge_base_service.py ← JSON KB lookup
│   ├── threshold_service.py   ← WHO ppm comparison
│   ├── alert_service.py       ← Alert creation + dispatch
│   └── firebase_service.py    ← Firebase Admin SDK writer
│
├── models/                    ← Pydantic schemas
│   ├── gas_reading.py
│   ├── alert.py
│   ├── prediction.py
│   └── report.py
│
├── db/
│   ├── database.py            ← SQLAlchemy engine + session factory
│   └── schemas/               ← SQL DDL files
│
└── middleware/
    ├── cors.py
    ├── rate_limiter.py
    └── auth.py
```

---

## 7.3 main.py Application Lifecycle

```python
# Startup: Load ML models, connect MQTT, connect DBs
# Running: Handle HTTP requests + background MQTT loop
# Shutdown: Graceful disconnect MQTT, close DB connections

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    await ml_service.load_models()          # Load .pkl files
    await firebase_service.initialize()     # Init Firebase Admin
    asyncio.create_task(mqtt_service.start_subscriber())  # Background task
    db_engine = await database.connect()   # PostgreSQL connection pool

    yield   # App runs here

    # --- SHUTDOWN ---
    await mqtt_service.stop()
    await database.disconnect()
```

---

## 7.4 Service Interaction Diagram

```
                MQTT Message Arrives
                        │
                        ▼
              ┌──────────────────┐
              │  mqtt_service.py │
              │  on_message()    │
              └────────┬─────────┘
                       │
          ┌────────────┼──────────────┐
          │            │              │
          ▼            ▼              ▼
  ┌─────────────┐ ┌──────────┐ ┌────────────┐
  │ ml_service  │ │threshold │ │  firebase  │
  │ .classify() │ │_service  │ │  _service  │
  │             │ │.evaluate()│ │  .write()  │
  └──────┬──────┘ └────┬─────┘ └────────────┘
         │             │
         └──────┬───────┘
                │ combined result
                ▼
     ┌─────────────────────┐
     │ knowledge_base      │
     │ _service.lookup()   │
     └──────────┬──────────┘
                │
                ▼
     ┌─────────────────────┐
     │ alert_service       │
     │ .create_alert()     │
     │   → save PostgreSQL │
     │   → push Firebase   │
     │   → MQTT command    │
     │     to ESP32        │
     └─────────────────────┘
```

---

## 7.5 Pydantic Models (Schemas)

### GasReading (Input from MQTT)
```python
class SensorData(BaseModel):
    mq2_ppm:        float = Field(..., ge=0, le=10000)
    mq7_ppm:        float = Field(..., ge=0, le=1000)
    mq135_ppm:      float = Field(..., ge=0, le=10000)
    mq303_ppm:      float = Field(..., ge=0, le=100)
    mq136_ppm:      float = Field(..., ge=0, le=200)
    temperature_c:  float = Field(..., ge=-40, le=80)
    humidity_pct:   float = Field(..., ge=0, le=100)

class GasReadingPayload(BaseModel):
    device_id:   str
    timestamp:   datetime
    sensors:     SensorData
    environment: EnvironmentData
```

### Alert (Output)
```python
class RiskLevel(str, Enum):
    GREEN  = "GREEN"
    YELLOW = "YELLOW"
    RED    = "RED"

class AlertResponse(BaseModel):
    alert_id:          str
    timestamp:         datetime
    device_id:         str
    risk_level:        RiskLevel
    gas_detected:      str
    gas_confidence:    float
    readings:          SensorData
    who_comparison:    WHOComparison
    source_device:     str
    health_risks:      List[str]
    actions:           List[str]
```

---

## 7.6 ML Service Design

```python
# services/ml_service.py

class MLService:
    def __init__(self):
        self.model = None
        self.label_encoder = None
        self.scaler = None
        self.model_version = None

    async def load_models(self):
        MODEL_DIR = Path("ml_models/")
        self.model         = joblib.load(MODEL_DIR / "random_forest_v1.pkl")
        self.label_encoder = joblib.load(MODEL_DIR / "label_encoder.pkl")
        self.scaler        = joblib.load(MODEL_DIR / "scaler.pkl")
        self.model_version = "rf_v1"

    def classify(self, sensors: SensorData) -> PredictionResult:
        features = [[
            sensors.mq2_ppm,
            sensors.mq7_ppm,
            sensors.mq135_ppm,
            sensors.mq303_ppm,
            sensors.mq136_ppm,
            sensors.temperature_c,
            sensors.humidity_pct
        ]]
        features_scaled = self.scaler.transform(features)
        pred_idx        = self.model.predict(features_scaled)[0]
        probabilities   = self.model.predict_proba(features_scaled)[0]
        confidence      = float(probabilities.max())
        gas_class       = self.label_encoder.inverse_transform([pred_idx])[0]

        return PredictionResult(
            gas_class=gas_class,
            confidence=confidence,
            model_version=self.model_version
        )
```

---

## 7.7 WHO Threshold Service

```python
# services/threshold_service.py

WHO_LIMITS = {
    "CO":       {"limit": 25.0,    "unit": "ppm",    "sensor": "mq7"},
    "LPG":      {"limit": 1000.0,  "unit": "ppm",    "sensor": "mq2"},
    "BENZENE":  {"limit": 0.5,     "unit": "ppm",    "sensor": "mq135"},
    "AMMONIA":  {"limit": 25.0,    "unit": "ppm",    "sensor": "mq135"},
    "MERCURY":  {"limit": 0.025,   "unit": "mg/m3",  "sensor": "mq303"},
    "H2S":      {"limit": 1.0,     "unit": "ppm",    "sensor": "mq136"},
}

def evaluate_risk(gas_class: str, sensors: SensorData) -> RiskResult:
    limit_info = WHO_LIMITS[gas_class]
    reading    = getattr(sensors, f"{limit_info['sensor']}_ppm")
    limit      = limit_info["limit"]
    ratio      = reading / limit

    if ratio < 0.5:
        level = RiskLevel.GREEN
    elif ratio < 1.0:
        level = RiskLevel.YELLOW
    else:
        level = RiskLevel.RED

    exceeded_pct = max(0, (ratio - 1.0) * 100) if ratio > 1.0 else 0

    return RiskResult(
        risk_level=level,
        reading=reading,
        who_limit=limit,
        unit=limit_info["unit"],
        exceeded_by_pct=exceeded_pct
    )
```

---

## 7.8 API Documentation

FastAPI auto-generates interactive documentation:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

> These pages are extremely useful for demonstrating your API during the research presentation.
