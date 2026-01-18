# elogfetch

Fetch LCLS experiment data from the electronic logbook (elog) system and store it in a local SQLite database.

## Installation

This package requires `krtc` which is only available in SLAC conda environments.

### Setup

1. Create a `.env` file from the template:
```bash
cp .env.example .env
```

2. Edit `.env` to set paths for your environment (`UV_CACHE_DIR` and `UV_PYTHON`)

3. Create a virtual environment and install:
```bash
set -a; source .env; set +a
uv venv --python $UV_PYTHON --system-site-packages
unset UV_PYTHON  # so uv pip targets .venv, not the conda env
uv pip install -e .
```

4. Activate the environment:
```bash
source .venv/bin/activate
```

### Available conda environments with krtc
```bash
ls /sdf/group/lcls/ds/ana/sw/conda1/inst/envs/
```

## Prerequisites

- Valid Kerberos ticket for SLAC authentication
- Python 3.9+ (from a SLAC conda environment with `krtc`)

Before using, authenticate with Kerberos:
```bash
kinit
```

## Usage

### Check status
```bash
elogfetch status
```

### Update database with recent experiments
```bash
# Fetch experiments updated in the last 24 hours
elogfetch update --hours 24

# Dry run to see what would be fetched
elogfetch update --hours 24 --dry-run

# Exclude certain experiments
elogfetch update --hours 24 --exclude 'txi*' --exclude 'test*'

# Specify output directory
elogfetch update --hours 168 --output-dir /path/to/data

# Run with more parallel jobs for faster fetching
elogfetch update --hours 24 --parallel 20

# Incrementally update an existing database
elogfetch update --hours 24 --incremental

# Update a specific database file
elogfetch update --hours 24 --incremental /path/to/existing.db
```

### Fetch a specific experiment
```bash
elogfetch fetch mfxl1033223
```

### Retry failed experiments
```bash
# Retry experiments that failed in a previous run
elogfetch retry

# Retry from a specific failed_experiments.json file
elogfetch retry --file /path/to/failed_experiments.json
```

### List recently updated experiments
```bash
elogfetch list-experiments --hours 72
```

## Configuration

Create a config file at `~/.config/elogfetch/config.yaml`:

```yaml
hours_lookback: 168
exclude_patterns:
  - "txi*"
  - "test*"
parallel_jobs: 10
database_dir: ~/experiments
```

Configuration precedence: CLI args > environment variables > config file > defaults

### Environment Variables

- `FETCH_ELOG_HOURS_LOOKBACK`: Hours to look back
- `FETCH_ELOG_PARALLEL_JOBS`: Number of parallel jobs
- `FETCH_ELOG_DATABASE_DIR`: Database directory

### Advanced Options

The `update` command supports tuning parameters for large datasets:
- `--queue-size`: Buffer size for streaming (default: 100)
- `--batch-size`: Experiments per database commit (default: 50)

## Database

The database is stored as `elog_YYYY_MMDD_HHMM.db` with the following tables:

- `Experiment`: Experiment metadata
- `Run`: Run information
- `RunProductionData`: Production statistics per run
- `Detector`: Detector definitions
- `RunDetector`: Detector status per run
- `Logbook`: Logbook entries
- `Questionnaire`: Proposal questionnaires
- `Workflow`: Workflow definitions
- `Metadata`: Key-value store for fetch metadata

## Development

```bash
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/ --fix
```
