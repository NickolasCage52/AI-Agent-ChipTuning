from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import Supplier
from app.schemas import SupplierOut
from app.repositories.suppliers import SupplierRepository
from app.repositories.events import LeadEventRepository
from app.supplier_import import parse_supplier_price

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierOut])
async def list_suppliers(db: AsyncSession = Depends(get_db)) -> list[Supplier]:
    repo = SupplierRepository(db)
    return await repo.list_suppliers()


@router.post("/import")
async def import_price(
    request: Request,
    lead_id: uuid.UUID | None = Form(None),
    supplier_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = SupplierRepository(db)
    supplier = await repo.get_supplier(supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    content = await file.read()
    offers = parse_supplier_price(file.filename or "price.csv", content)
    count = await repo.upsert_offers(supplier_id, offers)
    if lead_id is not None:
        ev = LeadEventRepository(db)
        await ev.append(
            lead_id=lead_id,
            event_type="supplier.price_imported",
            payload={"supplier_id": str(supplier_id), "filename": file.filename, "imported": count},
            request_id=getattr(request.state, "request_id", None),
        )
    await db.commit()
    return {"supplier_id": str(supplier_id), "imported": count}

