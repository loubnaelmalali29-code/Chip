"""Structured logging configuration for Chip."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("chip.server")


def configure_logging() -> None:
    """Configure logging with structured format and configurable log level."""
    if logger.handlers:
        return

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Suppress noisy HTTP client logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

















