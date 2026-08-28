# 11 — Deployment Architecture

## 11.1 Deployment Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                        │
│                                                                 │
│  ┌─────────────────┐                                           │
│  │   ESP32 Device  │                                           │
│  │   (Physical)    │                                           │
│  └────────┬────────┘                                           │
│           │ MQTT/TLS                                           │
│           ▼                                                     │
│  ┌─────────────────────┐     ┌──────────────────────────────┐  │
│  │  HiveMQ Cloud       │────►│  Render.com                  │  │
│  │  (MQTT Broker)      │     │  (FastAPI Backend)            │  │
│  │  Free Tier          │     │  Free Tier                   │  │
│  └─────────────────────┘     │  URL: ewaste-api.onrender.com│  │
│                               └──────────────┬───────────────┘  │
│                                              │                  │
│           ┌──────────────────────────────────┤                  │
│           │                                  │                  │
│  ┌────────▼────────────┐          ┌──────────▼──────────────┐  │
│  │  Firebase RT DB     │          │  PostgreSQL              │  │
│  │  (Live data)        │          │  (Supabase free tier)    │  │
│  │  Free Tier          │          │  Free Tier               │  │
│  └────────┬────────────┘          └─────────────────────────-┘  │
│           │ Firebase SDK                                         │
│  ┌────────▼────────────────────────────────────────────────┐    │
│  │  Vercel                                                 │    │
│  │  (React.js Dashboard)                                   │    │
│  │  Free Tier                                              │    │
│  │  URL: ewaste-dashboard.vercel.app                       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11.2 Service-by-Service Deployment

### Backend — Render.com

| Setting | Value |
|---------|-------|
| Service Type | Web Service |
| Runtime | Python 3.11 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Environment | Set all `.env` variables in Render dashboard |
| Free Tier | 750 hrs/month, sleeps after 15min inactivity |
| URL | `https://ewaste-api.onrender.com` |

> ⚠️ **Free tier limitation:** Render free tier sleeps after 15 minutes of inactivity. For demos, wake up the API by hitting `/health` first, or use Render's UptimeRobot integration to keep it awake.

### Frontend — Vercel

| Setting | Value |
|---------|-------|
| Framework | React (Vite or Create React App) |
| Build Command | `npm run build` |
| Output Directory | `dist` or `build` |
| Deploy Trigger | Push to `main` branch on GitHub |
| Environment Variables | Set `VITE_API_URL`, `VITE_FIREBASE_*` in Vercel dashboard |
| Free Tier | Unlimited deploys, 100GB bandwidth |
| URL | `https://ewaste-dashboard.vercel.app` |

### Database — PostgreSQL (Supabase)

| Setting | Value |
|---------|-------|
| Provider | Supabase (free PostgreSQL in cloud) |
| Free Tier | 500MB storage, 2GB bandwidth |
| Connection | `postgresql://...@db.supabase.co:5432/postgres` |
| Auth | Connection string with password |

> **Alternative:** Use Render's included PostgreSQL service (free, 256MB)

### MQTT Broker — HiveMQ Cloud

| Setting | Value |
|---------|-------|
| Plan | Free Cluster |
| Max Connections | 100 |
| Max Messages | 10k/month |
| TLS Port | 8883 |
| WebSocket Port | 8884 |

---

## 11.3 Docker Configuration (Optional)

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-load ML models into image
COPY ml_models/ ./ml_models/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml (for local development)
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/ewaste_db
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ewaste_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## 11.4 Environment Variables

### Backend `.env.example`
```env
# MQTT
MQTT_BROKER_HOST=abc123.s2.eu.hivemq.cloud
MQTT_BROKER_PORT=8883
MQTT_USERNAME=ewaste_backend
MQTT_PASSWORD=your_secure_password

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/ewaste_db

# Firebase
FIREBASE_CREDENTIALS_PATH=firebase-service-account.json
FIREBASE_DATABASE_URL=https://ewaste-system-default-rtdb.firebaseio.com

# API Security
API_KEY=your_api_key_here
ALLOWED_ORIGINS=https://ewaste-dashboard.vercel.app,http://localhost:3000

# App
APP_ENV=production
DEBUG=false
```

### Frontend `.env.example`
```env
VITE_API_BASE_URL=https://ewaste-api.onrender.com/api/v1
VITE_API_KEY=your_api_key_here

# Firebase (safe to expose - protected by Firebase security rules)
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=ewaste-system.firebaseapp.com
VITE_FIREBASE_DATABASE_URL=https://ewaste-system-default-rtdb.firebaseio.com
VITE_FIREBASE_PROJECT_ID=ewaste-system
```

---

## 11.5 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml

name: Deploy on Push

on:
  push:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ -v

  # Render auto-deploys on push to main (configured in Render)
  # Vercel auto-deploys on push to main (configured in Vercel)
```

---

## 11.6 Total Cost Summary

| Service | Plan | Cost |
|---------|------|------|
| HiveMQ Cloud | Free | $0/month |
| Render.com | Free Web Service | $0/month |
| Supabase | Free tier | $0/month |
| Firebase | Spark (free) | $0/month |
| Vercel | Hobby (free) | $0/month |
| GitHub | Free | $0/month |
| **Hardware** | One-time | ~$34 |
| **TOTAL** | | **~$34 total** |
