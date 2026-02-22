# elogfetch

Fetch LCLS experiment data from the electronic logbook (elog) system and store it in a local SQLite database.

## Prerequisites

- Python 3.10+
- `mamba` or `conda` (build-time only, for krb5 headers)
- SLAC Kerberos credentials (prompted automatically on first use)

## Installation

Authentication uses the `gssapi` package, which can be compiled if we have `krb5-config` binary in our path + related headers `gssapi`-related shared libs. On S3DF we do not have the `krb5-devel` package installed, so that binary is not present. However the `krb5` conda package has that binary, so we can create a minmal conda environment to provide these at build time.

### Setup (S3DF)

1. Create a minimal conda environment with the krb5 headers:

```bash
cd elogfetch
mamba create --prefix $(pwd)/.krb5 krb5
```

1. Install dependencies, pointing `gssapi`'s build to the right place:

```bash
GSSAPI_KRB5CONFIG=$(pwd)/.krb5/bin/krb5-config \
GSSAPI_MAIN_LIB=/usr/lib64/libgssapi_krb5.so.2 \
uv sync
```

1. Activate the virtual environment:

```bash
source .venv/bin/activate
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

## Operations

### Backfilling Missing Experiments

If experiments are missing from the database (e.g., an instrument had no activity during the normal lookback window), you can run a one-time backfill with a longer lookback period.

**Why experiments might be missing:**

- The cron job uses a 7-day (168 hour) lookback window by default
- Experiments only appear in the API response if they had elog activity within the lookback period
- If an instrument was inactive for longer than the lookback window, its experiments won't be captured

**Safe backfill procedure:**

```bash
# 1. Activate the environment
source env.sh
source .venv/bin/activate

# 2. Verify Kerberos ticket
klist -s || kinit

# 3. (Optional) Dry-run to see what would be fetched
elogfetch update --dry-run --hours 2160 \
  --output-dir /path/to/data

# 4. Run backfill with extended lookback (e.g., 90 days = 2160 hours)
elogfetch update --incremental --hours 2160 --parallel 10 \
  --output-dir /path/to/data

# 5. Update the symlink to point to new database
cd /path/to/data
latest_db=$(ls -t elog_*.db | head -1)
ln -sf "$latest_db" elog-copilot.db

# 6. Verify the missing experiments were added
sqlite3 elog-copilot.db "SELECT experiment_id, start_time FROM Experiment WHERE instrument='tmo' ORDER BY start_time DESC LIMIT 10;"
```

**Why this is safe:**

- The `.elogfetch.lock` file prevents cron from running simultaneously
- Creates a new timestamped database file (doesn't overwrite existing ones)
- Uses `--incremental` to preserve existing data and only update changed experiments
- The next cron run will use the backfilled database as its base

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
uv sync

# Run tests (use python -m to ensure correct interpreter)
uv run pytest
uv run pytest -v # Verbose
uv run pytest --cov=elogfetch --cov-report=term-missing # Coverage

# Format code
uv run ruff format src/
uv run ruff check src/ --fix
```

## Technical Notes

### Database Journal Mode

During operation, elogfetch uses SQLite WAL (Write-Ahead Logging) mode for better concurrent write performance. When the database is closed, it is automatically converted to DELETE journal mode for maximum portability.

This ensures the resulting database file can be read by any SQLite client without requiring write permissions to create temporary `-wal` and `-shm` files.
