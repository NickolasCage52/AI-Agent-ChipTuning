from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Intent = Literal["to_service", "parts_search", "problem_symptom", "unknown"]


class AgentPlan(BaseModel):
    intent: Intent
    required_slots: list[str] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    next_action: Literal["ask_questions", "call_tools"] = "ask_questions"
    tools_to_call: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True


REQUIRED_SLOTS: dict[Intent, list[str]] = {
    "to_service": ["brand", "model", "year", "mileage"],
    "parts_search": ["part_query", "brand", "model", "year"],
    "problem_symptom": ["brand", "model", "year"],
    "unknown": ["brand", "model", "year"],
}


TOOLS_BY_INTENT: dict[Intent, list[str]] = {
    "to_service": ["get_catalog_jobs", "search_parts", "build_estimate", "request_approval", "save_estimate"],
    "parts_search": ["search_parts", "compare_supplier_offers", "build_estimate", "request_approval", "save_estimate"],
    "problem_symptom": ["get_catalog_jobs", "build_estimate", "request_approval", "save_estimate"],
    "unknown": ["update_lead"],
}


def build_plan(intent: Intent, slots: dict[str, Any], *, require_approval: bool) -> AgentPlan:
    required = REQUIRED_SLOTS.get(intent, REQUIRED_SLOTS["unknown"])
    missing = [s for s in required if not slots.get(s)]
    next_action: Literal["ask_questions", "call_tools"] = "ask_questions" if missing else "call_tools"
    tools = [] if missing else TOOLS_BY_INTENT.get(intent, [])
    return AgentPlan(
        intent=intent,
        required_slots=required,
        missing_slots=missing,
        next_action=next_action,
        tools_to_call=tools,
        requires_human_approval=bool(require_approval),
    )

