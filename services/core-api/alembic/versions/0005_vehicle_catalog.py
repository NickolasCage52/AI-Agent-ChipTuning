"""vehicle catalog (makes, models, engines)

Revision ID: 0005_vehicle_catalog
Revises: 0004_rag_fulltext
Create Date: 2026-02-27

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_vehicle_catalog"
down_revision = "0004_rag_fulltext"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_makes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name_ru", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
    )
    op.create_index("ix_vehicle_makes_name_ru", "vehicle_makes", ["name_ru"])
    op.create_index("ix_vehicle_makes_slug", "vehicle_makes", ["slug"], unique=True)

    op.create_table(
        "vehicle_models",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("make_id", sa.Integer(), nullable=False),
        sa.Column("name_ru", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("year_to", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["make_id"], ["vehicle_makes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_vehicle_models_make_id", "vehicle_models", ["make_id"])
    op.create_index("ix_vehicle_models_name_ru", "vehicle_models", ["name_ru"])

    op.create_table(
        "vehicle_engines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("name_ru", sa.String(150), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("displacement", sa.Numeric(3, 1), nullable=True),
        sa.Column("fuel", sa.String(20), nullable=True),
        sa.Column("power_hp", sa.Integer(), nullable=True),
        sa.Column("year_from", sa.Integer(), nullable=True),
        sa.Column("year_to", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["model_id"], ["vehicle_models.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_vehicle_engines_model_id", "vehicle_engines", ["model_id"])


def downgrade() -> None:
    op.drop_table("vehicle_engines")
    op.drop_table("vehicle_models")
    op.drop_table("vehicle_makes")
