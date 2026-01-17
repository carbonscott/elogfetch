# elogfetch Development Instructions

## Environment Setup

Always activate the virtual environment before running commands:

```bash
source .venv/bin/activate
```

## Running the CLI

```bash
elogfetch -h                    # Show help
elogfetch status                # Check database status
elogfetch update -H 24          # Fetch experiments updated in last 24 hours
elogfetch fetch <experiment_id> # Fetch a specific experiment
```

## Testing

```bash
pytest
```

## Code Quality

```bash
black src/
ruff check src/ --fix
```
