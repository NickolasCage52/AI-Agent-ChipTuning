from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import Document
from app.schemas import DocumentOut
from app.settings import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)) -> list[Document]:
    stmt = select(Document).order_by(Document.uploaded_at.desc()).limit(200)
    return (await db.execute(stmt)).scalars().all()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)) -> dict:
    """
    Proxy upload to rag-service to reuse chunking/indexing logic.
    """
    url = f"{settings.rag_url.rstrip('/')}/api/rag/upload"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, files={"file": (file.filename or "document.txt", await file.read())})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RAG service unavailable: {e}") from e
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"RAG error: {r.status_code} {r.text}")
    return r.json()

