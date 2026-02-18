from __future__ import annotations

from pydantic import BaseModel


class ClientContact(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    tg_id: int | None = None

