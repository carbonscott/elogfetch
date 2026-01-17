# elogfetch: Design Document

## Overview

`elogfetch` is a Python package for fetching LCLS experiment data from the electronic logbook (elog) system and storing it in a local SQLite database. It is designed to be run by individual users, with each user maintaining their own database containing only the experiments they are authorized to access.

## Goals

1. **Simplicity**: Single command to fetch and update experiment data
2. **Safety**: Handle concurrent runs, cleanup temp files, preserve backups
3. **Security**: Leverage existing Kerberos authentication for access control
4. **Reliability**: Proper error handling, retries, and logging
5. **Multi-user ready**: No shared state that could cause conflicts

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              elogfetch                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │    CLI       │───▶│   Fetcher    │───▶│   SLAC eLog API          │   │
│  │  (click)     │    │   (core)     │    │   (Kerberos auth)        │   │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘   │
│         │                   │                                            │
│         │                   ▼                                            │
│         │            ┌──────────────┐                                   │
│         │            │   Storage    │                                   │
│         │            │   (SQLite)   │                                   │
│         │            └──────────────┘                                   │
│         │                   │                                            │
│         ▼                   ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Config / Logging                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
elogfetch/
├── docs/
│   └── DESIGNS.md              # This document
├── src/
│   └── elogfetch/
│       ├── __init__.py
│       ├── cli.py              # Command-line interface (click)
│       ├── config.py           # Configuration loading (YAML + env + CLI)
│       ├── fetcher.py          # Core data fetching logic
│       ├── api/
│       │   ├── __init__.py
│       │   ├── client.py       # HTTP client with Kerberos auth
│       │   ├── experiments.py  # Experiment list API
│       │   ├── logbook.py      # Logbook entries API
│       │   ├── runtable.py     # Run table API
│       │   ├── filemanager.py  # File manager API
│       │   ├── questionnaire.py# Questionnaire API
│       │   └── workflow.py     # Workflow API
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py     # SQLite database operations
│       │   └── models.py       # Data models (dataclasses)
│       └── utils/
│           ├── __init__.py
│           ├── logging.py      # Logging setup
│           └── locking.py      # File locking utilities
├── tests/
│   ├── __init__.py
│   ├── test_fetcher.py
│   ├── test_api.py
│   └── test_storage.py
├── pyproject.toml
└── README.md
```

---

## Key Design Decisions

### 1. Use `requests` with `requests-kerberos` instead of `curl`

**Problem**: The current implementation shells out to `curl`, which:
- Requires correct system configuration for Kerberos
- Makes error handling difficult
- Adds subprocess overhead

**Solution**:
```python
from requests_kerberos import HTTPKerberosAuth

session = requests.Session()
session.auth = HTTPKerberosAuth(mutual_authentication=REQUIRED)
response = session.get(url)
```

**Benefits**:
- Explicit Kerberos authentication
- Better error messages
- Connection pooling
- Retry support via `urllib3`

---

### 2. Temporary Directories with Automatic Cleanup

**Problem**: Current implementation uses hardcoded paths like `experiments.csv` and `elog_data/` in the working directory, causing race conditions if multiple users run in the same directory.

**Solution**:
```python
import tempfile
from pathlib import Path

class FetchSession:
    def __init__(self, work_dir: Path = None):
        if work_dir is None:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="elogfetch_")
            self.work_dir = Path(self._temp_dir.name)
        else:
            self._temp_dir = None
            self.work_dir = work_dir

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self._temp_dir:
            self._temp_dir.cleanup()
```

**Benefits**:
- No conflicts between concurrent runs
- Automatic cleanup even on errors
- Option to specify custom directory for debugging

---

### 3. File Locking for Concurrent Safety

**Problem**: If cron runs the script while a previous run is still executing, they could corrupt the database.

**Solution**:
```python
import fcntl
from contextlib import contextmanager

@contextmanager
def acquire_lock(lock_path: Path, blocking: bool = False):
    """Acquire an exclusive lock on a file."""
    lock_file = open(lock_path, 'w')
    try:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        fcntl.flock(lock_file, flags)
        yield lock_file
    except BlockingIOError:
        raise RuntimeError(f"Another instance is already running (lock: {lock_path})")
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
```

**Usage**:
```python
lock_path = db_path.with_suffix('.lock')
with acquire_lock(lock_path):
    # Safe to update database
    ...
```

---

### 4. Structured Database Naming

**Problem**: Current pattern matching (`*.db` with `_`) is too loose and could match unrelated files.

**Solution**:
```python
DB_PREFIX = "elog_"
DB_PATTERN = re.compile(r"^elog_(\d{4})_(\d{4})_(\d{4})\.db$")

def generate_db_name() -> str:
    timestamp = datetime.now().strftime("%Y_%m%d_%H%M")
    return f"{DB_PREFIX}{timestamp}.db"

def find_latest_database(directory: Path) -> Path | None:
    """Find the most recent elog database."""
    candidates = []
    for path in directory.glob(f"{DB_PREFIX}*.db"):
        if DB_PATTERN.match(path.name):
            candidates.append(path)

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)
```

---

### 5. Configuration Hierarchy

**Problem**: Current config handling has subtle bugs (e.g., checking `!= 24` to detect CLI override).

**Solution**: Use a clear hierarchy with explicit merging:

```python
from dataclasses import dataclass, field
from typing import Optional
import os

