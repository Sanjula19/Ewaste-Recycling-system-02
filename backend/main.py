import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import forecast, disposition, iot, manifest, market
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


@app.get("/api/health")
def health_check():
    return {"status": "ok", "component": "Smart Valuation & Material Routing - EWaste Dashboard"}