"""Vehicle catalog API: makes, models, years, engines."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import VehicleMake, VehicleModel, VehicleEngine

router = APIRouter(prefix="/api/vehicle", tags=["vehicle"])


@router.get("/makes")
async def get_makes(
    q: str = Query(default="", description="Поиск по названию"),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Список марок с поиском по названию."""
    stmt = select(VehicleMake).order_by(VehicleMake.name_ru).limit(limit)
    if q:
        stmt = stmt.where(VehicleMake.name_ru.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    makes = result.scalars().all()

    if not makes and not q:
        return {"error": "catalog_empty", "message": "Каталог не загружен. Выполните: python scripts/import_vehicle_catalog.py"}

    return [{"id": m.id, "label": m.name_ru, "value": m.id, "slug": m.slug} for m in makes]


@router.get("/models")
async def get_models(
    make_id: int = Query(..., description="ID марки"),
    q: str = Query(default=""),
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Модели по марке."""
    stmt = (
        select(VehicleModel)
        .where(VehicleModel.make_id == make_id)
        .order_by(VehicleModel.name_ru)
        .limit(limit)
    )
    if q:
        stmt = stmt.where(VehicleModel.name_ru.ilike(f"%{q}%"))
    result = await db.execute(stmt)
    models = result.scalars().all()
    return [
        {
            "id": m.id,
            "label": m.name_ru,
            "value": m.id,
            "year_from": m.year_from,
            "year_to": m.year_to,
        }
        for m in models
    ]


@router.get("/years")
async def get_years(
    model_id: int = Query(..., description="ID модели"),
    db: AsyncSession = Depends(get_db),
):
    """Доступные годы для модели."""
    result = await db.execute(select(VehicleModel).where(VehicleModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        return []

    year_from = model.year_from or 1990
    year_to = model.year_to or 2025

    # Расширяем диапазон по двигателям
    eng_result = await db.execute(select(VehicleEngine).where(VehicleEngine.model_id == model_id))
    engines = eng_result.scalars().all()
    if engines:
        engine_years: list[int] = []
        for e in engines:
            if e.year_from is not None:
                engine_years.append(e.year_from)
            if e.year_to is not None:
                engine_years.append(e.year_to)
        if engine_years:
            year_from = min(year_from, min(engine_years))
            year_to = max(year_to, max(engine_years))

    years = list(range(year_to, year_from - 1, -1))
    return [{"id": y, "label": str(y), "value": y} for y in years]


@router.get("/engines")
async def get_engines(
    model_id: int = Query(..., description="ID модели"),
    year: int = Query(..., description="Год выпуска"),
    db: AsyncSession = Depends(get_db),
):
    """Двигатели для модели и года."""
    stmt = (
        select(VehicleEngine)
        .where(VehicleEngine.model_id == model_id)
        .where(or_(VehicleEngine.year_from.is_(None), VehicleEngine.year_from <= year))
        .where(or_(VehicleEngine.year_to.is_(None), VehicleEngine.year_to >= year))
        .order_by(VehicleEngine.displacement, VehicleEngine.power_hp)
    )
    result = await db.execute(stmt)
    engines = result.scalars().all()

    return [
        {
            "id": e.id,
            "label": e.name_ru,
            "value": e.id,
            "extra": {
                "code": e.code,
                "displacement": float(e.displacement) if e.displacement else None,
                "fuel": e.fuel,
                "power_hp": e.power_hp,
            },
        }
        for e in engines
    ]
