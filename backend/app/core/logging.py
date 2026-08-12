"""Structured logging configuration using structlog."""

import logging
import sys
from typing import cast

import structlog
from structlog.typing import Processor

from backend.app.core.config import settings


def configure_logging() -> None:
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
        else structlog.dev.ConsoleRenderer(),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
