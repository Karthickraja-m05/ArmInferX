"""Unit tests for Settings configuration."""

from backend.app.core.config import settings


def test_settings_defaults() -> None:
    assert settings.app.env == "development"
    assert settings.app.api_port == 8000
    assert "postgresql" in settings.database.connection_url
