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
    op.create_table(
        "chat_request_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_key", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_request_log_id", "chat_request_log", ["id"], unique=False)
    op.create_index("ix_chat_request_log_client_key", "chat_request_log", ["client_key"], unique=False)
    op.create_index("ix_chat_request_log_created_at", "chat_request_log", ["created_at"], unique=False)
    op.create_index(
        "ix_chat_request_log_key_time",
        "chat_request_log",
        ["client_key", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chat_request_log_key_time", table_name="chat_request_log")
    op.drop_index("ix_chat_request_log_created_at", table_name="chat_request_log")
    op.drop_index("ix_chat_request_log_client_key", table_name="chat_request_log")
    op.drop_index("ix_chat_request_log_id", table_name="chat_request_log")
    op.drop_table("chat_request_log")
