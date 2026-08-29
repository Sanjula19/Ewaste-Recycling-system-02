from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "E-Waste Gas Detection System"
    app_version: str = "2.0.0"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./ewaste_gas.db"
    model_dir: str = "ml_models"

    # ── MQTT ──────────────────────────────────────────────────────────
    mqtt_broker: str = "8c22931e95374473bea07f2ce5b65093.s1.eu.hivemq.cloud"
    mqtt_port: int = 8883
    mqtt_topic: str = "ewaste/esp32/sensors"
    mqtt_user: str = "hivemq.webclient.1786954284059"
    mqtt_password: str = "3yFM1cjfifMAV4UzzbReWpykGepk9cCO"

    raw_adc_alert_thresholds_json: str = ""
    cors_origins: List[str] = []
    jwt_secret_key: str = "ewaste-gas-detection-super-secret-key-2024"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    default_api_key: str = "esp32-device-key-001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        protected_namespaces=()
    )

settings = Settings()