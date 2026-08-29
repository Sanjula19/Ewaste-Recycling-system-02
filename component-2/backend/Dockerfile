# Component 2 — Toxic Gas Detection (Sanjula)
# ---------------------------------------------------------------------------
# COMPLETELY INDEPENDENT SERVICE — not part of the C1 -> C3 -> C4 workflow.
# Runtime: Python 3.11 (per component-2/architecture/13_technology_stack.md).
# Entry point: app/main.py -> FastAPI instance `app` (uvicorn app.main:app).
#
# On startup this service connects to a real HiveMQ Cloud MQTT broker over
# TLS (see app/config.py / backend/.env) — it needs outbound internet access
# to receive live ESP32 sensor data. Its SQLite database
# (component2_ewaste_gas.db) is written at the path in DATABASE_URL; the
# compose file points this at a mounted volume so data survives restarts.

FROM python:3.11-slim-bookworm

WORKDIR /app

# STEP 7 FIX: some Docker Desktop network setups block plain-HTTP egress and
# return "403 Forbidden" for the default http://deb.debian.org mirror. Forcing
# both the classic sources.list and the newer deb822 sources.list.d format to
# HTTPS fixes `apt-get update` without changing which packages are installed.
RUN if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g; s|http://security.debian.org|https://security.debian.org|g' /etc/apt/sources.list; \
    fi; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g; s|http://security.debian.org|https://security.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY knowledge_base/ ./knowledge_base/
COPY ml_models/ ./ml_models/

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8002/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
