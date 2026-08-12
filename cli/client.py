"""ArmServe CLI API Client for backend communication."""

from typing import Any

import httpx

from cli.config import CLIConfig


class CLIError(Exception):
    """Custom exception raised when CLI operations fail."""

    def __init__(self, message: str, status_code: int | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class ArmServeClient:
    """HTTP Client for communicating with the real ArmServe backend API."""

    def __init__(self, config: CLIConfig) -> None:
        self.config = config
        self.base_url = config.api_url.rstrip("/")

        headers = {
            "Accept": "application/json",
            "User-Agent": "ArmServe-CLI/0.1.0",
        }
        if config.api_key:
            headers["X-API-Key"] = config.api_key
            headers["Authorization"] = f"Bearer {config.api_key}"

        self.client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=config.timeout,
            follow_redirects=True,
        )

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Process API response and handle HTTP errors cleanly."""
        try:
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as err:
            try:
                error_json = err.response.json()
                detail = error_json.get("message") or error_json.get("detail") or str(err)
            except Exception:
                detail = err.response.text or str(err)
            raise CLIError(
                message=f"API request failed with status {err.response.status_code}: {detail}",
                status_code=err.response.status_code,
                details=detail,
            ) from err
        except httpx.RequestError as err:
            raise CLIError(
                message=f"Failed to connect to ArmServe backend at '{self.base_url}': {err}"
            ) from err

    def get_health(self) -> dict[str, Any]:
        """Fetch system health status from `/system/health`."""
        try:
            response = self.client.get("/system/health")
            return self._handle_response(response)
        except CLIError:
            raise
        except Exception as err:
            raise CLIError(f"Unexpected error checking health: {err}") from err

    def get_system_info(self) -> dict[str, Any]:
        """Fetch system metadata and diagnostics from `/system/info`."""
        try:
            response = self.client.get("/system/info")
            return self._handle_response(response)
        except CLIError:
            raise
        except Exception as err:
            raise CLIError(f"Unexpected error fetching system info: {err}") from err

    def validate_config(self, env_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate configuration settings using backend `/system/config/validate` API."""
        try:
            payload = {"env_overrides": env_overrides} if env_overrides else {}
            response = self.client.post("/system/config/validate", json=payload)
            return self._handle_response(response)
        except CLIError:
            raise
        except Exception as err:
            raise CLIError(f"Unexpected error validating configuration: {err}") from err

    def close(self) -> None:
        """Close the underlying HTTP client session cleanly."""
        try:
            self.client.close()
        except AttributeError:
            pass
