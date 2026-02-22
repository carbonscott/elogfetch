"""Alembic configuration helper for elogfetch SQLModel models."""


from pathlib import Path

from alembic.config import Config
from sqlalchemy.engine import Engine

# Alembic scripts live alongside this package, not at the repo root.
_ALEMBIC_DIR = Path(__file__).parents[1] / "alembic"


def alembic_config(engine: Engine) -> Config:
    """Return an Alembic Config wired to the bundled alembic directory and *engine*."""
    cfg = Config()
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    # render_as_string keeps the password in the URL for programmatic use
    cfg.set_main_option(
        "sqlalchemy.url",
        engine.url.render_as_string(hide_password=False),
    )
    return cfg
