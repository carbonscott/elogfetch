"""Utility functions for elogfetch."""

from __future__ import annotations

from .locking import acquire_lock
from .logging import get_logger, setup_logging

__all__ = ["get_logger", "setup_logging", "acquire_lock"]
