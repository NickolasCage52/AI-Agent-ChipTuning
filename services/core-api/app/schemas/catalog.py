from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict


class CatalogJobIn(BaseModel):
    code: str
    name: str
    description: str | None = None
    base_price: float = 0
    norm_hours: float = 0
    tags: dict[str, Any] | None = None
    applicability: dict[str, Any] | None = None


class CatalogJobOut(CatalogJobIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class PricingRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    rule_type: str
    params: dict[str, Any] | None = None


class PricingRuleIn(BaseModel):
    name: str
    rule_type: str
    params: dict[str, Any] | None = None

