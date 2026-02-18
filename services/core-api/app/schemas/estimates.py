from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EstimateJobItem(BaseModel):
    type: Literal["job"] = "job"
    code: str
    name: str
    qty: float = 1
    unit_price: float
    total: float


class EstimatePartItem(BaseModel):
    type: Literal["part"] = "part"
    sku: str | None = None
    oem: str | None = None
    name: str
    brand: str | None = None
    qty: float = 1
    unit_price: float
    total: float
    supplier_id: uuid.UUID | None = None
    delivery_days: int | None = None
    stock: int | None = None


class DraftEstimate(BaseModel):
    lead_id: uuid.UUID
    items: dict[str, Any]
    total_price: float
    requires_approval: bool = True


class EstimateBuildIn(BaseModel):
    lead_id: uuid.UUID
    jobs: list[dict[str, Any]] = Field(default_factory=list, description="Jobs from catalog or user-selected")
    pricing_rules: list[dict[str, Any]] = Field(default_factory=list)
    parts: list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = None


class EstimateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    lead_id: uuid.UUID
    items: dict[str, Any]
    total_price: float
    requires_approval: bool
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime


class EstimateApproveIn(BaseModel):
    approved_by: str

