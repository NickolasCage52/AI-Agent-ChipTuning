from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CarHint, ClientContact


class ClientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str | None
    phone: str | None
    email: str | None
    tg_id: int | None
    created_at: datetime


class CarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    client_id: uuid.UUID
    vin: str | None
    brand: str | None
    model: str | None
    year: int | None
    engine: str | None
    mileage: int | None


class LeadCreate(BaseModel):
    channel: str = Field(..., examples=["telegram", "web"])
    contact: ClientContact = Field(default_factory=ClientContact)
    problem_text: str | None = None
    car_hint: CarHint = Field(default_factory=CarHint)


class LeadPatch(BaseModel):
    status: str | None = None
    problem_text: str | None = None
    channel: str | None = None
    contact: ClientContact | None = None
    car_hint: CarHint | None = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    client_id: uuid.UUID
    car_id: uuid.UUID | None
    channel: str
    status: str
    problem_text: str | None
    created_at: datetime
    updated_at: datetime


class LeadOutExpanded(LeadOut):
    model_config = ConfigDict(from_attributes=True)
    client: ClientOut
    car: CarOut | None

