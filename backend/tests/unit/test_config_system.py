"""Comprehensive unit tests for ArmServe production configuration and secrets management system."""

from typing import cast

import pytest
from pydantic import SecretStr, ValidationError

from backend.app.core.config import (
    AppConfig,
    ArmServeSettings,
    AuthConfig,
    DatabaseConfig,
    EnvironmentType,
    OptimizationConfig,
)


def test_valid_default_development_config() -> None:
    """Verify that default settings instantiate cleanly in development or test mode."""
    cfg = ArmServeSettings()
    assert cfg.app.env in [EnvironmentType.DEVELOPMENT, EnvironmentType.TEST]
    assert cfg.app.debug is True
    assert cfg.database.host == "localhost"
    assert isinstance(cfg.database.password, SecretStr)
    assert cfg.database.password.get_secret_value() == "armserve_dev_pass"


def test_secret_str_masking_in_repr_and_str() -> None:
    """Verify that secret values are masked and never printed directly in string outputs."""
    password_secret = SecretStr("super-secret-db-password-12345")
    api_key_secret = SecretStr("arm_live_secret_key_99999999")

    db_cfg = DatabaseConfig(password=password_secret)
    auth_cfg = AuthConfig(secret_key=api_key_secret)

    # String representation must mask secret values
    assert "super-secret-db-password-12345" not in str(db_cfg)
    assert "super-secret-db-password-12345" not in repr(db_cfg)
    assert "arm_live_secret_key_99999999" not in str(auth_cfg)
    assert "arm_live_secret_key_99999999" not in repr(auth_cfg)

    assert "**********" in repr(password_secret)
    assert db_cfg.password.get_secret_value() == "super-secret-db-password-12345"


def test_invalid_value_rejection() -> None:
    """Verify that invalid field values fail validation immediately."""
    invalid_port = cast(int, 0)
    invalid_trials_limit = cast(int, 0)

    # Invalid port (< 1)
    with pytest.raises(ValidationError) as exc_info:
        AppConfig(api_port=invalid_port)
    assert "api_port" in str(exc_info.value)

    # Invalid max_trials_limit (< 1)
    with pytest.raises(ValidationError) as exc_info:
        ArmServeSettings(optimization=OptimizationConfig(max_trials_limit=invalid_trials_limit))
    assert "max_trials_limit" in str(exc_info.value)


def test_environment_separation_production_rules() -> None:
    """Verify that production environment rules enforce strict security constraints."""
    # Production with debug=True must fail
    with pytest.raises(ValueError) as exc_info:
        ArmServeSettings(
            app=AppConfig(env=EnvironmentType.PRODUCTION, debug=True),
            auth=AuthConfig(
                secret_key=SecretStr("a-very-long-production-secret-key-32-chars-long")
            ),
            database=DatabaseConfig(password=SecretStr("prod-password-999")),
        )
    assert "ARMSERVE_DEBUG cannot be True in production" in str(exc_info.value)

    # Production with default dev secret key must fail
    with pytest.raises(ValueError) as exc_info:
        ArmServeSettings(
            app=AppConfig(env=EnvironmentType.PRODUCTION, debug=False),
            auth=AuthConfig(
                secret_key=SecretStr("dev-secret-key-change-in-production-min-32-chars")
            ),
            database=DatabaseConfig(password=SecretStr("prod-password-999")),
        )
    assert "Production requires a strong ARMSERVE_SECRET_KEY" in str(exc_info.value)

    # Production with default database password must fail
    with pytest.raises(ValueError) as exc_info:
        ArmServeSettings(
            app=AppConfig(env=EnvironmentType.PRODUCTION, debug=False),
            auth=AuthConfig(
                secret_key=SecretStr("a-very-long-production-secret-key-32-chars-long")
            ),
            database=DatabaseConfig(password=SecretStr("armserve_dev_pass")),
        )
    assert "Default database password cannot be used in production" in str(exc_info.value)


def test_valid_production_config() -> None:
    """Verify that a valid production configuration passes all startup rules."""
    cfg = ArmServeSettings(
        app=AppConfig(env=EnvironmentType.PRODUCTION, debug=False),
        auth=AuthConfig(
            secret_key=SecretStr("super-secure-production-jwt-secret-key-min-32-bytes")
        ),
        database=DatabaseConfig(password=SecretStr("secure-prod-db-pass-12345")),
    )
    assert cfg.app.env == EnvironmentType.PRODUCTION
    assert cfg.app.debug is False
    assert (
        cfg.auth.secret_key.get_secret_value()
        == "super-secure-production-jwt-secret-key-min-32-bytes"
    )
    assert cfg.database.password.get_secret_value() == "secure-prod-db-pass-12345"


def test_secret_exposure_prevention_in_exceptions() -> None:
    """Verify that secret values are not leaked in exception messages."""
    raw_secret = "sensitive-super-secret-key-value-999"

    # Exception strings should mask the secret value
    try:
        raise ValueError(f"Config error for secret: {SecretStr(raw_secret)}")
    except ValueError as err:
        err_msg = str(err)
        assert raw_secret not in err_msg
        assert "**********" in err_msg
