from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.estimate_logic import build_draft_estimate
from app.models import Estimate, Lead, PricingRule
from app.settings import settings


class EstimateRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_and_save(
        self,
        *,
        lead_id: uuid.UUID,
        jobs: list[dict],
        parts: list[dict],
        pricing_rules: list[dict] | None,
        notes: str | None = None,
    ) -> Estimate:
        lead = await self.db.get(Lead, lead_id)
        if not lead:
            raise ValueError("Lead not found")
        rules = pricing_rules or []
        if not rules:
            db_rules = (await self.db.execute(select(PricingRule).order_by(PricingRule.id.asc()))).scalars().all()
            rules = [{"rule_type": r.rule_type, "params": r.params or {}} for r in db_rules]
        draft = build_draft_estimate(
            lead_id=str(lead_id),
            jobs=jobs,
            parts=parts,
            pricing_rules=rules,
            notes=notes,
        )
        est = Estimate(
            lead_id=lead_id,
            items=draft["items"],
            total_price=float(Decimal(str(draft["total_price"]))),
            requires_approval=bool(settings.estimate_requires_approval),
        )
        self.db.add(est)
        lead.status = "estimated"
        self.db.add(lead)
        await self.db.flush()
        return est

    async def approve(self, estimate_id: uuid.UUID, approved_by: str) -> Estimate:
        est = await self.db.get(Estimate, estimate_id)
        if not est:
            raise ValueError("Estimate not found")
        est.requires_approval = False
        est.approved_by = approved_by
        est.approved_at = datetime.utcnow()
        self.db.add(est)
        lead = await self.db.get(Lead, est.lead_id)
        if lead:
            lead.status = "approved"
            self.db.add(lead)
        await self.db.flush()
        return est

    async def list_for_lead(self, lead_id: uuid.UUID | None, limit: int = 200) -> list[Estimate]:
        stmt = select(Estimate).order_by(Estimate.created_at.desc()).limit(limit)
        if lead_id:
            stmt = stmt.where(Estimate.lead_id == lead_id)
        return (await self.db.execute(stmt)).scalars().all()

    async def get(self, estimate_id: uuid.UUID) -> Estimate | None:
        return await self.db.get(Estimate, estimate_id)

    async def attach_ui(self, estimate_id: uuid.UUID, ui: dict) -> Estimate:
        est = await self.db.get(Estimate, estimate_id)
        if not est:
            raise ValueError("Estimate not found")
        items = est.items or {}
        if not isinstance(items, dict):
            items = {"items": items}
        items["ui"] = ui
        est.items = items
        self.db.add(est)
        await self.db.flush()
        return est

