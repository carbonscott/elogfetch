.DEFAULT_GOAL := help

.PHONY: help migration schema test

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

migration:  ## Generate an Alembic migration from SQLModel (uses testcontainers)
	uv run python scripts/gen_migration.py
	uv run python -m pytest tests/test_migrations.py -v

# Install Node deps only when the lockfile changes (skipped if node_modules is current)
scripts/dbml/node_modules: scripts/dbml/package-lock.json
	npm ci --prefix scripts/dbml
	@touch scripts/dbml/node_modules

schema: scripts/dbml/node_modules  ## Regenerate schema/db.sql and schema/db.dbml from SQLModel metadata
	uv run python scripts/gen_ddl.py
	cd scripts/dbml && npx ts-node sql_to_dbml.ts

test:  ## Run all tests
	uv run python -m pytest -v