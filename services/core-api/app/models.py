from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.utcnow()


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tg_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, nullable=False)

    cars: Mapped[list["Car"]] = relationship(back_populates="client")
    leads: Mapped[list["Lead"]] = relationship(back_populates="client")


class Car(Base):
    __tablename__ = "cars"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    vin: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    engine: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="cars")
    leads: Mapped[list["Lead"]] = relationship(back_populates="car")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    car_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cars.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new", index=True)
    problem_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, onupdate=utcnow, nullable=False)

    client: Mapped["Client"] = relationship(back_populates="leads")
    car: Mapped["Car | None"] = relationship(back_populates="leads")
    estimates: Mapped[list["Estimate"]] = relationship(back_populates="lead")


class CatalogJob(Base):
    __tablename__ = "catalog_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    norm_hours: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    applicability: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class PricingRule(Base):
    __tablename__ = "pricing_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contacts: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierOffer(Base):
    __tablename__ = "supplier_offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False, index=True)
    sku: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    oem: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True, index=True)
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_supplier_offers_supplier_sku_oem", "supplier_id", "sku", "oem"),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, nullable=False)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)  # reserved for real embeddings
    # NOTE: attribute name "metadata" is reserved in SQLAlchemy declarative models.
    chunk_meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    agent_plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, nullable=False)


class Estimate(Base):
    __tablename__ = "estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    items: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, nullable=False)

    lead: Mapped["Lead"] = relationship(back_populates="estimates")


class LeadEvent(Base):
    __tablename__ = "lead_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_lead_events_lead_created", "lead_id", "created_at"),
    )


class WidgetSession(Base):
    __tablename__ = "widget_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, nullable=False, index=True)
    # NOTE: attribute name "metadata" is reserved in SQLAlchemy declarative models.
    session_meta: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)

