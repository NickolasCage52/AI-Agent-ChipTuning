"""widget sessions

Revision ID: 0003_widget_sessions
Revises: 0002_lead_events
Create Date: 2026-02-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_widget_sessions"
down_revision = "0002_lead_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "widget_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
    )
    op.create_index("ix_widget_sessions_lead_id", "widget_sessions", ["lead_id"])
    op.create_index("ix_widget_sessions_last_seen_at", "widget_sessions", ["last_seen_at"])


def downgrade() -> None:
    op.drop_table("widget_sessions")

