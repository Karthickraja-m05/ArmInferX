"""Unit tests for Settings configuration."""

from backend.app.core.config import settings


def test_settings_defaults() -> None:
    assert str(settings.app.env.value) == "development"
    assert settings.app.api_port == 8000
    assert (
        "sqlite" in settings.database.connection_url
        or "postgresql" in settings.database.connection_url
    )
