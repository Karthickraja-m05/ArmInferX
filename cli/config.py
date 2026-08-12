"""ArmServe CLI Configuration Management System."""

import json
import os
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CLIConfig(BaseSettings):
    """Configuration settings for ArmServe CLI client."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="ARMSERVE_",
    )

    api_url: str = Field(
        default="http://localhost:8000/api/v1",
        description="ArmServe Backend API Base URL",
    )
    api_key: str | None = Field(
        default=None,
        description="Optional API key or Auth Token for backend communication",
    )
    timeout: float = Field(
        default=10.0,
        ge=0.5,
        le=120.0,
        description="HTTP request timeout in seconds",
    )
    json_output: bool = Field(
        default=False,
        description="Output responses in raw JSON format",
    )

    @classmethod
    def load(
        cls,
        config_path: str | Path | None = None,
        api_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        json_output: bool | None = None,
    ) -> "CLIConfig":
        """Load CLI configuration with precedence: CLI arguments > Config file > Env vars > Defaults."""
        file_data: dict[str, Any] = {}

        if config_path:
            path = Path(config_path)
            if path.exists() and path.is_file():
                if path.suffix == ".json":
                    with path.open("r", encoding="utf-8") as f:
                        file_data = json.load(f)
                elif path.name.endswith(".env") or path.suffix == ".env":
                    from dotenv import dotenv_values

                    file_data = {
                        k.lower().removeprefix("armserve_"): v
                        for k, v in dotenv_values(path).items()
                        if v is not None
                    }

        # Priority resolution
        resolved_api_url = (
            api_url
            or file_data.get("api_url")
            or os.getenv("ARMSERVE_API_URL")
            or "http://localhost:8000/api/v1"
        )
        resolved_api_key = (
            api_key
            if api_key is not None
            else file_data.get("api_key") or os.getenv("ARMSERVE_API_KEY")
        )
        resolved_timeout = (
            timeout
            if timeout is not None
            else float(file_data.get("timeout", os.getenv("ARMSERVE_TIMEOUT", "10.0")))
        )
        resolved_json = (
            json_output if json_output is not None else bool(file_data.get("json_output", False))
        )

        return CLIConfig(
            api_url=resolved_api_url,
            api_key=resolved_api_key,
            timeout=resolved_timeout,
            json_output=resolved_json,
        )
