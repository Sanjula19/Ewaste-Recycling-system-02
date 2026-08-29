# gateway/app/main.py
# -------------------
# Lightweight API Gateway — routing only, no business logic.
#
# Routes
# ------
#   GET  /health                    Gateway self-health + per-service ping
#   ANY  /api/component1/{path:path} -> Component 1 (http://localhost:8001)
#   ANY  /api/component2/{path:path} -> Component 2 (http://localhost:8002)
#   ANY  /api/component3/{path:path} -> Component 3 (http://localhost:8003)
#   ANY  /api/component4/{path:path} -> Component 4 (http://localhost:8004)
#
# Architecture rule: Component 2 is COMPLETELY INDEPENDENT.
# The gateway only routes requests — it does not chain or orchestrate
# business logic between components.

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.proxy import forward_request, ping_service

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gateway")

# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(
    title="E-Waste Recycling System — API Gateway",
    version="1.0.0",
    description=(
        "Lightweight routing gateway. Forwards requests to the four "
        "component backends. No business logic lives here."
    ),
)

# ── CORS ─────────────────────────────────────────────────────────────────
# Allow the future common frontend (and individual component frontends)
# to call the gateway from the browser.
_cors_origins = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup banner ────────────────────────────────────────────────────────
_START_TIME = time.time()


@app.on_event("startup")
async def _on_startup():
    logger.info("=" * 60)
    logger.info("API Gateway starting on port %s", settings.gateway_port)
    logger.info("  Component 1 -> %s", settings.component1_url)
    logger.info("  Component 2 -> %s", settings.component2_url)
    logger.info("  Component 3 -> %s", settings.component3_url)
    logger.info("  Component 4 -> %s", settings.component4_url)
    logger.info("=" * 60)


# ── Health endpoint ───────────────────────────────────────────────────────

@app.get("/health", tags=["Gateway"])
async def gateway_health():
    """
    Gateway self-health plus an async ping of every component backend.
    Returns 200 even when individual backends are down so that a load
    balancer / monitoring tool can distinguish between the gateway being
    unreachable and a component being temporarily unavailable.
    """
    # Ping all four backends concurrently to keep response latency low
    results = await asyncio.gather(
        ping_service(
            "component1",
            settings.component1_url,
            settings.health_paths["component1"],
            settings.health_timeout,
        ),
        ping_service(
            "component2",
            settings.component2_url,
            settings.health_paths["component2"],
            settings.health_timeout,
        ),
        ping_service(
            "component3",
            settings.component3_url,
            settings.health_paths["component3"],
            settings.health_timeout,
        ),
        ping_service(
            "component4",
            settings.component4_url,
            settings.health_paths["component4"],
            settings.health_timeout,
        ),
    )

    services = {r["service"]: r for r in results}
    all_ok = all(r["status"] == "ok" for r in results)

    return {
        "gateway": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "overall_status": "ok" if all_ok else "degraded",
        "services": services,
        "routes": {
            "/api/component1/*": settings.component1_url,
            "/api/component2/*": settings.component2_url,
            "/api/component3/*": settings.component3_url,
            "/api/component4/*": settings.component4_url,
        },
    }


# ── Root redirect ─────────────────────────────────────────────────────────

@app.get("/", tags=["Gateway"])
async def root():
    return {
        "service": "E-Waste Recycling System API Gateway",
        "version": "1.0.0",
        "health": "/health",
        "docs": "/docs",
        "routes": {
            "component1": "/api/component1/<path>",
            "component2": "/api/component2/<path>",
            "component3": "/api/component3/<path>",
            "component4": "/api/component4/<path>",
        },
    }


# ── Component 1 — Shehan (AI Waste Assessment) ────────────────────────────
# Backend: http://localhost:8001
# Architecture: Component 2 is INDEPENDENT — not connected here.

@app.api_route(
    "/api/component1/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    tags=["Component 1 — AI Waste Assessment"],
    summary="Proxy to Component 1 backend (port 8001)",
)
async def proxy_component1(path: str, request: Request) -> Response:
    return await forward_request(
        request,
        upstream_base=settings.component1_url,
        upstream_path=f"/{path}",
        timeout=settings.proxy_timeout,
    )


# ── Component 2 — Sanjula (Toxic Gas Detection) ───────────────────────────
# Backend: http://localhost:8002
# ARCHITECTURE RULE: Component 2 is COMPLETELY INDEPENDENT.
# This route only provides pass-through access. The gateway does NOT
# chain Component 2 responses into Component 1, 3, or 4 workflows.

@app.api_route(
    "/api/component2/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    tags=["Component 2 — Toxic Gas Detection (Independent)"],
    summary="Proxy to Component 2 backend (port 8002) — independent module",
)
async def proxy_component2(path: str, request: Request) -> Response:
    return await forward_request(
        request,
        upstream_base=settings.component2_url,
        upstream_path=f"/{path}",
        timeout=settings.proxy_timeout,
    )


# ── Component 3 — Wisu (Smart Process Optimization) ──────────────────────
# Backend: http://localhost:8003

@app.api_route(
    "/api/component3/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    tags=["Component 3 — Smart Process Optimization"],
    summary="Proxy to Component 3 backend (port 8003)",
)
async def proxy_component3(path: str, request: Request) -> Response:
    return await forward_request(
        request,
        upstream_base=settings.component3_url,
        upstream_path=f"/{path}",
        timeout=settings.proxy_timeout,
    )


# ── Component 4 — Mayashi (Predictive Economic Valuation) ────────────────
# Backend: http://localhost:8004

@app.api_route(
    "/api/component4/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    tags=["Component 4 — Predictive Economic Valuation"],
    summary="Proxy to Component 4 backend (port 8004)",
)
async def proxy_component4(path: str, request: Request) -> Response:
    return await forward_request(
        request,
        upstream_base=settings.component4_url,
        upstream_path=f"/{path}",
        timeout=settings.proxy_timeout,
    )
