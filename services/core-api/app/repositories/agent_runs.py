from __future__ import annotations

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun


class AgentRunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
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
        self.db.add(ar)
        await self.db.flush()
        return ar

    async def list_for_lead(self, lead_id: uuid.UUID, limit: int = 200) -> list[AgentRun]:
        stmt = select(AgentRun).where(AgentRun.lead_id == lead_id).order_by(AgentRun.created_at.desc()).limit(limit)
        return (await self.db.execute(stmt)).scalars().all()

