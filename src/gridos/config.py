"""
GridOS configuration management.

This reduced launch version keeps the configuration surface intentionally small so
that the default developer path works without external infrastructure. Optional
persistent backends remain available, but they are not required for first use.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class StorageBackend(str, Enum):
    """Optional persistent storage backends."""

    INFLUXDB = "influxdb"
    TIMESCALEDB = "timescaledb"


class Settings(BaseSettings):
    """Central configuration for the reduced GridOS launch path.

    Values are read from environment variables prefixed with ``GRIDOS_`` and from
    a local ``.env`` file when present. The default mode is intentionally local
    and lightweight.
    """

    model_config = SettingsConfigDict(
        env_prefix="GRIDOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment.",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level.",
    )
    secret_key: str = Field(
        default="replace-this-before-production",
        description="Secret key for future signing or auth-related features.",
    )

    host: str = Field(
        default="0.0.0.0",
        description="API bind address.",
    )
    port: int = Field(
        default=8000,
        description="API bind port.",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins.",
    )

    use_inmemory_storage: bool = Field(
        default=True,
        description="Use lightweight in-memory telemetry storage for the default launch path.",
    )
    storage_backend: StorageBackend = Field(
        default=StorageBackend.INFLUXDB,
        description="Persistent storage backend used only when in-memory mode is disabled.",
    )

    influxdb_url: str = Field(
        default="http://localhost:8086",
        alias="INFLUXDB_URL",
        description="InfluxDB 2.x connection URL.",
    )
    influxdb_token: str = Field(
        default="replace-with-real-token",
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

    timescaledb_dsn: str = Field(
        default="postgresql://gridos:gridos@localhost:5432/gridos",
        alias="TIMESCALEDB_DSN",
        description="TimescaleDB connection string.",
    )


settings = Settings()
