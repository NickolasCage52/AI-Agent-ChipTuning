from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import Car, Client, Lead
from app.schemas.common import CarHint, ClientContact


class LeadRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_or_create_client(self, contact: ClientContact) -> Client:
        q = None
        if contact.tg_id is not None:
            q = select(Client).where(Client.tg_id == contact.tg_id)
        elif contact.phone:
            q = select(Client).where(Client.phone == contact.phone)

        client = (await self.db.execute(q)).scalar_one_or_none() if q is not None else None
        if client:
            if contact.name and not client.name:
                client.name = contact.name
            if contact.email and not client.email:
                client.email = contact.email
            if contact.phone and not client.phone:
                client.phone = contact.phone
            return client

        client = Client(name=contact.name, phone=contact.phone, email=contact.email, tg_id=contact.tg_id)
        self.db.add(client)
        await self.db.flush()
        return client

    async def create_car(self, client_id: uuid.UUID, car_hint: CarHint) -> Car:
        car = Car(
            client_id=client_id,
            vin=car_hint.vin,
            brand=car_hint.brand,
            model=car_hint.model,
            year=car_hint.year,
            engine=car_hint.engine,
            mileage=car_hint.mileage,
        )
        self.db.add(car)
        await self.db.flush()
        return car

    async def create_lead(self, channel: str, contact: ClientContact, problem_text: str | None, car_hint: CarHint) -> Lead:
        client = await self.find_or_create_client(contact)
        car = await self.create_car(client.id, car_hint) if any(vars(car_hint).values()) else None
        lead = Lead(client_id=client.id, car_id=car.id if car else None, channel=channel, status="new", problem_text=problem_text)
        self.db.add(lead)
        await self.db.flush()
        return lead

    async def get(self, lead_id: uuid.UUID) -> Lead | None:
        return await self.db.get(Lead, lead_id)

    async def get_expanded(self, lead_id: uuid.UUID) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id).options(joinedload(Lead.client), joinedload(Lead.car))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list(self, status: str | None = None, limit: int = 200) -> list[Lead]:
        stmt = select(Lead).order_by(Lead.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(Lead.status == status)
        return (await self.db.execute(stmt)).scalars().all()

    async def update_lead_fields(self, lead: Lead, fields: dict) -> Lead:
        for k, v in fields.items():
            if v is None:
                continue
            if hasattr(lead, k):
                setattr(lead, k, v)
        lead.updated_at = datetime.utcnow()
        self.db.add(lead)
        await self.db.flush()
        return lead

    async def update_client(self, client_id: uuid.UUID, contact: dict) -> Client:
        client = await self.db.get(Client, client_id)
        if not client:
            raise RuntimeError("Client not found")
        for k in ("name", "phone", "email", "tg_id"):
            v = contact.get(k)
            if v is not None:
                setattr(client, k, v)
        self.db.add(client)
        await self.db.flush()
        return client

    async def upsert_lead_car(self, lead: Lead, car_hint: dict) -> Car:
        if lead.car_id:
            car = await self.db.get(Car, lead.car_id)
            if not car:
                car = Car(client_id=lead.client_id)
                self.db.add(car)
                await self.db.flush()
                lead.car_id = car.id
        else:
            car = Car(client_id=lead.client_id)
            self.db.add(car)
            await self.db.flush()
            lead.car_id = car.id

        for k in ("vin", "brand", "model", "year", "engine", "mileage"):
            v = car_hint.get(k)
            if v is not None:
                setattr(car, k, v)
        self.db.add(car)
        self.db.add(lead)
        await self.db.flush()
        return car

