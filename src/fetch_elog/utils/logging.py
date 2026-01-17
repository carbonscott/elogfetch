"""Logging setup for fetch-elog."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOGGER_NAME = "fetch_elog"


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    quiet: bool = False,
) -> logging.Logger:
    """Configure logging for the application.

    Args:
        level: Logging level (default: INFO)
        log_file: Optional path to log file
        quiet: If True, suppress console output

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not quiet:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    """Get the fetch-elog logger instance."""
    return logging.getLogger(LOGGER_NAME)
