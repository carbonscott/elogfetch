"""Configuration management for elogfetch."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
import re

import yaml


DB_PREFIX = "elog_"
DB_PATTERN = re.compile(r"^elog_(\d{4})_(\d{4})_(\d{4})\.db$")


@dataclass
class Config:
    """Configuration for elogfetch."""

    # Fetch settings
    hours_lookback: float = 168.0  # 7 days default
    exclude_patterns: list[str] = field(default_factory=list)

    # Execution settings
    parallel_jobs: int = 10

    # Paths
    database_dir: Path | None = None
    lock_timeout: int = 60  # seconds

    # API settings
    base_url: str = "https://pswww.slac.stanford.edu"
    kerberos_principal: str = "HTTP@pswww.slac.stanford.edu"

    @classmethod
    def load(
        cls,
        config_file: Path | None = None,
        cli_args: dict[str, Any] | None = None,
    ) -> "Config":
        """Load config with precedence: CLI > env > file > defaults."""
        config = cls()

        # 1. Load from file
        if config_file and config_file.exists():
            config = cls._merge_yaml(config, config_file)

        # 2. Apply environment variables
        config = cls._merge_env(config)

        # 3. Apply CLI arguments (highest precedence)
        if cli_args:
            config = cls._merge_cli(config, cli_args)

        return config

    @classmethod
    def _merge_yaml(cls, config: "Config", config_file: Path) -> "Config":
        """Merge configuration from YAML file."""
        with open(config_file) as f:
            data = yaml.safe_load(f)

        if not data:
            return config

        if "hours_lookback" in data:
            config.hours_lookback = float(data["hours_lookback"])
        if "exclude_patterns" in data:
            config.exclude_patterns = data["exclude_patterns"]
        if "parallel_jobs" in data:
            config.parallel_jobs = int(data["parallel_jobs"])
        if "database_dir" in data:
            config.database_dir = Path(data["database_dir"]).expanduser()
        if "lock_timeout" in data:
            config.lock_timeout = int(data["lock_timeout"])

        return config

    @classmethod
    def _merge_env(cls, config: "Config") -> "Config":
        """Merge configuration from environment variables."""
        if val := os.environ.get("FETCH_ELOG_HOURS_LOOKBACK"):
            config.hours_lookback = float(val)
        if val := os.environ.get("FETCH_ELOG_PARALLEL_JOBS"):
            config.parallel_jobs = int(val)
        if val := os.environ.get("FETCH_ELOG_DATABASE_DIR"):
            config.database_dir = Path(val).expanduser()
        if val := os.environ.get("FETCH_ELOG_LOCK_TIMEOUT"):
            config.lock_timeout = int(val)
        if val := os.environ.get("FETCH_ELOG_BASE_URL"):
            config.base_url = val
        if val := os.environ.get("FETCH_ELOG_KERBEROS_PRINCIPAL"):
            config.kerberos_principal = val

        return config

    @classmethod
    def _merge_cli(cls, config: "Config", cli_args: dict[str, Any]) -> "Config":
        """Merge configuration from CLI arguments."""
        if cli_args.get("hours") is not None:
            config.hours_lookback = float(cli_args["hours"])
        if cli_args.get("exclude"):
            config.exclude_patterns = cli_args["exclude"]
        if cli_args.get("parallel_jobs") is not None:
            config.parallel_jobs = int(cli_args["parallel_jobs"])
        if cli_args.get("database_dir"):
            config.database_dir = Path(cli_args["database_dir"]).expanduser()

        return config
