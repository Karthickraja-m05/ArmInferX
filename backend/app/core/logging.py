"""Structured logging configuration using structlog with automatic credential masking."""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any, cast

import structlog
from structlog.typing import Processor

from backend.app.core.config import settings

SENSITIVE_KEYWORDS = {
    "password",
    "pass",
    "secret",
    "secret_key",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "auth",
    "authorization",
    "x-api-key",
    "access_key",
    "aws_secret_access_key",
    "credentials",
    "bearer",
}


def mask_sensitive_data(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Structlog processor that redacts passwords, tokens, API keys, and credentials."""
    for key, val in list(event_dict.items()):
        key_lower = key.lower()
        if any(keyword in key_lower for keyword in SENSITIVE_KEYWORDS):
            event_dict[key] = "********"
        elif isinstance(val, MutableMapping):
            event_dict[key] = mask_sensitive_data(logger, method_name, val)
    return event_dict


def configure_logging() -> None:
    """Configure global structlog and standard logging settings."""
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    log_level = getattr(logging, settings.app.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    renderer = cast(
        Processor,
        structlog.processors.JSONRenderer()
        if not settings.app.debug
        else structlog.dev.ConsoleRenderer(colors=False),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            mask_sensitive_data,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
