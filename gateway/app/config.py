# gateway/app/config.py
# ---------------------
# Loads all gateway settings from environment variables / .env file.

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the gateway root directory (one level above app/)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")


class Settings:
    # Listening port for the gateway itself
    gateway_port: int = int(os.getenv("GATEWAY_PORT", "8080"))

    # Upstream component URLs
    component1_url: str = os.getenv("COMPONENT1_URL", "http://127.0.0.1:8001")
    component2_url: str = os.getenv("COMPONENT2_URL", "http://127.0.0.1:8002")
    component3_url: str = os.getenv("COMPONENT3_URL", "http://127.0.0.1:8003")
    component4_url: str = os.getenv("COMPONENT4_URL", "http://127.0.0.1:8004")

    # Timeouts (seconds)
    proxy_timeout: float = float(os.getenv("PROXY_TIMEOUT", "30"))
    health_timeout: float = float(os.getenv("HEALTH_TIMEOUT", "5"))

    # CORS — "*" permits all origins; restrict in production
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")

    # Health-check paths used when pinging each component
    # These match each component's documented health endpoint.
    health_paths = {
        "component1": "/health",          # GET http://localhost:8001/health
        "component2": "/api/v1/health",   # GET http://localhost:8002/api/v1/health
<<<<<<< Updated upstream
        "component3": "/api/health",      # GET http://localhost:8003/api/health (real Smart Process Optimization backend, Step 5A/5B)
=======
        "component3": "/health",   # GET http://localhost:8003/api/v1/health
>>>>>>> Stashed changes
        "component4": "/api/health",      # GET http://localhost:8004/api/health
    }


settings = Settings()
