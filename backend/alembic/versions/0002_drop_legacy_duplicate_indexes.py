"""drop legacy duplicate indexes

Databases created before Alembic got extra indexes from the ALTER guards in
create_all_tables() that duplicate constraints the models already declare.
On a database created by the baseline migration this is a no-op.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# legacy index -> what already enforces or covers the same thing
DUPLICATE_INDEXES = {
    "ix_city_activity_log_type": "ix_city_activity_log_activity_type",
    "uq_city_scrape_state_city": "ix_city_scrape_state_city (unique)",
    "uq_city_scrape_state_city_key": "city_scrape_state_pkey",
    "uq_events_source_idx": "uq_events_source",
    "uq_tickets_event_seat_idx": "uq_tickets_event_seat",
}


def upgrade() -> None:
    for name in DUPLICATE_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")


def downgrade() -> None:
    # The dropped indexes were redundant; nothing to restore
    pass
