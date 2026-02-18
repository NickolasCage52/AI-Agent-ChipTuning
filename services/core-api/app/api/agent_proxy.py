from __future__ import annotations

from fastapi import APIRouter, HTTPException
import httpx

from app.schemas import AgentMessageIn, AgentMessageOut
from app.settings import settings

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/message", response_model=AgentMessageOut)
async def agent_message(payload: AgentMessageIn) -> AgentMessageOut:
    url = f"{settings.orchestrator_url.rstrip('/')}/api/agent/message"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(url, json=payload.model_dump(mode="json"))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Orchestrator unavailable: {e}") from e
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Orchestrator error: {r.status_code} {r.text}")
    return AgentMessageOut.model_validate(r.json())

