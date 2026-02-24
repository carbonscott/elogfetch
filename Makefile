.DEFAULT_GOAL := help

.PHONY: help migration test 

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

migration:  ## Generate an Alembic migration from SQLModel (uses testcontainers)
	uv run python scripts/gen_migration.py
	uv run python -m pytest tests/test_migrations.py -v

test:  ## Run all tests
	uv run python -m pytest -v
	
