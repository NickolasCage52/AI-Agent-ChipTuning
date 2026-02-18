from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WidgetSession


class WidgetSessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, *, lead_id: uuid.UUID, metadata: dict[str, Any] | None) -> WidgetSession:
        ws = WidgetSession(lead_id=lead_id, session_meta=metadata, last_seen_at=datetime.utcnow())
        self.db.add(ws)
        await self.db.flush()
        return ws

    async def get(self, session_id: uuid.UUID) -> WidgetSession | None:
        return await self.db.get(WidgetSession, session_id)

    async def touch(self, session_id: uuid.UUID) -> WidgetSession | None:
        ws = await self.get(session_id)
        if not ws:
            return None
        ws.last_seen_at = datetime.utcnow()
        self.db.add(ws)
        await self.db.flush()
        return ws

    async def get_by_lead(self, lead_id: uuid.UUID) -> WidgetSession | None:
        stmt = select(WidgetSession).where(WidgetSession.lead_id == lead_id).order_by(WidgetSession.created_at.desc()).limit(1)
        return (await self.db.execute(stmt)).scalar_one_or_none()

