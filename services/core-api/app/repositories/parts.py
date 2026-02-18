from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SupplierOffer


class PartsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(self, query: str, limit: int = 50) -> list[SupplierOffer]:
        q = f"%{query.strip().lower()}%"
        stmt = (
            select(SupplierOffer)
            .where(or_(SupplierOffer.sku.ilike(q), SupplierOffer.oem.ilike(q), SupplierOffer.name.ilike(q), SupplierOffer.brand.ilike(q)))
            .order_by(SupplierOffer.stock.desc().nullslast(), SupplierOffer.price.asc().nullslast(), SupplierOffer.delivery_days.asc().nullslast())
            .limit(limit)
        )
        return (await self.db.execute(stmt)).scalars().all()

    async def compare(self, sku: str | None, oem: str | None, limit: int = 20) -> list[SupplierOffer]:
        stmt = select(SupplierOffer)
        if sku:
            stmt = stmt.where(SupplierOffer.sku == sku)
        if oem:
            stmt = stmt.where(SupplierOffer.oem == oem)
        stmt = stmt.order_by(SupplierOffer.stock.desc().nullslast(), SupplierOffer.price.asc().nullslast(), SupplierOffer.delivery_days.asc().nullslast()).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()

