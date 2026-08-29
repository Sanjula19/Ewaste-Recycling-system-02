# API Gateway — E-Waste Recycling System

Lightweight FastAPI reverse-proxy gateway that routes requests to the four
independent component backends. **No business logic lives here.**

---

## Architecture Rule

> **Component 2 (Sanjula — Toxic Gas Detection) is COMPLETELY INDEPENDENT.**
> The gateway provides pass-through routing only.
> It does not chain or orchestrate Component 2 responses into any other workflow.

---

## Port Map

| Service              | Port  |
|----------------------|-------|
| **This gateway**     | 8080  |
| Component 1 backend  | 8001  |
| Component 2 backend  | 8002  |
| Component 3 backend  | 8003  |
| Component 4 backend  | 8004  |

---

## Route Map

| Gateway Route            | Upstream URL              | Component                         |
|--------------------------|---------------------------|-----------------------------------|
| `/api/component1/{path}` | `http://localhost:8001`   | Shehan — AI Waste Assessment      |
| `/api/component2/{path}` | `http://localhost:8002`   | Sanjula — Toxic Gas Detection     |
| `/api/component3/{path}` | `http://localhost:8003`   | Wisu — Smart Process Optimization |
| `/api/component4/{path}` | `http://localhost:8004`   | Mayashi — Economic Valuation      |

All HTTP methods (GET, POST, PUT, DELETE, PATCH) are forwarded.
Query parameters, request bodies, and Content-Type headers are preserved.
Backend status codes are returned unchanged.

---

## Quick Start

```bash
# 1. Install dependencies
cd gateway
pip install -r requirements.txt

# 2. Configure (optional — defaults work for local dev)
cp .env.example .env
# Edit .env if your component backends run on non-default ports.

# 3. Start the gateway
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Gateway is now available at http://localhost:8080
# Interactive API docs: http://localhost:8080/docs
```

---

## Environment Variables

Defined in `.env` (copy from `.env.example`):

| Variable          | Default                   | Description                          |
|-------------------|---------------------------|--------------------------------------|
| `GATEWAY_PORT`    | `8080`                    | Port the gateway listens on          |
| `COMPONENT1_URL`  | `http://localhost:8001`   | Component 1 backend base URL         |
| `COMPONENT2_URL`  | `http://localhost:8002`   | Component 2 backend base URL         |
| `COMPONENT3_URL`  | `http://localhost:8003`   | Component 3 backend base URL         |
| `COMPONENT4_URL`  | `http://localhost:8004`   | Component 4 backend base URL         |
| `PROXY_TIMEOUT`   | `30`                      | Upstream request timeout (seconds)   |
| `HEALTH_TIMEOUT`  | `5`                       | Health-check timeout (seconds)       |
| `CORS_ORIGINS`    | `*`                       | Comma-separated CORS origins (or `*`)|

---

## Endpoints

### Gateway health

```
GET http://localhost:8080/health
```

Response (example — all backends running):
```json
{
  "gateway": "ok",
  "timestamp": "2026-08-29T05:30:00+00:00",
  "uptime_seconds": 42.3,
  "overall_status": "ok",
  "services": {
    "component1": { "service": "component1", "url": "http://localhost:8001", "status": "ok", "http_code": 200 },
    "component2": { "service": "component2", "url": "http://localhost:8002", "status": "ok", "http_code": 200 },
    "component3": { "service": "component3", "url": "http://localhost:8003", "status": "ok", "http_code": 200 },
    "component4": { "service": "component4", "url": "http://localhost:8004", "status": "ok", "http_code": 200 }
  },
  "routes": {
    "/api/component1/*": "http://localhost:8001",
    "/api/component2/*": "http://localhost:8002",
    "/api/component3/*": "http://localhost:8003",
    "/api/component4/*": "http://localhost:8004"
  }
}
```

When a backend is down, its entry shows `"status": "unavailable"` — the gateway
itself still returns HTTP 200 so monitoring tools can distinguish between
"gateway is down" and "one component is temporarily unavailable".

---

## curl Examples

### Gateway self-check
```bash
curl http://localhost:8080/health
```

### Component 1 — AI Waste Assessment (Shehan)
```bash
# Health
curl http://localhost:8080/api/component1/health

# General waste prediction (multipart image)
curl -X POST http://localhost:8080/api/component1/waste/predict \
     -F "file=@/path/to/image.jpg"

# E-waste analysis
curl -X POST http://localhost:8080/api/component1/ewaste/analyze \
     -F "file=@/path/to/ewaste.jpg"
```

### Component 2 — Toxic Gas Detection (Sanjula) — INDEPENDENT
```bash
# Health
curl http://localhost:8080/api/component2/api/v1/health

# MQTT connection status
curl http://localhost:8080/api/component2/api/v1/mqtt/status

# Latest gas reading
curl http://localhost:8080/api/component2/api/v1/readings/latest

# Paginated readings
curl "http://localhost:8080/api/component2/api/v1/readings?limit=20&offset=0"

# Dashboard stats
curl http://localhost:8080/api/component2/api/v1/dashboard/stats

# Active alerts
curl http://localhost:8080/api/component2/api/v1/alerts
```

### Component 3 — Smart Process Optimization (Wisu)
```bash
# Health
curl http://localhost:8080/api/component3/api/health

# Supported materials
curl http://localhost:8080/api/component3/api/materials

# Generate a process recipe
curl -X POST http://localhost:8080/api/component3/api/optimize \
     -H "Content-Type: application/json" \
     -d '{"material_name": "PET Water Bottles", "waste_type": "Plastic", "weight_kg": 5.0, "moisture_condition": "Wet"}'

# Past optimization results
curl http://localhost:8080/api/component3/api/history

# Latest SHEF moisture sensor reading
curl http://localhost:8080/api/component3/api/sensor/moisture/latest
```

### Component 4 — Economic Valuation (Mayashi)
```bash
# Health
curl http://localhost:8080/api/component4/api/health

# Supported metals list
curl http://localhost:8080/api/component4/api/forecast/supported-metals

# 90-day price forecast for copper (500 kg)
curl -X POST http://localhost:8080/api/component4/api/forecast/ \
     -H "Content-Type: application/json" \
     -d '{"metal": "copper", "weight_kg": 500}'

# Market overview
curl http://localhost:8080/api/component4/api/market/overview

# Manifest summary
curl http://localhost:8080/api/component4/api/manifest/summary
```

---

## Error Responses

| HTTP Status | Meaning                                      |
|-------------|----------------------------------------------|
| `503`       | Backend unreachable (ConnectError)           |
| `504`       | Backend did not respond within timeout       |
| `502`       | Unexpected proxy error                       |

All proxy errors return JSON:
```json
{
  "error": "service_unavailable",
  "detail": "Cannot connect to upstream at http://localhost:8001. ...",
  "upstream": "http://localhost:8001"
}
```

---

## File Structure

```
gateway/
├── app/
│   ├── __init__.py
│   ├── config.py       # Settings loaded from .env
│   ├── proxy.py        # Core reverse-proxy + health ping logic
│   └── main.py         # FastAPI app, CORS, route handlers
├── .env                # Active config (not committed to git)
├── .env.example        # Config template
├── requirements.txt    # Gateway-only dependencies
└── README.md           # This file
```
