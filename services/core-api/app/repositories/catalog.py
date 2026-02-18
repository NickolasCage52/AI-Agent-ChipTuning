from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CatalogJob, PricingRule


class CatalogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_jobs(self, query: str | None, limit: int = 50) -> list[CatalogJob]:
        if not query:
            stmt = select(CatalogJob).order_by(CatalogJob.name).limit(limit)
            return (await self.db.execute(stmt)).scalars().all()
        q = f"%{query.lower()}%"
        stmt = (
            select(CatalogJob)
            .where(or_(CatalogJob.code.ilike(q), CatalogJob.name.ilike(q), CatalogJob.description.ilike(q)))
            .order_by(CatalogJob.name)
            .limit(limit)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def list_pricing_rules(self) -> list[PricingRule]:
        stmt = select(PricingRule).order_by(PricingRule.id.asc())
        return (await self.db.execute(stmt)).scalars().all()

    async def create_job(self, job: CatalogJob) -> CatalogJob:
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_job(self, job_id: uuid.UUID) -> CatalogJob | None:
        return await self.db.get(CatalogJob, job_id)

    async def delete_job(self, job_id: uuid.UUID) -> bool:
        job = await self.db.get(CatalogJob, job_id)
        if not job:
            return False
        await self.db.delete(job)
        await self.db.flush()
        return True

    async def get_pricing_rule(self, rule_id: uuid.UUID) -> PricingRule | None:
        return await self.db.get(PricingRule, rule_id)

    async def create_pricing_rule(self, rule: PricingRule) -> PricingRule:
        self.db.add(rule)
        await self.db.flush()
        return rule

    async def delete_pricing_rule(self, rule_id: uuid.UUID) -> bool:
        rule = await self.db.get(PricingRule, rule_id)
        if not rule:
            return False
        await self.db.delete(rule)
        await self.db.flush()
        return True

