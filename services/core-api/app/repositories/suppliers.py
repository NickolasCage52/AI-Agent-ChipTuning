from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Supplier, SupplierOffer
from app.supplier_import import NormalizedOffer


class SupplierRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_suppliers(self) -> list[Supplier]:
        stmt = select(Supplier).order_by(Supplier.name)
        return (await self.db.execute(stmt)).scalars().all()

    async def get_supplier(self, supplier_id: uuid.UUID) -> Supplier | None:
        return await self.db.get(Supplier, supplier_id)

    async def upsert_offers(self, supplier_id: uuid.UUID, offers: list[NormalizedOffer]) -> int:
        count = 0
        for o in offers:
            sku = (o.sku or "").strip() or None
            oem = (o.oem or "").strip() or None
            name = (o.name or "").strip() or None

            stmt = select(SupplierOffer).where(SupplierOffer.supplier_id == supplier_id)
            if sku:
                stmt = stmt.where(SupplierOffer.sku == sku)
            elif oem:
                stmt = stmt.where(SupplierOffer.oem == oem)
            elif name:
                stmt = stmt.where(SupplierOffer.name == name)
            existing = (await self.db.execute(stmt.limit(1))).scalar_one_or_none()

            if existing:
                existing.oem = oem or existing.oem
                existing.sku = sku or existing.sku
                existing.name = name or existing.name
                existing.brand = o.brand or existing.brand
                existing.price = float(o.price) if o.price is not None else existing.price
                existing.stock = o.stock if o.stock is not None else existing.stock
                existing.delivery_days = o.delivery_days if o.delivery_days is not None else existing.delivery_days
                self.db.add(existing)
            else:
                self.db.add(
                    SupplierOffer(
                        supplier_id=supplier_id,
                        sku=sku,
                        oem=oem,
                        name=name,
                        brand=o.brand,
                        price=float(o.price) if o.price is not None else None,
                        stock=o.stock,
                        delivery_days=o.delivery_days,
                    )
                )
            count += 1
        await self.db.flush()
        return count

