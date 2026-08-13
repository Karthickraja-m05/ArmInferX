"""ArmServe Production-Oriented Configuration and Secrets Management System.

Enforces strongly-typed nested configuration, secret masking (SecretStr),
environment separation (development/test/production), and startup validation rules.
"""

import os
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    env: EnvironmentType = Field(default=EnvironmentType.DEVELOPMENT)
    debug: bool = Field(default=True)
    log_level: str = Field(default="INFO")
    api_host: str = Field(default="0.0.0.0")  # nosec B104
    api_port: int = Field(default=8000, ge=1, le=65535)
    storage_path: str = Field(default="./storage")


class DatabaseConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    user: str = Field(default="armserve")
    password: SecretStr = Field(default=SecretStr("armserve_dev_pass"))
    name: str = Field(default="armserve_dev")
    max_connections: int = Field(default=20, ge=1, le=100)
    pool_size: int = Field(default=10, ge=1, le=50)
    max_overflow: int = Field(default=10, ge=0, le=50)
    pool_timeout: int = Field(default=30, ge=1, le=120)
    pool_recycle: int = Field(default=1800, ge=60)
    pool_pre_ping: bool = Field(default=True)
    database_url: SecretStr | None = Field(default=None)

    @property
    def connection_url(self) -> str:
        if self.database_url:
            return self.database_url.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.user}:"
            f"{self.password.get_secret_value()}@{self.host}:{self.port}/{self.name}"
        )


class CloudProviderConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: SecretStr | None = Field(default=None)
    aws_secret_access_key: SecretStr | None = Field(default=None)
    aws_s3_bucket: str = Field(default="armserve-models")

    azure_subscription_id: SecretStr | None = Field(default=None)
    azure_tenant_id: SecretStr | None = Field(default=None)

    gcp_project_id: str | None = Field(default=None)
    gcp_credentials_json: SecretStr | None = Field(default=None)


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    default_storage_bucket: str = Field(default="armserve-models")
    max_model_size_bytes: int = Field(default=50 * 1024 * 1024 * 1024, ge=1)  # 50GB
    allowed_formats: list[str] = Field(
        default_factory=lambda: ["ONNX", "PYTORCH", "GGUF", "SAFETENSORS"]
    )


class InferenceConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    default_runtime: str = Field(default="onnxruntime")
    max_num_threads: int = Field(default=64, ge=1, le=256)
    max_batch_size: int = Field(default=128, ge=1, le=1024)
    memory_limit_mb_default: int = Field(default=4096, ge=128)


class OptimizationConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    default_strategy: str = Field(default="tpe")
    max_trials_limit: int = Field(default=100, ge=1, le=1000)
    default_timeout_seconds: int = Field(default=3600, ge=60)


class ObservabilityConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    otlp_endpoint: str | None = Field(default=None)
    prometheus_enabled: bool = Field(default=True)
    enable_tracing: bool = Field(default=False)


class AuthConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-key-change-in-production-min-32-chars")
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60, ge=1)
    api_key_header_name: str = Field(default="X-API-Key")


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="ignore", protected_namespaces=())

    model_path: str = Field(default="storage/models/qwen2.5-0.5b-instruct-q4_k_m.gguf")
    context_length: int = Field(default=2048, ge=128, le=32768)
    thread_count: int = Field(default=4, ge=1, le=128)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=256, ge=1, le=4096)
    batch_size: int = Field(default=128, ge=1, le=2048)
    server_port: int = Field(default=8000, ge=1024, le=65535)
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)


class ArmServeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ARMSERVE_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Top-level settings maps
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cloud: CloudProviderConfig = Field(default_factory=CloudProviderConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)

    # Flat environment mapping helpers for direct env vars
    ENV: EnvironmentType | None = None
    DEBUG: bool | None = None
    LOG_LEVEL: str | None = None
    API_HOST: str | None = None
    API_PORT: int | None = None
    SECRET_KEY: SecretStr | None = None
    DATABASE_URL: SecretStr | None = None
    DB_PASSWORD: SecretStr | None = None

    @model_validator(mode="after")
    def sync_flat_env_vars_and_validate(self) -> "ArmServeSettings":
        # Synchronize flat env overrides into nested categories if supplied
        if self.ENV is not None:
            self.app.env = self.ENV
        if self.DEBUG is not None:
            self.app.debug = self.DEBUG
        if self.LOG_LEVEL is not None:
            self.app.log_level = self.LOG_LEVEL
        if self.API_HOST is not None:
            self.app.api_host = self.API_HOST
        if self.API_PORT is not None:
            self.app.api_port = self.API_PORT
        if self.SECRET_KEY is not None:
            self.auth.secret_key = self.SECRET_KEY
        if self.DATABASE_URL is not None:
            self.database.database_url = self.DATABASE_URL
        elif os.getenv("DATABASE_URL"):
            self.database.database_url = SecretStr(os.getenv("DATABASE_URL") or "")
        if self.DB_PASSWORD is not None:
            self.database.password = self.DB_PASSWORD

        # Production Validation Rules
        if self.app.env == EnvironmentType.PRODUCTION:
            if self.app.debug:
                raise ValueError("ARMSERVE_DEBUG cannot be True in production environment")

            secret_val = self.auth.secret_key.get_secret_value()
            if "dev-secret-key" in secret_val or len(secret_val) < 32:
                raise ValueError(
                    "Production requires a strong ARMSERVE_SECRET_KEY (minimum 32 characters, non-default)"
                )

            if self.database.password.get_secret_value() == "armserve_dev_pass":
                raise ValueError("Default database password cannot be used in production")

        return self


# Global singleton configuration instance
settings = ArmServeSettings()
