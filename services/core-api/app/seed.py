from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import CatalogJob, Document, DocumentChunk, PricingRule, Supplier, SupplierOffer
from app.repositories.suppliers import SupplierRepository
from app.supplier_import import parse_supplier_price


async def ensure_seed(db: AsyncSession | None = None) -> None:
    owns_session = db is None
    if db is None:
        db = AsyncSessionLocal()

    async def ensure_job(code: str, **fields) -> None:
        existing = (await db.execute(select(CatalogJob).where(CatalogJob.code == code))).scalar_one_or_none()
        if existing:
            return
        db.add(CatalogJob(code=code, **fields))

    async def ensure_rule(name: str, rule_type: str, params: dict) -> None:
        existing = (await db.execute(select(PricingRule).where(PricingRule.name == name))).scalar_one_or_none()
        if existing:
            return
        db.add(PricingRule(name=name, rule_type=rule_type, params=params))

    async def ensure_supplier(name: str, **fields) -> Supplier:
        existing = (await db.execute(select(Supplier).where(Supplier.name == name))).scalar_one_or_none()
        if existing:
            return existing
        s = Supplier(name=name, **fields)
        db.add(s)
        await db.flush()
        return s

    def chunk_text(text: str, max_len: int = 800) -> list[tuple[str, str]]:
        """
        Deterministic chunker with markdown section support.
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

    async def ensure_seed_doc(path: Path) -> None:
        title = path.name
        # Be resilient if a document with the same title was uploaded multiple times.
        # (Upload endpoint is intentionally simple in MVP and may create duplicates.)
        existing = (await db.execute(select(Document).where(Document.title == title).limit(1))).scalars().first()
        if existing:
            return
        content = path.read_bytes()
        text = content.decode("utf-8", errors="ignore")
        doc_id = uuid.uuid4()
        db.add(Document(id=doc_id, title=title, source="seed", file_path=str(path)))
        for idx, (section, ch) in enumerate(chunk_text(text)):
            db.add(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc_id,
                    chunk_text=ch,
                    embedding=None,
                    chunk_meta={"chunk": idx, "filename": title, "section": section},
                )
            )

    # Slice 2 seed: 6+ jobs
    await ensure_job(
        "TO_OIL_FILTER",
        name="ТО: замена масла + масляного фильтра",
        description="Регламентное ТО. Итог уточняется по осмотру и выбранным расходникам.",
        base_price=2500,
        norm_hours=1.0,
        tags={"category": "maintenance", "keywords": ["maintenance", "oil", "filter"]},
        applicability={"note": "универсально"},
    )
    await ensure_job(
        "TO_AIR_FILTER",
        name="ТО: замена воздушного фильтра",
        description="Замена воздушного фильтра двигателя.",
        base_price=900,
        norm_hours=0.3,
        tags={"category": "maintenance", "keywords": ["maintenance", "air", "filter"]},
        applicability={"note": "универсально"},
    )
    await ensure_job(
        "TO_CABIN_FILTER",
        name="ТО: замена салонного фильтра",
        description="Замена салонного фильтра.",
        base_price=900,
        norm_hours=0.3,
        tags={"category": "maintenance", "keywords": ["maintenance", "cabin", "filter"]},
        applicability={"note": "универсально"},
    )
    await ensure_job(
        "BRAKE_INSPECTION",
        name="Осмотр тормозной системы",
        description="Осмотр колодок/дисков/суппортов, рекомендации по замене.",
        base_price=800,
        norm_hours=0.4,
        tags={"category": "inspection", "keywords": ["brake", "inspection"]},
        applicability={"note": "универсально"},
    )
    await ensure_job(
        "DIAG_SUSP",
        name="Диагностика подвески",
        description="Диагностика причины стука/люфта. Диагноз не утверждается без осмотра.",
        base_price=1500,
        norm_hours=0.7,
        tags={"category": "diagnostics", "keywords": ["symptom", "suspension", "noise"]},
        applicability={"note": "для всех авто"},
    )
    await ensure_job(
        "DIAG_ECU",
        name="Компьютерная диагностика (сканер)",
        description="Считывание ошибок, первичная оценка. Не заменяет осмотр/проверки.",
        base_price=1200,
        norm_hours=0.5,
        tags={"category": "diagnostics", "keywords": ["diagnostics", "scanner"]},
        applicability={"note": "для всех авто"},
    )

    # Demo seed: 3 pricing rules (deterministic engine)
    await ensure_rule("Urgent +15%", "percent_add_total", {"percent": 15})
    await ensure_rule("Complexity +20%", "percent_add_total", {"percent": 20})
    await ensure_rule("Seasonal +10%", "percent_add_total", {"percent": 10})
    await ensure_rule("Diagnostics fee +500", "fixed_add_total", {"amount": 500})
    await ensure_rule("Warranty handling +5%", "percent_mult_total", {"percent": 5})

    # Demo seed: suppliers + 50+ offers total from demo-data
    demo_supplier = await ensure_supplier(
        "DemoSupplier",
        terms="Demo terms",
        delivery_days=2,
        contacts="demo@example.local",
    )
    alt_supplier = await ensure_supplier(
        "AltSupplier",
        terms="Alt demo terms",
        delivery_days=3,
        contacts="alt@example.local",
    )

    demo_dir = Path(os.environ.get("DEMO_DATA_DIR") or "/demo-data")
    demo_csv = demo_dir / "suppliers" / "demo.csv"
    if demo_csv.exists():
        content = demo_csv.read_bytes()
        offers = parse_supplier_price(demo_csv.name, content)
        repo = SupplierRepository(db)
        await repo.upsert_offers(demo_supplier.id, offers)

    alt_csv = demo_dir / "supplier_price.csv"
    if alt_csv.exists():
        content = alt_csv.read_bytes()
        offers = parse_supplier_price(alt_csv.name, content)
        repo = SupplierRepository(db)
        await repo.upsert_offers(alt_supplier.id, offers)

    # Demo seed: 2-3 local docs for RAG (tsvector search)
    docs_dir = demo_dir / "docs"
    if docs_dir.exists():
        docs = sorted([p for p in docs_dir.iterdir() if p.is_file() and p.suffix.lower() in (".md", ".txt")])
        for p in docs[:3]:
            await ensure_seed_doc(p)

    await db.commit()
    if owns_session:
        await db.close()

