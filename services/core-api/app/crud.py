from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, Car, CatalogJob, Client, Estimate, Lead, PricingRule, Supplier, SupplierOffer
from app.schemas import CarHint, ClientContact
from app.supplier_import import NormalizedOffer


async def find_or_create_client(db: AsyncSession, contact: ClientContact) -> Client:
    q = None
    if contact.tg_id is not None:
        q = select(Client).where(Client.tg_id == contact.tg_id)
    elif contact.phone:
        q = select(Client).where(Client.phone == contact.phone)

    client = (await db.execute(q)).scalar_one_or_none() if q is not None else None
    if client:
        # soft-update known fields
        if contact.name and not client.name:
            client.name = contact.name
        if contact.email and not client.email:
            client.email = contact.email
        if contact.phone and not client.phone:
            client.phone = contact.phone
        return client

    client = Client(
        name=contact.name,
        phone=contact.phone,
        email=contact.email,
        tg_id=contact.tg_id,
    )
    db.add(client)
    await db.flush()
    return client


async def create_car(db: AsyncSession, client_id: uuid.UUID, car_hint: CarHint) -> Car:
    car = Car(
        client_id=client_id,
        vin=car_hint.vin,
        brand=car_hint.brand,
        model=car_hint.model,
        year=car_hint.year,
        engine=car_hint.engine,
        mileage=car_hint.mileage,
    )
    db.add(car)
    await db.flush()
    return car


async def create_lead(db: AsyncSession, channel: str, contact: ClientContact, problem_text: str | None, car_hint: CarHint) -> Lead:
    client = await find_or_create_client(db, contact)
    car = await create_car(db, client.id, car_hint) if any(vars(car_hint).values()) else None
    lead = Lead(
        client_id=client.id,
        car_id=car.id if car else None,
        channel=channel,
        status="new",
        problem_text=problem_text,
    )
    db.add(lead)
    await db.flush()
    return lead


async def update_lead(db: AsyncSession, lead: Lead, fields: dict) -> Lead:
    for k, v in fields.items():
        if v is None:
            continue
        if hasattr(lead, k):
            setattr(lead, k, v)
    lead.updated_at = datetime.utcnow()
    db.add(lead)
    await db.flush()
    return lead


async def update_client(db: AsyncSession, client_id: uuid.UUID, contact: dict) -> Client:
    client = await db.get(Client, client_id)
    if not client:
        raise RuntimeError("Client not found")
    for k in ("name", "phone", "email", "tg_id"):
        v = contact.get(k)
        if v is not None:
            setattr(client, k, v)
    db.add(client)
    await db.flush()
    return client


async def upsert_lead_car(db: AsyncSession, lead: Lead, car_hint: dict) -> Car:
    if lead.car_id:
        car = await db.get(Car, lead.car_id)
        if not car:
            # inconsistent state, recreate
            car = Car(client_id=lead.client_id)
            db.add(car)
            await db.flush()
            lead.car_id = car.id
    else:
        car = Car(client_id=lead.client_id)
        db.add(car)
        await db.flush()
        lead.car_id = car.id

    for k in ("vin", "brand", "model", "year", "engine", "mileage"):
        v = car_hint.get(k)
        if v is not None:
            setattr(car, k, v)
    db.add(car)
    db.add(lead)
    await db.flush()
    return car


async def search_catalog_jobs(db: AsyncSession, query: str | None) -> list[CatalogJob]:
    if not query:
        return (await db.execute(select(CatalogJob).order_by(CatalogJob.name).limit(50))).scalars().all()
    q = f"%{query.lower()}%"
    stmt = (
        select(CatalogJob)
        .where(or_(CatalogJob.code.ilike(q), CatalogJob.name.ilike(q), CatalogJob.description.ilike(q)))
        .order_by(CatalogJob.name)
        .limit(50)
    )
    return (await db.execute(stmt)).scalars().all()


async def list_pricing_rules(db: AsyncSession) -> list[PricingRule]:
    return (await db.execute(select(PricingRule).order_by(PricingRule.name))).scalars().all()


async def list_suppliers(db: AsyncSession) -> list[Supplier]:
    return (await db.execute(select(Supplier).order_by(Supplier.name))).scalars().all()


async def upsert_supplier_offers(db: AsyncSession, supplier_id: uuid.UUID, offers: list[NormalizedOffer]) -> int:
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
        existing = (await db.execute(stmt.limit(1))).scalar_one_or_none()

        if existing:
            existing.oem = oem or existing.oem
            existing.sku = sku or existing.sku
            existing.name = name or existing.name
            existing.brand = o.brand or existing.brand
            existing.price = float(o.price) if o.price is not None else existing.price
            existing.stock = o.stock if o.stock is not None else existing.stock
            existing.delivery_days = o.delivery_days if o.delivery_days is not None else existing.delivery_days
            db.add(existing)
        else:
            db.add(
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
    await db.flush()
    return count


async def search_parts(db: AsyncSession, query: str, limit: int = 50) -> list[SupplierOffer]:
    q = f"%{query.strip().lower()}%"
    stmt = (
        select(SupplierOffer)
        .where(or_(SupplierOffer.sku.ilike(q), SupplierOffer.oem.ilike(q), SupplierOffer.name.ilike(q), SupplierOffer.brand.ilike(q)))
        .order_by(SupplierOffer.stock.desc().nullslast(), SupplierOffer.price.asc().nullslast(), SupplierOffer.delivery_days.asc().nullslast())
        .limit(limit)
    )
    return (await db.execute(stmt)).scalars().all()


async def compare_offers(db: AsyncSession, sku: str | None, oem: str | None, limit: int = 20) -> list[SupplierOffer]:
    stmt = select(SupplierOffer)
    if sku:
        stmt = stmt.where(SupplierOffer.sku == sku)
    if oem:
        stmt = stmt.where(SupplierOffer.oem == oem)
    stmt = stmt.order_by(SupplierOffer.stock.desc().nullslast(), SupplierOffer.price.asc().nullslast(), SupplierOffer.delivery_days.asc().nullslast()).limit(limit)
    return (await db.execute(stmt)).scalars().all()


def create_agent_run(
    db: AsyncSession,
    lead_id: uuid.UUID,
    user_message: str,
    agent_plan: dict | None,
    tool_calls: list[dict] | None,
    final_answer: str | None,
) -> AgentRun:
    ar = AgentRun(
        lead_id=lead_id,
        user_message=user_message,
        agent_plan=agent_plan,
        tool_calls=tool_calls,
        final_answer=final_answer,
    )
    db.add(ar)
    # flush is done by callers (async)
    return ar


def create_estimate(
    db: AsyncSession,
    lead_id: uuid.UUID,
    items: dict,
    total_price: Decimal,
    requires_approval: bool = True,
) -> Estimate:
    est = Estimate(
        lead_id=lead_id,
        items=items,
        total_price=float(total_price),
        requires_approval=requires_approval,
    )
    db.add(est)
    # flush is done by callers (async)
    return est

