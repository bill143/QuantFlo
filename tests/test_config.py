"""Tests for the typed settings surface (no secrets, defaults only)."""
from __future__ import annotations

import os

import pytest

from quantflo.core.config import Settings, get_settings


def test_settings_construct_with_safe_defaults() -> None:
    settings = get_settings()
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.ruflo_enabled is False


def test_secret_and_endpoint_fields_default_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # Field DEFAULTS must not hard-code any secret/endpoint. Isolate from BOTH the .env
    # file AND any QUANTFLO_* environment variables (CI injects DATABASE_URL/REDIS_URL).
    for key in list(os.environ):
        if key.startswith("QUANTFLO_"):
            monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=None)
    assert settings.database_url is None
    assert settings.redis_url is None
    assert settings.kms_key_id is None
    assert settings.kms_key_arn is None
    assert settings.databento_api_key is None
    assert settings.sentry_dsn is None
    assert settings.vault_addr is None
    assert settings.broker_name is None
    assert settings.market_data_provider is None


def test_settings_are_frozen() -> None:
    settings = Settings()
    try:
        settings.environment = "production"  # type: ignore[misc]
    except (ValueError, TypeError, AttributeError):
        pass
    else:  # pragma: no cover
        raise AssertionError("Settings should be immutable (frozen)")
