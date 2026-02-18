from __future__ import annotations

import os
import re
import uuid
from datetime import datetime

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.logging_config import setup_logging
from app.models import Document, DocumentChunk
from app.settings import settings


setup_logging()
app = FastAPI(title="autoshop rag-service (mvp)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _chunk_text(text: str, max_len: int = 800) -> list[tuple[str, str]]:
    """
    Very small deterministic chunker with section support for markdown.
    Returns list of (section, chunk_text).
    """
    clean = text.replace("\r", "")
    lines = clean.split("\n")
    current_section = "Введение"
    section_blocks: list[tuple[str, str]] = []
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        raw = "\n".join(buf).strip()
        buf = []
        if raw:
            section_blocks.append((current_section, raw))

    for line in lines:
        m = re.match(r"^\s{0,3}#{1,6}\s+(.*)$", line)
        if m:
            flush()
            title = (m.group(1) or "").strip()
            current_section = title or current_section
            continue
        buf.append(line)
    flush()

    out: list[tuple[str, str]] = []
    for section, block in section_blocks:
        parts = [p.strip() for p in block.split("\n\n") if p.strip()]
        for p in parts:
            while len(p) > max_len:
                out.append((section, p[:max_len]))
                p = p[max_len:]
            out.append((section, p))
    return out[:2000]


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/rag/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    _ensure_dir(settings.documents_dir)
    content = await file.read()
    title = file.filename or "document"
    doc_id = uuid.uuid4()
    path = os.path.join(settings.documents_dir, f"{doc_id}_{title}")
    with open(path, "wb") as f:
        f.write(content)

    # MVP: treat everything as text (utf-8 best-effort)
    text = content.decode("utf-8", errors="ignore")
    chunks = _chunk_text(text)

    doc = Document(id=doc_id, title=title, source="upload", file_path=path, uploaded_at=datetime.utcnow())
    db.add(doc)
    for idx, (section, ch) in enumerate(chunks):
        db.add(
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_id,
                chunk_text=ch,
                embedding=None,
                chunk_meta={"chunk": idx, "filename": title, "section": section},
            )
        )
    db.commit()
    return {"document_id": str(doc_id), "title": title, "chunks": len(chunks)}


@app.post("/api/rag/query")
async def query(payload: dict, db: Session = Depends(get_db)) -> dict:
    q = (payload.get("query") or "").strip()
    top_k = int(payload.get("top_k") or 3)
    if not q:
        return {"results": []}

    top_k = max(1, min(top_k, 10))
    tsq = func.plainto_tsquery("simple", q)
    rank = func.ts_rank_cd(DocumentChunk.tsv, tsq)
    stmt = (
        select(DocumentChunk, Document, rank.label("rank"))
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.tsv.op("@@")(tsq))
        .order_by(rank.desc())
        .limit(top_k)
    )
    rows = db.execute(stmt).all()
    results = []
    for chunk, doc, _ in rows:
        results.append(
            {
                "document_id": str(doc.id),
                "title": doc.title,
                "metadata": chunk.chunk_meta or {},
                "chunk_text": chunk.chunk_text[:500],
            }
        )
    return {"results": results}

