"""Database storage for fetch-elog."""

from __future__ import annotations

from .database import Database, find_latest_database, generate_db_name

__all__ = ["Database", "find_latest_database", "generate_db_name"]
