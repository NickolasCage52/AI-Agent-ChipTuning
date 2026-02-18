from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import CatalogJob
from app.schemas import CatalogJobIn, CatalogJobOut
from app.repositories.catalog import CatalogRepository

router = APIRouter(prefix="/api/catalog", tags=["catalog"])


@router.get("/jobs", response_model=list[CatalogJobOut])
async def search_jobs(query: str | None = None, db: AsyncSession = Depends(get_db)) -> list[CatalogJob]:
    repo = CatalogRepository(db)
    return await repo.search_jobs(query)


@router.post("/jobs", response_model=CatalogJobOut)
async def create_job(payload: CatalogJobIn, db: AsyncSession = Depends(get_db)) -> CatalogJob:
    repo = CatalogRepository(db)
    job = CatalogJob(**payload.model_dump())
    await repo.create_job(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.put("/jobs/{job_id}", response_model=CatalogJobOut)
async def update_job(job_id: uuid.UUID, payload: CatalogJobIn, db: AsyncSession = Depends(get_db)) -> CatalogJob:
    repo = CatalogRepository(db)
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for k, v in payload.model_dump().items():
        setattr(job, k, v)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    repo = CatalogRepository(db)
    ok = await repo.delete_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.commit()
    return {"ok": True}

