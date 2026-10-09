import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import forecast, disposition, iot, manifest, market, fx
from services import market_service, pretrained_models

# Without a root handler, logger.info() below goes nowhere (logging's
# last-resort handler only passes WARNING and above). uvicorn configures its
# own loggers with propagate=False, so this does not duplicate its output.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s %(message)s")
logger = logging.getLogger("ecovision")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Which model artifacts this process will serve (MODEL_DIR, default
    # "models"). Logged at startup so a wrong folder is obvious immediately
    # instead of showing up as quietly different forecasts.
    logger.info("Serving forecast models from %s", pretrained_models.models_dir())

    # Loud, because a forced decision is not a model output. If this is on
    # by accident, every scan in the cycle is a bench artefact -- so it is
    # a warning, not an info line, and it names the way out.
    from routers.iot import trial_force_decision
    forced = trial_force_decision()
    if forced:
        logger.warning(
            "TRIAL MODE: TRIAL_FORCE_DECISION=%s -- /api/iot/ingest will return "
            "this decision instead of the model's, and every response and "
            "manifest entry is marked forced=true. Unset it before recording "
            "anything real.", forced,
        )

    # Load every model, scaler and training record once, here, instead of
    # re-reading them on each request. Startup pays a few seconds so that no
    # request does; a metal whose files are missing is skipped with a
    # warning and falls back to a live fit, as it always did.
    t0 = time.perf_counter()
    loaded = pretrained_models.warmup()
    logger.info("Preloaded model artifacts in %.1fs: %s",
                time.perf_counter() - t0,
                ", ".join(f"{m}={'+'.join(k) or 'none'}" for m, k in loaded.items()))

    # Keeps the Market Overview cache warm in the background -- computing
    # it fresh takes ~a minute (pretrained ARIMA+LSTM backtest across 6
    # metals), too slow to do inline on a dashboard request. See
    # services/market_service.py.
    refresh_task = asyncio.create_task(market_service.refresh_loop())
    yield
    refresh_task.cancel()


app = FastAPI(
    title="EcoVision — Smart Valuation & Material Routing",
    version="1.0.0",
    description="Smart Valuation & Material Routing - Predictive dashboard for e-waste recycling facilities",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Vite auto-shifts to 5174, 5175, etc. if 5173 is already taken by
    # something else on your machine, and the browser may use either
    # "localhost" or "127.0.0.1" depending on how you opened the page --
    # matching any port on either hostname (instead of hardcoding one
    # exact origin) means the dashboard keeps working regardless of which
    # port Vite actually lands on that session.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast.router, prefix="/api/forecast", tags=["Financial Forecast"])
app.include_router(disposition.router, prefix="/api/disposition", tags=["Strategic Disposition"])
app.include_router(iot.router, prefix="/api/iot", tags=["IoT Ingestion (pre-hardware contract)"])
app.include_router(manifest.router, prefix="/api/manifest", tags=["Tonnage Manifest"])
app.include_router(market.router, prefix="/api/market", tags=["Market Overview"])
app.include_router(fx.router, prefix="/api/fx", tags=["Exchange Rate"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "component": "Smart Valuation & Material Routing - EWaste Dashboard"}