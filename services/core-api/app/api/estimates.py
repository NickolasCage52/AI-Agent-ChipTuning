from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import Estimate
from app.schemas import EstimateApproveIn, EstimateBuildIn, EstimateOut
from app.repositories.estimates import EstimateRepository
from app.repositories.events import LeadEventRepository

router = APIRouter(tags=["estimates"])


@router.post("/api/estimate", response_model=EstimateOut)
async def build_estimate(payload: EstimateBuildIn, request: Request, db: AsyncSession = Depends(get_db)) -> Estimate:
    repo = EstimateRepository(db)
    ev = LeadEventRepository(db)
    try:
        est = await repo.build_and_save(
            lead_id=payload.lead_id,
            jobs=payload.jobs,
            parts=payload.parts,
            pricing_rules=payload.pricing_rules,
            notes=payload.notes,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Lead not found")
    await ev.append(
        lead_id=payload.lead_id,
        event_type="estimate.draft_created",
        payload={"estimate_id": str(est.id), "total_price": float(est.total_price), "requires_approval": est.requires_approval},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    await db.refresh(est)
    return est


@router.post("/api/estimate/{estimate_id}/approve", response_model=EstimateOut)
async def approve_estimate(estimate_id: uuid.UUID, payload: EstimateApproveIn, request: Request, db: AsyncSession = Depends(get_db)) -> Estimate:
    repo = EstimateRepository(db)
    ev = LeadEventRepository(db)
    try:
        est = await repo.approve(estimate_id, payload.approved_by)
    except ValueError:
        raise HTTPException(status_code=404, detail="Estimate not found")
    await ev.append(
        lead_id=est.lead_id,
        event_type="estimate.approved",
        payload={"estimate_id": str(est.id), "approved_by": payload.approved_by},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    await db.refresh(est)
    return est


@router.get("/api/estimates", response_model=list[EstimateOut])
async def list_estimates(lead_id: uuid.UUID | None = None, db: AsyncSession = Depends(get_db)) -> list[Estimate]:
    repo = EstimateRepository(db)
    return await repo.list_for_lead(lead_id, limit=200)


@router.get("/api/estimates/{estimate_id}", response_model=EstimateOut)
async def get_estimate(estimate_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Estimate:
    repo = EstimateRepository(db)
    est = await repo.get(estimate_id)
    if not est:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return est

