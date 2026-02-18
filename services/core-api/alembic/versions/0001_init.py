"""init schema

Revision ID: 0001_init
Revises: 
Create Date: 2026-02-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("tg_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_clients_phone", "clients", ["phone"])
    op.create_index("ix_clients_tg_id", "clients", ["tg_id"])

    op.create_table(
        "cars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vin", sa.String(length=64), nullable=True),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("engine", sa.String(length=100), nullable=True),
        sa.Column("mileage", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
    )
    op.create_index("ix_cars_client_id", "cars", ["client_id"])
    op.create_index("ix_cars_vin", "cars", ["vin"])
    op.create_index("ix_cars_brand", "cars", ["brand"])
    op.create_index("ix_cars_model", "cars", ["model"])
    op.create_index("ix_cars_year", "cars", ["year"])

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("car_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("problem_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["car_id"], ["cars.id"]),
    )
    op.create_index("ix_leads_client_id", "leads", ["client_id"])
    op.create_index("ix_leads_car_id", "leads", ["car_id"])
    op.create_index("ix_leads_status", "leads", ["status"])

    op.create_table(
        "catalog_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("norm_hours", sa.Numeric(10, 2), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("applicability", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_catalog_jobs_code", "catalog_jobs", ["code"], unique=True)
    op.create_index("ix_catalog_jobs_name", "catalog_jobs", ["name"])

    op.create_table(
        "pricing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_pricing_rules_name", "pricing_rules", ["name"], unique=True)

    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("contacts", sa.Text(), nullable=True),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"], unique=True)

    op.create_table(
        "supplier_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("oem", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=True),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=True),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
    )
    op.create_index("ix_supplier_offers_supplier_id", "supplier_offers", ["supplier_id"])
    op.create_index("ix_supplier_offers_sku", "supplier_offers", ["sku"])
    op.create_index("ix_supplier_offers_oem", "supplier_offers", ["oem"])
    op.create_index("ix_supplier_offers_name", "supplier_offers", ["name"])
    op.create_index("ix_supplier_offers_brand", "supplier_offers", ["brand"])
    op.create_index("ix_supplier_offers_price", "supplier_offers", ["price"])
    op.create_index("ix_supplier_offers_stock", "supplier_offers", ["stock"])
    op.create_index("ix_supplier_offers_delivery_days", "supplier_offers", ["delivery_days"])
    op.create_index("ix_supplier_offers_supplier_sku_oem", "supplier_offers", ["supplier_id", "sku", "oem"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=False), nullable=False),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("agent_plan", postgresql.JSONB(), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("final_answer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
    )
    op.create_index("ix_agent_runs_lead_id", "agent_runs", ["lead_id"])

    op.create_table(
        "estimates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("approved_by", sa.String(length=200), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"]),
    )
    op.create_index("ix_estimates_lead_id", "estimates", ["lead_id"])
    op.create_index("ix_estimates_requires_approval", "estimates", ["requires_approval"])


def downgrade() -> None:
    op.drop_table("estimates")
    op.drop_table("agent_runs")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("supplier_offers")
    op.drop_table("suppliers")
    op.drop_table("pricing_rules")
    op.drop_table("catalog_jobs")
    op.drop_table("leads")
    op.drop_table("cars")
    op.drop_table("clients")

