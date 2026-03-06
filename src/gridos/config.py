"""
GridOS configuration management.

Uses Pydantic ``BaseSettings`` to load configuration from environment variables
and ``.env`` files.  Every setting has a sensible default so that the platform
can start in development mode without any external configuration.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageBackend(str, Enum):
    """Supported time-series storage backends."""

    INFLUXDB = "influxdb"
    TIMESCALEDB = "timescaledb"


class Settings(BaseSettings):
    """Central configuration for the GridOS platform.

    Values are read from environment variables prefixed with ``GRIDOS_`` or
    from a ``.env`` file located in the project root.
    """

    model_config = SettingsConfigDict(
        env_prefix="GRIDOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── General ──────────────────────────────────────────
    env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment.",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )
    secret_key: str = Field(
        default="change-me-to-a-random-string",
        description="Secret key used for signing tokens and sessions.",
    )

    # ── FastAPI ──────────────────────────────────────────
    host: str = Field(default="0.0.0.0", description="API bind address.")  # noqa: S104  # nosec B104
    port: int = Field(default=8000, description="API bind port.")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins.",
    )

    # ── InfluxDB ─────────────────────────────────────────
    influxdb_url: str = Field(
        default="http://localhost:8086",
        alias="INFLUXDB_URL",
        description="InfluxDB 2.x connection URL.",
    )
    influxdb_token: str = Field(
        default="my-super-secret-token",
        alias="INFLUXDB_TOKEN",
        description="InfluxDB authentication token.",
    )
    influxdb_org: str = Field(
        default="gridos",
        alias="INFLUXDB_ORG",
        description="InfluxDB organization.",
    )
    influxdb_bucket: str = Field(
        default="telemetry",
        alias="INFLUXDB_BUCKET",
        description="InfluxDB bucket for telemetry data.",
    )

    # ── TimescaleDB ──────────────────────────────────────
    timescaledb_dsn: str = Field(
        default="postgresql://gridos:gridos@localhost:5432/gridos",
        alias="TIMESCALEDB_DSN",
        description="TimescaleDB connection string.",
    )

    # ── MQTT ─────────────────────────────────────────────
    mqtt_broker_host: str = Field(
        default="localhost",
        alias="MQTT_BROKER_HOST",
        description="MQTT broker hostname.",
    )
    mqtt_broker_port: int = Field(
        default=1883,
        alias="MQTT_BROKER_PORT",
        description="MQTT broker port.",
    )
    mqtt_username: str = Field(
        default="",
        alias="MQTT_USERNAME",
        description="MQTT username (leave empty for anonymous).",
    )
    mqtt_password: str = Field(
        default="",
        alias="MQTT_PASSWORD",
        description="MQTT password.",
    )
    mqtt_topic_prefix: str = Field(
        default="gridos/",
        alias="MQTT_TOPIC_PREFIX",
        description="MQTT topic prefix for all GridOS messages.",
    )

    # ── Modbus ───────────────────────────────────────────
    modbus_default_host: str = Field(
        default="localhost",
        alias="MODBUS_DEFAULT_HOST",
        description="Default Modbus TCP host.",
    )
    modbus_default_port: int = Field(
        default=502,
        alias="MODBUS_DEFAULT_PORT",
        description="Default Modbus TCP port.",
    )

    # ── Storage Backend Selection ────────────────────────
    storage_backend: StorageBackend = Field(
        default=StorageBackend.INFLUXDB,
        description="Active time-series storage backend.",
    )

    # ── ML / Forecasting ────────────────────────────────
    ml_model_dir: Path = Field(
        default=Path("./models_cache"),
        alias="ML_MODEL_DIR",
        description="Directory for persisting trained ML models.",
    )
    ml_forecast_horizon_hours: int = Field(
        default=24,
        alias="ML_FORECAST_HORIZON_HOURS",
        description="Default forecast horizon in hours.",
    )

    # ── Optimization ─────────────────────────────────────
    opt_time_horizon_hours: int = Field(
        default=24,
        alias="OPT_TIME_HORIZON_HOURS",
        description="Optimization scheduling horizon in hours.",
    )
    opt_time_step_minutes: int = Field(
        default=15,
        alias="OPT_TIME_STEP_MINUTES",
        description="Optimization time-step granularity in minutes.",
    )


# Singleton instance — import ``settings`` wherever needed.
settings = Settings()