@dataclass
class Config:
    # Fetch settings
    hours_lookback: float = 168.0
    update_frequency_hours: float = 24.0
    exclude_patterns: list[str] = field(default_factory=list)

    # Execution settings
    parallel_jobs: int = 10

    # Paths
    database_path: Optional[Path] = None

    @classmethod
    def load(cls,
             config_file: Path = None,
             cli_args: dict = None) -> "Config":
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
```

---

### 6. Proper Logging Throughout

**Problem**: Inconsistent logging (some modules use `logging`, others use `print`).

**Solution**: Centralized logging setup:

```python
# utils/logging.py
import logging
import sys

def setup_logging(
    level: int = logging.INFO,
    log_file: Path = None,
    quiet: bool = False
) -> logging.Logger:
    """Configure logging for the application."""

    logger = logging.getLogger("elogfetch")
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
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
```

All modules use:
```python
logger = logging.getLogger("elogfetch")
```

---

## CLI Interface

Using `click` for clean command-line interface:

```python
@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config, verbose):
    """elogfetch: Fetch LCLS experiment data."""
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config.load(config_file=config)
    ctx.obj['verbose'] = verbose


@cli.command()
@click.option('--hours', type=float, help='Hours to look back')
@click.option('--force', is_flag=True, help='Force update regardless of schedule')
@click.option('--dry-run', is_flag=True, help='Show what would be done')
@click.pass_context
def update(ctx, hours, force, dry_run):
    """Update the local database with recent experiments."""
    ...


@cli.command()
@click.argument('experiment')
@click.pass_context
def fetch(ctx, experiment):
    """Fetch data for a specific experiment."""
    ...


@cli.command()
@click.pass_context
def status(ctx):
    """Show status of local database."""
    ...
```

**Usage**:
```bash
# Update database
elogfetch update --hours 24

# Force update
elogfetch update --force

# Check status
elogfetch status

# Fetch specific experiment
elogfetch fetch mfx12345
```

---

## Error Handling Strategy

```python
class FetchElogError(Exception):
    """Base exception for elogfetch."""
    pass

class AuthenticationError(FetchElogError):
    """Kerberos authentication failed."""
    pass

class APIError(FetchElogError):
    """API request failed."""
    def __init__(self, message: str, status_code: int = None, response: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class DatabaseError(FetchElogError):
    """Database operation failed."""
    pass

class LockError(FetchElogError):
    """Failed to acquire lock."""
    pass
```

**Recovery**:
- Authentication errors: Clear message to run `kinit`
- API errors: Retry with exponential backoff (up to 3 times)
- Database errors: Preserve original database, report error
- Lock errors: Report that another instance is running

---

## Multi-User Support

The design inherently supports multi-user operation:

1. **Each user runs their own instance**: No shared daemon or service
2. **Kerberos enforces access**: API returns only authorized experiments
3. **Local database per user**: No shared database files
4. **Lock files are per-database**: Different users have different locks

**Recommended setup per user**:
```yaml
# ~/.config/elogfetch/config.yaml
database_path: ~/experiments/elog.db
hours_lookback: 168
update_frequency_hours: 12
parallel_jobs: 5
```

---

## Database Schema

```sql
-- Experiments table
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    instrument TEXT,
    start_time TEXT,
    end_time TEXT,
    description TEXT,
    updated_at TEXT NOT NULL
);

-- Logbook entries
CREATE TABLE logbook_entries (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    entry_id TEXT NOT NULL,
    author TEXT,
    content TEXT,
    created_at TEXT,
    tags TEXT,  -- JSON array
    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    UNIQUE (experiment_id, entry_id)
);

-- Run table
CREATE TABLE runs (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    run_number INTEGER NOT NULL,
    start_time TEXT,
    end_time TEXT,
    parameters TEXT,  -- JSON object
    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    UNIQUE (experiment_id, run_number)
);

-- Files
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    path TEXT NOT NULL,
    size INTEGER,
    created_at TEXT,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);

-- Questionnaires
CREATE TABLE questionnaires (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    data TEXT,  -- JSON object
    updated_at TEXT,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    UNIQUE (experiment_id)
);

-- Workflows
CREATE TABLE workflows (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER NOT NULL,
    data TEXT,  -- JSON object
    updated_at TEXT,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    UNIQUE (experiment_id)
);

-- Metadata
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
```

---

## Testing Strategy

1. **Unit tests**: Mock API responses, test data processing logic
2. **Integration tests**: Use a test database, verify end-to-end flow
3. **No live API tests in CI**: Require Kerberos auth, run manually

```python
# Example unit test
def test_find_latest_database(tmp_path):
    # Create test databases
    (tmp_path / "elog_2024_0101_0000.db").touch()
    (tmp_path / "elog_2024_0615_1200.db").touch()
    (tmp_path / "other.db").touch()  # Should be ignored

    latest = find_latest_database(tmp_path)

    assert latest.name == "elog_2024_0615_1200.db"
```

---

## Migration from Current System

Users of the current `periodic_update.py` can migrate by:

1. Install new package: `pip install elogfetch`
2. Create config file from existing YAML
3. Run initial sync: `elogfetch update --hours 720` (30 days)
4. Set up cron with new command

The database schema is different, so existing `.db` files are not compatible. A fresh sync is required.

---

## Future Enhancements (Not in Initial Scope)

- Web UI for browsing local database
- Incremental sync (only changed entries)
- Export to other formats (CSV, JSON)
- Search across experiments
- Integration with Jupyter notebooks
