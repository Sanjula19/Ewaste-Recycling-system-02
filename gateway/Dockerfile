# API Gateway — routing only, no business logic.
# ---------------------------------------------------------------------------
# Runtime: Python 3.11 (consistent with the other services; the gateway has
# no heavy dependencies so any recent 3.x would do).
# Entry point: app/main.py -> FastAPI instance `app` (uvicorn app.main:app).
#
# Component URLs are provided at runtime via environment variables
# (COMPONENT1_URL..COMPONENT4_URL) — see docker-compose.yml. Inside Docker
# these MUST be service names (http://component1:8001, etc.), not localhost.

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
