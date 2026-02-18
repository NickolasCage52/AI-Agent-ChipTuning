from __future__ import annotations

import base64
import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.catalog import CatalogJobOut, PricingRuleOut
from app.schemas.common import CarHint, ClientContact
from app.schemas.estimates import EstimateOut
from app.schemas.leads import LeadOutExpanded, LeadPatch
from app.schemas.suppliers import SupplierOfferOut


class ToolCallAudit(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result_summary: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0
    request_id: str | None = None


class ToolCreateLeadIn(BaseModel):
    channel: str
    contact: ClientContact = Field(default_factory=ClientContact)
    problem_text: str | None = None
    car_hint: CarHint = Field(default_factory=CarHint)


class ToolCreateLeadOut(BaseModel):
    lead: LeadOutExpanded


class ToolUpdateLeadIn(BaseModel):
    lead_id: uuid.UUID
    fields: LeadPatch


class ToolUpdateLeadOut(BaseModel):
    lead: LeadOutExpanded


class ToolGetCatalogJobsIn(BaseModel):
    query: str | None = None
    car_context: dict[str, Any] | None = None


class ToolGetCatalogJobsOut(BaseModel):
    jobs: list[CatalogJobOut]


class ToolGetPricingRulesIn(BaseModel):
    pass


class ToolGetPricingRulesOut(BaseModel):
    rules: list[PricingRuleOut]


class ToolBuildEstimateIn(BaseModel):
    lead_id: uuid.UUID
    jobs: list[dict[str, Any]] = Field(default_factory=list)
    pricing_rules: list[dict[str, Any]] = Field(default_factory=list)
    parts: list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = None


class ToolBuildEstimateOut(BaseModel):
    estimate: EstimateOut


class ToolSaveEstimateIn(BaseModel):
    lead_id: uuid.UUID
    estimate_id: uuid.UUID | None = None
    ui: dict[str, Any] | None = None


class ToolSaveEstimateOut(BaseModel):
    ok: bool = True


class ToolRequestApprovalIn(BaseModel):
    lead_id: uuid.UUID
    estimate_id: uuid.UUID | None = None


class ToolRequestApprovalOut(BaseModel):
    ok: bool = True


class ToolSearchPartsIn(BaseModel):
    query: str
    car_context: dict[str, Any] | None = None


class ToolSearchPartsOut(BaseModel):
    offers: list[SupplierOfferOut]


class ToolCompareSupplierOffersIn(BaseModel):
    part_key: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] | None = None


class ToolCompareSupplierOffersOut(BaseModel):
    offers: list[SupplierOfferOut]


class ToolImportSupplierPriceIn(BaseModel):
    supplier_id: uuid.UUID
    filename: str = "price.csv"
    content_base64: str

    def decode(self) -> bytes:
        return base64.b64decode(self.content_base64)


class ToolImportSupplierPriceOut(BaseModel):
    supplier_id: uuid.UUID
    imported: int


class ToolLogAgentRunIn(BaseModel):
    lead_id: uuid.UUID
    user_message: str
    agent_plan: dict[str, Any] | None = None
    tool_calls: list[ToolCallAudit] = Field(default_factory=list)
    final_answer: str | None = None


class ToolLogAgentRunOut(BaseModel):
    ok: bool = True


class ToolAppendEventIn(BaseModel):
    lead_id: uuid.UUID
    event_type: str
    payload: dict[str, Any] | None = None


class ToolAppendEventOut(BaseModel):
    ok: bool = True


class ToolFindActiveLeadByTgIn(BaseModel):
    tg_id: int


class ToolFindActiveLeadByTgOut(BaseModel):
    lead_id: uuid.UUID | None = None


class ToolCreateWidgetSessionIn(BaseModel):
    channel: str = "widget"
    metadata: dict[str, Any] | None = None


class ToolCreateWidgetSessionOut(BaseModel):
    session_id: uuid.UUID
    lead_id: uuid.UUID


class ToolGetWidgetSessionIn(BaseModel):
    session_id: uuid.UUID


class ToolGetWidgetSessionOut(BaseModel):
    session_id: uuid.UUID
    lead_id: uuid.UUID

