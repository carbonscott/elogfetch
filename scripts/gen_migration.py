import sys
from pathlib import Path

from alembic import command
from sqlalchemy import create_engine
from testcontainers.postgres import PostgresContainer

import elogfetch.storage.models as _models  # noqa: F401
from elogfetch.storage.schema import alembic_config

ROOT = Path(__file__).parent.parent

POSTGRES_IMAGE = "postgres:17"
POSTGRES_DRIVER = "psycopg"
VERSIONS_DIR = ROOT / "src" / "elogfetch" / "alembic" / "versions"


def main() -> None:
    message = input("Migration name: ").strip()
    if not message:
        print("Aborted: migration name cannot be empty.")
        sys.exit(1)

    before = {f for f in VERSIONS_DIR.glob("*.py") if f.name != "__init__.py"}

    print(f"Starting {POSTGRES_IMAGE}...")
    with PostgresContainer(POSTGRES_IMAGE) as pg:
        engine = create_engine(pg.get_connection_url(driver=POSTGRES_DRIVER))
        cfg = alembic_config(engine)
        command.upgrade(cfg, "head")
        command.revision(cfg, autogenerate=True, message=message)
        engine.dispose()

    new_files = {
        f for f in VERSIONS_DIR.glob("*.py") if f.name != "__init__.py"
    } - before
    for f in sorted(new_files):
        print(f"Generated: {f.name}")


if __name__ == "__main__":
    main()
