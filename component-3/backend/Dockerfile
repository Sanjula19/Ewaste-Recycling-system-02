# Component 3 — Smart Process Optimization (Wisu) — REAL backend
# ---------------------------------------------------------------------------
# This replaces the earlier Dockerfile, which containerized a wrong,
# toxic-gas-clone backend (see integration/INTEGRATION_STATUS.md history).
# The real Smart Process Optimization implementation was placed here in
# Step 5A: Decision Tree (model.pkl) + MCDM (energy_service.py) + rule-based
# safety engine (safety_service.py), with results persisted to Firestore.
#
# Runtime: Python 3.11 (no version pin found in the project; 3.11 satisfies
# scikit-learn==1.3.2, pandas, numpy, scipy, firebase-admin).
# Entry point: app/main.py -> FastAPI instance `app` (uvicorn app.main:app).
#
# KNOWN ISSUE: app/firebase_key.json (a real Firebase service-account key)
# is required for Firestore persistence (/api/history, and /api/optimize's
# save step) but is intentionally NOT copied into the image and NOT
# committed to git (see component-3/.gitignore). Without it, Firebase
# connection fails gracefully at startup (logged, not fatal) and
# /api/optimize still returns a full result — it just cannot save/retrieve
# history. Mount it at runtime (e.g. a bind mount or secret) if Firestore
# persistence is needed in this container.

FROM python:3.11-slim-bookworm

WORKDIR /app

# STEP 7 FIX carried forward: some Docker Desktop network setups block
# plain-HTTP egress and return "403 Forbidden" for the default
# http://deb.debian.org mirror. Forcing HTTPS fixes `apt-get update` without
# changing which packages are installed.
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

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8003/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
