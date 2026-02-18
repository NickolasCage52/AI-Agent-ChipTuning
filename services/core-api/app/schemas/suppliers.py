from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    terms: str | None = None
    delivery_days: int | None = None
    contacts: str | None = None


class SupplierOfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supplier_id: uuid.UUID
    sku: str | None = None
    oem: str | None = None
    name: str | None = None
    brand: str | None = None
    price: float | None = None
    stock: int | None = None
    delivery_days: int | None = None
    updated_at: datetime

