import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.config import get_settings
from app.db.session import create_all_tables, engine

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "0001"


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    # Keep the app's logging setup instead of alembic.ini's
    cfg.attributes["configure_logger"] = False
    return cfg


def run_migrations() -> None:
    """Bring the database schema to the latest Alembic revision.

    A database created before Alembic (by create_all() and the ALTER guards)
    has tables but no alembic_version: the legacy guard brings it up to the
    baseline schema once, then it is stamped and handled by Alembic from then on.
    """
    cfg = alembic_config()
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables and "users" in tables:
        logger.info("Existing database without Alembic history: stamping baseline %s", BASELINE_REVISION)
        create_all_tables()
        command.stamp(cfg, BASELINE_REVISION)
    command.upgrade(cfg, "head")
