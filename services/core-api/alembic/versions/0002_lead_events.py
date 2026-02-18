"""lead events event log

Revision ID: 0002_lead_events
Revises: 0001_init
Create Date: 2026-02-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_lead_events"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
    )
    op.create_index("ix_lead_events_lead_id", "lead_events", ["lead_id"])
    op.create_index("ix_lead_events_event_type", "lead_events", ["event_type"])
    op.create_index("ix_lead_events_request_id", "lead_events", ["request_id"])
    op.create_index("ix_lead_events_created_at", "lead_events", ["created_at"])
    op.create_index("ix_lead_events_lead_created", "lead_events", ["lead_id", "created_at"])


def downgrade() -> None:
    op.drop_table("lead_events")

