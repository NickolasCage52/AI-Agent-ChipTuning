from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import PricingRule
from app.schemas import PricingRuleIn, PricingRuleOut
from app.repositories.catalog import CatalogRepository
from app.seed import ensure_seed

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/seed")
async def seed(db: AsyncSession = Depends(get_db)) -> dict:
    await ensure_seed(db)
    return {"ok": True}


@router.get("/pricing_rules", response_model=list[PricingRuleOut])
async def list_pricing_rules(db: AsyncSession = Depends(get_db)):
    repo = CatalogRepository(db)
    return await repo.list_pricing_rules()


@router.post("/pricing_rules", response_model=PricingRuleOut)
async def create_pricing_rule(payload: PricingRuleIn, db: AsyncSession = Depends(get_db)) -> PricingRule:
    repo = CatalogRepository(db)
    rule = PricingRule(**payload.model_dump())
    await repo.create_pricing_rule(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/pricing_rules/{rule_id}", response_model=PricingRuleOut)
async def update_pricing_rule(rule_id: uuid.UUID, payload: PricingRuleIn, db: AsyncSession = Depends(get_db)) -> PricingRule:
    repo = CatalogRepository(db)
    rule = await repo.get_pricing_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    for k, v in payload.model_dump().items():
        setattr(rule, k, v)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/pricing_rules/{rule_id}")
async def delete_pricing_rule(rule_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    repo = CatalogRepository(db)
    ok = await repo.delete_pricing_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    await db.commit()
    return {"ok": True}

