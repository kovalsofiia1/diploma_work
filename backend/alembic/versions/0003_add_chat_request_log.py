"""add chat request log

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Legacy bootstrap may have created this table before stamping revision 0001.
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("chat_request_log"):
        op.create_table(
            "chat_request_log",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("client_key", sa.String(length=80), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = (
        ("ix_chat_request_log_id", ("id",)),
        ("ix_chat_request_log_client_key", ("client_key",)),
        ("ix_chat_request_log_created_at", ("created_at",)),
        ("ix_chat_request_log_key_time", ("client_key", "created_at")),
    )
    existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("chat_request_log")}
    for name, columns in indexes:
        if name not in existing_indexes:
            op.create_index(name, "chat_request_log", list(columns), unique=False)


def downgrade() -> None:
    op.drop_index("ix_chat_request_log_key_time", table_name="chat_request_log")
    op.drop_index("ix_chat_request_log_created_at", table_name="chat_request_log")
    op.drop_index("ix_chat_request_log_client_key", table_name="chat_request_log")
    op.drop_index("ix_chat_request_log_id", table_name="chat_request_log")
    op.drop_table("chat_request_log")
