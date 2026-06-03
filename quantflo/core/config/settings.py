"""Typed application settings for QUANTFLO.

Values are read from the environment (or a local ``.env``) with the ``QUANTFLO_``
prefix. No secrets are committed; see ``.env.example`` for the full surface. Real
secret material (broker creds) is sourced from the KMS-backed vault, never here;
provider/observability tokens come from ``.env`` (gitignored).
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings (single-tenant; schema multi-tenant-ready)."""

    model_config = SettingsConfigDict(
        env_prefix="QUANTFLO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # ── Runtime ──
    environment: str = Field(default="development", description="deployment environment")
    log_level: str = Field(default="INFO", description="root log level")
    tenant_id: str = Field(default="local", description="single local owner; schema is multi-tenant-ready")

    # ── Datastore ──
    database_url: str | None = Field(default=None, description="primary Postgres DSN (asyncpg)")
    redis_url: str | None = Field(default=None, description="Redis / state-bus URL")
    db_pool_size: int = Field(default=10, ge=1, description="asyncpg pool base size")
    db_max_overflow: int = Field(default=20, ge=0, description="asyncpg pool overflow")
    db_pool_timeout: int = Field(default=30, ge=1, description="pool checkout timeout (s)")
    redis_max_connections: int = Field(default=50, ge=1, description="Redis pool max connections")

    # ── Market data provider ──
    market_data_provider: str | None = Field(default=None, description="market-data vendor id")
    market_data_api_base_url: str | None = Field(default=None, description="market-data API base URL")
    databento_api_key: str | None = Field(default=None, description="Databento API key (db-...)")

    # ── Secrets / KMS vault ──
    kms_provider: str = Field(default="local", description="'local' (dev emulator) or 'aws'")
    aws_region: str = Field(default="us-east-1", description="AWS region for KMS")
    kms_key_arn: str | None = Field(default=None, description="AWS KMS key ARN (when kms_provider=aws)")
    kms_key_id: str | None = Field(default=None, description="legacy/alt KMS key identifier")
    vault_addr: str | None = Field(default=None, description="external secrets-manager address (unused)")
    local_kms_master_key: str | None = Field(
        default=None, description="base64 master key for the LOCAL KMS emulator (dev only)"
    )

    # ── Observability ──
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN (not committed)")

    # ── Broker / execution (later phase) ──
    broker_name: str | None = Field(default=None, description="execution broker id (e.g. tradovate)")
    broker_account_id: str | None = Field(default=None, description="broker account identifier")
    broker_api_base_url: str | None = Field(default=None, description="broker API base URL")

    # ── Orchestration ──
    ruflo_enabled: bool = Field(default=False, description="bridge to the ruflo runtime")


def get_settings() -> Settings:
    """Construct settings from the current environment."""
    return Settings()
