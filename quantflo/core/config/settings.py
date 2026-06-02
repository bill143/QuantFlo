"""Typed application settings for QUANTFLO.

Phase 0 declares the configuration *surface* only. Values are read from the
environment (or a local ``.env``). No secrets are committed; see ``.env.example``
for the full list of variables later phases will require. Real secret material is
sourced from a vault in Phase 1 — never hard-coded here.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings. All fields optional in Phase 0 (surface only)."""

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

    # ── Datastore (Phase 1+) — declared surface only, no live endpoints ──
    database_url: str | None = Field(default=None, description="primary Postgres DSN")
    redis_url: str | None = Field(default=None, description="Redis / state-bus URL")

    # ── Secrets / KMS (Phase 1+) ──
    kms_key_id: str | None = Field(default=None, description="vault/KMS key identifier")
    vault_addr: str | None = Field(default=None, description="secrets manager address")

    # ── Broker (later phase) — no live credentials in Phase 0 ──
    broker_name: str | None = Field(
        default=None, description="execution broker id (e.g. tradovate)"
    )
    broker_account_id: str | None = Field(default=None, description="broker account identifier")
    broker_api_base_url: str | None = Field(default=None, description="broker API base URL")

    # ── Market data (later phase) ──
    market_data_provider: str | None = Field(default=None, description="market-data vendor id")
    market_data_api_base_url: str | None = Field(
        default=None, description="market-data API base URL"
    )

    # ── Orchestration ──
    ruflo_enabled: bool = Field(default=False, description="bridge to the ruflo runtime (Phase 1)")


def get_settings() -> Settings:
    """Construct settings from the current environment."""
    return Settings()
