from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result_summary: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0
    request_id: str | None = None

