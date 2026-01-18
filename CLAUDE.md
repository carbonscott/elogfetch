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
python -m pytest              # Run all tests
python -m pytest -v           # Verbose output
python -m pytest --cov=elogfetch --cov-report=term-missing  # With coverage
```

**Note:** Always use `python -m pytest` instead of `pytest` to ensure tests run with the virtual environment's Python interpreter.

## Code Quality

```bash
black src/
ruff check src/ --fix
```
