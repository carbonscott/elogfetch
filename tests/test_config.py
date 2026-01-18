"""Tests for configuration loading."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

from elogfetch.config import Config


class TestDefaultConfig:
    """Tests for default configuration values."""

    def test_default_config(self):
        """Verify default configuration values are sensible."""
        config = Config()

        assert config.hours_lookback == 168.0  # 7 days
        assert config.parallel_jobs == 10
        assert config.queue_size == 100
        assert config.batch_commit_size == 50
        assert config.database_dir is None
        assert config.lock_timeout == 60
        assert config.base_url == "https://pswww.slac.stanford.edu"
        assert config.exclude_patterns == []


class TestConfigFromCLI:
    """Tests for CLI argument configuration."""

    def test_cli_args_override(self):
        """Verify CLI args take precedence over defaults."""
        cli_args = {
            "hours": 24,
            "exclude": ["test*", "debug*"],
            "parallel_jobs": 5,
            "queue_size": 50,
            "batch_commit_size": 25,
            "database_dir": "/tmp/test_db",
        }

        config = Config.load(cli_args=cli_args)

        assert config.hours_lookback == 24.0
        assert config.exclude_patterns == ["test*", "debug*"]
        assert config.parallel_jobs == 5
        assert config.queue_size == 50
        assert config.batch_commit_size == 25
        assert config.database_dir == Path("/tmp/test_db")

    def test_cli_args_partial_override(self):
        """Verify partial CLI args only override specified values."""
        cli_args = {"hours": 12}

        config = Config.load(cli_args=cli_args)

        assert config.hours_lookback == 12.0
        # Other values should be defaults
        assert config.parallel_jobs == 10
        assert config.queue_size == 100


class TestConfigFromEnv:
    """Tests for environment variable configuration."""

    def test_env_var_override(self):
        """Verify environment variables override defaults."""
        env_vars = {
            "FETCH_ELOG_HOURS_LOOKBACK": "48",
            "FETCH_ELOG_PARALLEL_JOBS": "8",
            "FETCH_ELOG_DATABASE_DIR": "/tmp/env_db",
            "FETCH_ELOG_LOCK_TIMEOUT": "120",
            "FETCH_ELOG_BASE_URL": "https://test.slac.stanford.edu",
        }

        with mock.patch.dict(os.environ, env_vars, clear=False):
            config = Config.load()

        assert config.hours_lookback == 48.0
        assert config.parallel_jobs == 8
        assert config.database_dir == Path("/tmp/env_db")
        assert config.lock_timeout == 120
        assert config.base_url == "https://test.slac.stanford.edu"

    def test_cli_takes_precedence_over_env(self):
        """Verify CLI args take precedence over environment variables."""
        env_vars = {
            "FETCH_ELOG_HOURS_LOOKBACK": "48",
            "FETCH_ELOG_PARALLEL_JOBS": "8",
        }
        cli_args = {
            "hours": 24,
        }

        with mock.patch.dict(os.environ, env_vars, clear=False):
            config = Config.load(cli_args=cli_args)

        # CLI should win for hours
        assert config.hours_lookback == 24.0
        # Env should apply for parallel_jobs (not in CLI)
        assert config.parallel_jobs == 8


class TestConfigFromFile:
    """Tests for YAML file configuration."""

    def test_yaml_config_load(self, tmp_path):
        """Verify configuration loads from YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
hours_lookback: 72
exclude_patterns:
  - "test*"
  - "txi*"
parallel_jobs: 15
database_dir: ~/elog_data
"""
        )

        config = Config.load(config_file=config_file)

        assert config.hours_lookback == 72.0
        assert config.exclude_patterns == ["test*", "txi*"]
        assert config.parallel_jobs == 15
        assert config.database_dir == Path("~/elog_data").expanduser()

    def test_yaml_cli_precedence(self, tmp_path):
        """Verify CLI args take precedence over YAML file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
hours_lookback: 72
parallel_jobs: 15
"""
        )
        cli_args = {"hours": 24}

        config = Config.load(config_file=config_file, cli_args=cli_args)

        # CLI wins for hours
        assert config.hours_lookback == 24.0
        # YAML applies for parallel_jobs
        assert config.parallel_jobs == 15

    def test_full_precedence_chain(self, tmp_path):
        """Verify full precedence: CLI > env > file > defaults."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
hours_lookback: 72
parallel_jobs: 15
queue_size: 200
"""
        )
        env_vars = {
            "FETCH_ELOG_HOURS_LOOKBACK": "48",
            "FETCH_ELOG_PARALLEL_JOBS": "8",
        }
        cli_args = {"hours": 24}

        with mock.patch.dict(os.environ, env_vars, clear=False):
            config = Config.load(config_file=config_file, cli_args=cli_args)

        # CLI wins for hours (24)
        assert config.hours_lookback == 24.0
        # Env wins for parallel_jobs (8)
        assert config.parallel_jobs == 8
        # YAML applies for queue_size (200)
        assert config.queue_size == 200
        # Default for batch_commit_size (50)
        assert config.batch_commit_size == 50

    def test_missing_config_file(self, tmp_path):
        """Verify missing config file is handled gracefully."""
        config_file = tmp_path / "nonexistent.yaml"

        config = Config.load(config_file=config_file)

        # Should use defaults
        assert config.hours_lookback == 168.0
        assert config.parallel_jobs == 10

    def test_empty_config_file(self, tmp_path):
        """Verify empty config file is handled gracefully."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = Config.load(config_file=config_file)

        # Should use defaults
        assert config.hours_lookback == 168.0
        assert config.parallel_jobs == 10
