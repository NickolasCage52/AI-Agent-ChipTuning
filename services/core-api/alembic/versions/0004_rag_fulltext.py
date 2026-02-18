"""rag full-text search

Revision ID: 0004_rag_fulltext
Revises: 0003_widget_sessions
Create Date: 2026-02-17
"""

from __future__ import annotations

from alembic import op

revision = "0004_rag_fulltext"
down_revision = "0003_widget_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Generated column keeps itself in sync with chunk_text (no triggers needed).
    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN IF NOT EXISTS tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', coalesce(chunk_text, ''))) STORED
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_tsv ON document_chunks USING GIN (tsv)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS tsv")

