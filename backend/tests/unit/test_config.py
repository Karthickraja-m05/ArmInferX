"""Unit tests for Settings configuration."""

from backend.app.core.config import EnvironmentType, settings


def test_settings_defaults() -> None:
    assert settings.app.env in (
        EnvironmentType.DEVELOPMENT,
        EnvironmentType.TEST,
        EnvironmentType.STAGING,
        EnvironmentType.PRODUCTION,
    )
    assert settings.app.api_port == 8000
    assert (
        "sqlite" in settings.database.connection_url
        or "postgresql" in settings.database.connection_url
    )
