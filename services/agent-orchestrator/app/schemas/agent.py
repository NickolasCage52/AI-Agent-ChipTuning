from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.common import ClientContact


class AgentMessageIn(BaseModel):
    channel: str
    lead_id: uuid.UUID | None = None
    message: str
    client_contact: ClientContact | None = None


class AgentAction(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentCitation(BaseModel):
    title: str
    section: str | None = None


class EstimateUIJob(BaseModel):
    name: str
    qty: int = 1
    unit_price: float | None = None
    total: float | None = None


class EstimateUIPart(BaseModel):
    name: str
    brand: str | None = None
    oem: str | None = None
    sku: str | None = None
    qty: int = 1
    unit_price: float | None = None
    total: float | None = None
    supplier_id: str | None = None
    stock: int | None = None
    delivery_days: int | None = None


class EstimateUITotals(BaseModel):
    jobs_total: float | None = None
    parts_total: float | None = None
    total: float | None = None


class EstimateUI(BaseModel):
    jobs: list[EstimateUIJob] = Field(default_factory=list)
    # parts grouped by tier (эконом/оптимум/OEM)
    parts: dict[Literal["economy", "optimum", "oem"], list[EstimateUIPart]] = Field(
        default_factory=lambda: {"economy": [], "optimum": [], "oem": []}
    )
    totals: EstimateUITotals = Field(default_factory=EstimateUITotals)
    requires_approval: bool = True


class AgentResponse(BaseModel):
    answer_text: str
    questions: list[str] = Field(default_factory=list)
    estimate_ui: EstimateUI | None = None
    next_step: str
    citations: list[AgentCitation] = Field(default_factory=list)


class AgentMessageOut(BaseModel):
    lead_id: uuid.UUID
    # legacy plain string (kept for compatibility with older UI/demo scripts)
    answer: str
    response: AgentResponse
    actions: list[AgentAction] = Field(default_factory=list)
    requires_approval: bool = False
    draft_estimate: dict[str, Any] | None = None

