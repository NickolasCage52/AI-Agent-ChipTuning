from __future__ import annotations

from pydantic import BaseModel


class ClientContact(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    tg_id: int | None = None


class CarHint(BaseModel):
    vin: str | None = None
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    engine: str | None = None
    mileage: int | None = None

