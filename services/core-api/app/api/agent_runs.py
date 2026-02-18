from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.models import AgentRun
from app.schemas import AgentRunIn, AgentRunOut
from app.repositories.agent_runs import AgentRunRepository

router = APIRouter(prefix="/api/agent_runs", tags=["agent_runs"])


@router.post("", response_model=AgentRunOut)
async def create_agent_run(payload: AgentRunIn, db: AsyncSession = Depends(get_db)) -> AgentRun:
    repo = AgentRunRepository(db)
    ar = await repo.create(
        lead_id=payload.lead_id,
        user_message=payload.user_message,
        agent_plan=payload.agent_plan,
        tool_calls=payload.tool_calls,
        final_answer=payload.final_answer,
    )
    await db.commit()
    await db.refresh(ar)
    return ar


@router.get("", response_model=list[AgentRunOut])
async def list_agent_runs(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[AgentRun]:
    repo = AgentRunRepository(db)
    return await repo.list_for_lead(lead_id, limit=200)

