from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentRunIn(BaseModel):
    lead_id: uuid.UUID
    user_message: str
    agent_plan: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] | None = None
    final_answer: str | None = None


class AgentRunOut(AgentRunIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime

