"""tg_sessions and tg_search_history

Revision ID: 0006_tg_sessions
Revises: 0005_vehicle_catalog
Create Date: 2026-02-27

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_tg_sessions"
down_revision = "0005_vehicle_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tg_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(50), nullable=True, server_default="idle"),
        sa.Column("car_context", postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_intent", sa.String(50), nullable=True),
        sa.Column("clarification_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("pending_questions", postgresql.JSONB(), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True, server_default=sa.func.now()),
    )
    op.create_index("ix_tg_sessions_tg_user_id", "tg_sessions", ["tg_user_id"], unique=True)

    op.create_table(
        "tg_search_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("raw_query", sa.Text(), nullable=True),
        sa.Column("masked_query", sa.Text(), nullable=True),
        sa.Column("intent", sa.String(50), nullable=True),
        sa.Column("slots", postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("clarifications", postgresql.JSONB(), nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("results", postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("selected_tier", sa.String(20), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=True, server_default=sa.func.now()),
    )
    op.create_index("ix_tg_search_history_tg_user_id", "tg_search_history", ["tg_user_id"])
    op.create_index("ix_tg_search_history_created_at", "tg_search_history", ["created_at"])


def downgrade() -> None:
    op.drop_table("tg_search_history")
    op.drop_table("tg_sessions")
