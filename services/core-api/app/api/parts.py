from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import SupplierOffer
from app.schemas import SupplierOfferOut
from app.repositories.parts import PartsRepository

router = APIRouter(prefix="/api/parts", tags=["parts"])


@router.get("/search", response_model=list[SupplierOfferOut])
async def search_parts(query: str, db: AsyncSession = Depends(get_db)) -> list[SupplierOffer]:
    repo = PartsRepository(db)
    return await repo.search(query)


@router.get("/compare", response_model=list[SupplierOfferOut])
async def compare_offers(sku: str | None = None, oem: str | None = None, db: AsyncSession = Depends(get_db)) -> list[SupplierOffer]:
    repo = PartsRepository(db)
    return await repo.compare(sku=sku, oem=oem)

