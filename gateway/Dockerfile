# API Gateway — routing only, no business logic.
# ---------------------------------------------------------------------------
# Runtime: Python 3.11 (consistent with the other services; the gateway has
# no heavy dependencies so any recent 3.x would do).
# Entry point: app/main.py -> FastAPI instance `app` (uvicorn app.main:app).
#
# Component URLs are provided at runtime via environment variables
# (COMPONENT1_URL..COMPONENT4_URL) — see docker-compose.yml. Inside Docker
# these MUST be service names (http://component1:8001, etc.), not localhost.

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

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
