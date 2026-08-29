# Component 4 — Predictive Economic Valuation (Mayashi)
# ---------------------------------------------------------------------------
# Runtime: Python 3.11 (no version pin found; tensorflow==2.17.0 supports
# 3.9-3.12).
# Entry point: main.py -> FastAPI instance `app` (uvicorn main:app).
#
# InfluxDB is OPTIONAL — services/influx_client.py + fx_service.py fall back
# to the historical CSVs in data/ and cached FX rates when it is unset or
# unreachable, per component-4/backend/.env.example. This Dockerfile does not
# require an InfluxDB container to run.

FROM python:3.11-slim

WORKDIR /app

# libgomp1: required by tensorflow's CPU runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py data_loader.py materials_db.py ./
COPY routers/ ./routers/
COPY schemas/ ./schemas/
COPY services/ ./services/
COPY data/ ./data/
COPY models/ ./models/

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8004/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
