# fetch-elog

Fetch LCLS experiment data from the electronic logbook (elog) system and store it in a local SQLite database.

## Installation

Using uv with SLAC conda environment:
```bash
export UV_CACHE_DIR=/sdf/data/lcls/ds/prj/prjdat21/results/cwang31/.UV_CACHE
cd /sdf/data/lcls/ds/prj/prjcwang31/results/fetch-elog
uv pip install -e . --python /sdf/scratch/users/c/cwang31/miniconda/ana-4.0.59-torch/bin/python
```

Or with pip in an environment that has `krtc`:
```bash
pip install -e .
```

## Prerequisites

- Valid Kerberos ticket for SLAC authentication
- Python 3.9+
- `krtc` package (SLAC-specific, not on PyPI - available in SLAC conda environments)

Before using, authenticate with Kerberos:
```bash
kinit
```

## Usage

### Check status
```bash
fetch-elog status
```

### Update database with recent experiments
```bash
# Fetch experiments updated in the last 24 hours
fetch-elog update --hours 24

# Dry run to see what would be fetched
fetch-elog update --hours 24 --dry-run

# Exclude certain experiments
fetch-elog update --hours 24 --exclude 'txi*' --exclude 'test*'

# Specify output directory
fetch-elog update --hours 168 --output-dir /path/to/data
```

### Fetch a specific experiment
```bash
fetch-elog fetch mfxl1033223
```

### List recently updated experiments
```bash
fetch-elog list-experiments --hours 72
```

## Configuration

Create a config file at `~/.config/fetch-elog/config.yaml`:

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
