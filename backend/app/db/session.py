from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    # Import models for metadata
    from app.models import user  # noqa: F401
    from app.models import event  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Lightweight dev-time schema guard for new columns (use Alembic in prod)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE events_internal ADD COLUMN IF NOT EXISTS uid VARCHAR(128)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_events_internal_uid ON events_internal (uid)"))
        conn.execute(text("ALTER TABLE external_events ADD COLUMN IF NOT EXISTS uid VARCHAR(128)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_external_events_uid ON external_events (uid)"))
        # Backfill missing uids so lookups by uid always work
        conn.execute(text("UPDATE events_internal SET uid = 'internal:' || id::text WHERE uid IS NULL"))
        conn.execute(text("UPDATE external_events SET uid = 'external:' || id::text WHERE uid IS NULL"))

