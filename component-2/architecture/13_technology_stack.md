# 13 — Complete Technology Stack

## 13.1 Full Stack Summary

```
┌──────────────────────────────────────────────────────────────────┐
│                    TECHNOLOGY STACK                              │
├─────────────────┬────────────────────────┬─────────────────────-┤
│ Layer           │ Technology             │ Justification         │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ HARDWARE        │                        │                       │
│ Microcontroller │ ESP32 DevKit V1        │ WiFi built-in, 12-bit │
│                 │                        │ ADC, dual-core, cheap │
│ Gas Sensors     │ MQ-2, 7, 135, 303, 136 │ Covers all 6 target   │
│                 │                        │ e-waste gases         │
│ Env Sensor      │ DHT22                  │ Calibration accuracy  │
│ Display         │ LCD 16x2 I2C           │ Local readout, I2C    │
│ Alerts          │ LED ×3 + Active Buzzer │ Simple, reliable      │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ FIRMWARE        │                        │                       │
│ IDE             │ Arduino IDE 2.x        │ ESP32 support, free   │
│ Language        │ C++ (Arduino)          │ Standard for ESP32    │
│ MQTT Library    │ PubSubClient           │ Lightweight MQTT for  │
│                 │                        │ Arduino/ESP32         │
│ JSON Library    │ ArduinoJson 6.x        │ JSON serialize/parse  │
│ DHT Library     │ DHT sensor library     │ DHT22 reading         │
│ LCD Library     │ LiquidCrystal_I2C      │ I2C LCD control       │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ COMMUNICATION   │                        │                       │
│ Protocol        │ MQTT v3.1.1            │ Lightweight IoT       │
│                 │                        │ protocol, QoS support │
│ Broker          │ HiveMQ Cloud           │ Free, TLS, reliable   │
│ Security        │ TLS 1.2 + Auth         │ Encrypted transport   │
│ REST            │ HTTP/HTTPS             │ Dashboard ↔ Backend   │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ BACKEND         │                        │                       │
│ Framework       │ FastAPI (Python)       │ Async, auto-docs,     │
│                 │                        │ fast, modern          │
│ Server          │ Uvicorn                │ ASGI, production-     │
│                 │                        │ grade                 │
│ Language        │ Python 3.11+           │ ML ecosystem best     │
│ Validation      │ Pydantic v2            │ Type-safe models      │
│ MQTT client     │ aiomqtt                │ Async MQTT for FastAPI│
│ ORM             │ SQLAlchemy 2.0 (async) │ Industry standard     │
│ Migrations      │ Alembic                │ Schema versioning     │
│ Firebase        │ firebase-admin SDK     │ Realtime DB writes    │
│ Testing         │ pytest + httpx         │ API testing           │
│ Config          │ python-dotenv          │ .env management       │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ MACHINE LEARNING│                        │                       │
│ Language        │ Python 3.11+           │ ML ecosystem          │
│ Main ML lib     │ scikit-learn 1.3+      │ RF, SVM, DT, NB       │
│ Data processing │ pandas 2.x             │ DataFrame operations  │
│ Numerical       │ NumPy 1.24+            │ Array math            │
│ Imbalance       │ imbalanced-learn       │ SMOTE oversampling    │
│ Visualization   │ matplotlib + seaborn   │ Plots for paper       │
│ Notebooks       │ Jupyter Notebook       │ Interactive ML dev    │
│ Model saving    │ joblib                 │ .pkl model files      │
│ Primary model   │ Random Forest          │ Best for tabular,     │
│                 │                        │ interpretable, robust │
│ Comparison      │ SVM, DT, Naive Bayes   │ Baseline comparison   │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ DATABASE        │                        │                       │
│ Real-time       │ Firebase RT DB         │ Push updates, free    │
│ Historical      │ PostgreSQL 15+         │ ACID, queries, joins  │
│ DB hosting      │ Supabase (free)        │ Managed PostgreSQL    │
│ Knowledge base  │ JSON files             │ Simple, updatable     │
│ Training data   │ CSV files              │ Pandas-native         │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ FRONTEND        │                        │                       │
│ Framework       │ React.js 18            │ Component model,      │
│                 │                        │ ecosystem, Firebase   │
│ Routing         │ React Router v6        │ SPA routing           │
│ Charts          │ Recharts 2.x           │ React-native charts   │
│ API client      │ Axios                  │ HTTP client           │
│ State           │ Context API + Hooks    │ No extra deps needed  │
│ Styling         │ Tailwind CSS           │ Rapid UI development  │
│ Real-time       │ Firebase JS SDK 10     │ onValue() listener    │
│ Build tool      │ Vite                   │ Fast dev server       │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ DEPLOYMENT      │                        │                       │
│ Backend         │ Render.com             │ Free, GitHub deploy   │
│ Frontend        │ Vercel                 │ Free, instant CDN     │
│ Database        │ Supabase               │ Free managed PG       │
│ Realtime DB     │ Firebase (Spark)       │ Free 1GB              │
│ MQTT Broker     │ HiveMQ Cloud           │ Free cluster          │
│ Container       │ Docker                 │ Optional for local    │
├─────────────────┼────────────────────────┼──────────────────────-┤
│ DEV TOOLS       │                        │                       │
│ IDE             │ VS Code                │ Universal, extensions │
│ Hardware IDE    │ Arduino IDE 2.x        │ ESP32 support         │
│ Version control │ GitHub                 │ CI/CD integration     │
│ API testing     │ Postman                │ Endpoint testing      │
│ DB GUI          │ DBeaver (free)         │ PostgreSQL management │
│ Firebase GUI    │ Firebase Console       │ RT DB management      │
└─────────────────┴────────────────────────┴──────────────────────-┘
```

---

## 13.2 Python Requirements (`backend/requirements.txt`)

```
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0

# MQTT (async)
aiomqtt==1.2.1

# Database
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
alembic==1.12.1

# Firebase
firebase-admin==6.2.0

# ML Runtime
scikit-learn==1.3.2
numpy==1.24.4
joblib==1.3.2

# Testing
pytest==7.4.3
httpx==0.25.2
pytest-asyncio==0.21.1

# Utilities
python-multipart==0.0.6
```

---

## 13.3 Python ML Requirements (`ml/requirements.txt`)

```
# Core ML
scikit-learn==1.3.2
pandas==2.1.3
numpy==1.24.4
imbalanced-learn==0.11.0
joblib==1.3.2

# Visualization
matplotlib==3.8.2
seaborn==0.13.0

# Notebooks
jupyter==1.0.0
ipykernel==6.27.1

# Utilities
scipy==1.11.4
```

---

## 13.4 Arduino Libraries (`hardware/libraries.txt`)

```
# Install via Arduino Library Manager:
PubSubClient           by Nick O'Leary    # MQTT client
ArduinoJson            by Benoit Blanchon # JSON parsing/creation
DHT sensor library     by Adafruit        # DHT22 support
Adafruit Unified Sensor by Adafruit       # DHT dependency
LiquidCrystal I2C      by Frank de Brabander # LCD I2C

# ESP32 Board Support (via Board Manager URL):
# https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

---

## 13.5 Frontend Dependencies (`frontend/package.json`)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "recharts": "^2.10.1",
    "axios": "^1.6.2",
    "firebase": "^10.7.0"
  },
  "devDependencies": {
    "vite": "^5.0.6",
    "@vitejs/plugin-react": "^4.2.1",
    "tailwindcss": "^3.3.6",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32"
  }
}
```
