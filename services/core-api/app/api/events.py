from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.repositories.events import LeadEventRepository
from app.schemas.events import LeadEventOut

router = APIRouter(prefix="/api/leads", tags=["lead_events"])


@router.get("/{lead_id}/events", response_model=list[LeadEventOut])
async def list_lead_events(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[LeadEventOut]:
    repo = LeadEventRepository(db)
    return await repo.list_for_lead(lead_id)

