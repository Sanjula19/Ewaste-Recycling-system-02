# Component 3 — "Smart Process Optimization" (Wisu) — CURRENT BACKEND STATE
# ---------------------------------------------------------------------------
# IMPORTANT: this container currently packages the SAME toxic-gas-detection
# backend as Component 2 (see integration/contracts/component3-contract.md
# and integration/INTEGRATION_STATUS.md). It exposes /api/v1/health,
# /api/v1/readings, /api/v1/predict (gas classification), etc. — it does NOT
# implement /api/optimize, /api/materials, or /api/history. This Dockerfile
# containerizes ONLY what currently exists in component-3/backend; it does
# NOT fabricate the real Smart Process Optimization API. Replace the source
# under component-3/backend/ with the real implementation and this Dockerfile
# will not need structural changes (same layout: app/main.py, requirements.txt).
#
# Runtime: Python 3.11 (per component-2/architecture/13_technology_stack.md —
# component-3's backend is currently identical to component-2's).
# Entry point: app/main.py -> FastAPI instance `app` (uvicorn app.main:app).

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

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8003/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
