"""Tests for the typed settings surface (no secrets, defaults only)."""
from __future__ import annotations

from quantflo.core.config import Settings, get_settings


def test_settings_construct_with_safe_defaults() -> None:
    settings = get_settings()
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.ruflo_enabled is False


def test_secret_and_endpoint_fields_default_to_none() -> None:
    settings = get_settings()
    assert settings.database_url is None
    assert settings.redis_url is None
    assert settings.kms_key_id is None
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
