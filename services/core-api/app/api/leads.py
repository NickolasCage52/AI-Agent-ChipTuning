from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import Lead
from app.schemas import LeadCreate, LeadOut, LeadOutExpanded, LeadPatch
from app.repositories.leads import LeadRepository
from app.repositories.events import LeadEventRepository

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", response_model=LeadOut)
async def create_lead(payload: LeadCreate, request: Request, db: AsyncSession = Depends(get_db)) -> Lead:
    repo = LeadRepository(db)
    ev = LeadEventRepository(db)
    lead = await repo.create_lead(payload.channel, payload.contact, payload.problem_text, payload.car_hint)
    await ev.append(
        lead_id=lead.id,
        event_type="lead.created",
        payload={"channel": payload.channel, "problem_text": payload.problem_text, "car_hint": payload.car_hint.model_dump(), "contact": payload.contact.model_dump()},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    await db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
async def patch_lead(lead_id: uuid.UUID, payload: LeadPatch, request: Request, db: AsyncSession = Depends(get_db)) -> Lead:
    repo = LeadRepository(db)
    ev = LeadEventRepository(db)
    lead = await repo.get(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    data = payload.model_dump(exclude_unset=True)

    contact = data.pop("contact", None)
    car_hint = data.pop("car_hint", None)

    lead = await repo.update_lead_fields(lead, data)

    # allow updates via single tool call (agent must not touch DB directly)
    if contact:
        await repo.update_client(lead.client_id, contact)
    if car_hint:
        await repo.upsert_lead_car(lead, car_hint)

    await ev.append(
        lead_id=lead.id,
        event_type="lead.updated",
        payload={"fields": payload.model_dump(exclude_unset=True)},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    await db.refresh(lead)
    return lead


@router.get("", response_model=list[LeadOut])
async def list_leads(status: str | None = None, db: AsyncSession = Depends(get_db)) -> list[Lead]:
    repo = LeadRepository(db)
    return await repo.list(status=status, limit=200)


@router.get("/{lead_id}", response_model=LeadOutExpanded)
async def get_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Lead:
    repo = LeadRepository(db)
    lead = await repo.get_expanded(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

