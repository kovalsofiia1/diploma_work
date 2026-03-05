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
    from app.models import ticket  # noqa: F401
    from app.models import checkin  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Lightweight dev-time schema guard for new columns (use Alembic in prod)
    with engine.begin() as conn:
        # Ensure critical columns exist (best-effort; safe if already present)
        conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER"))
        conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS source_type VARCHAR(16)"))
        conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS source_name VARCHAR(64)"))
        conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS source_event_id VARCHAR(128)"))
        conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS source_url VARCHAR(1024)"))
        conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS status VARCHAR(16)"))
        conn.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS is_verified BOOLEAN"))
        # Ensure unified events table indexes exist (best-effort)
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_events_uid ON events (uid)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_events_source_idx ON events (source_name, source_event_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_events_city ON events (city)"))

        # Tickets table evolves frequently; add new columns if missing
        conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS seat_id VARCHAR(64)"))
        conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS seat VARCHAR(64)"))
        conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS token_id INTEGER"))
        conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ticket_hash VARCHAR(66)"))
        conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS tx_hash VARCHAR(66)"))
        conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS used BOOLEAN"))
        conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS status VARCHAR(16)"))
        conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS blockchain_tx_hash VARCHAR(66)"))
        # Helpful indexes/uniqueness
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tickets_seat_id ON tickets (seat_id)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_tickets_event_seat_idx ON tickets (event_id, seat_id)"))

