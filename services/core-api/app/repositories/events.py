from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LeadEvent


class LeadEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def append(
        self,
        *,
        lead_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any] | None,
        request_id: str | None,
    ) -> LeadEvent:
        ev = LeadEvent(lead_id=lead_id, event_type=event_type, payload=payload, request_id=request_id)
        self.db.add(ev)
        await self.db.flush()
        return ev

    async def list_for_lead(self, lead_id: uuid.UUID, limit: int = 500) -> list[LeadEvent]:
        stmt = select(LeadEvent).where(LeadEvent.lead_id == lead_id).order_by(LeadEvent.created_at.asc()).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()

