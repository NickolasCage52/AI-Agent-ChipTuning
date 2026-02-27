from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.chat.intent_extractor import extract_intent_and_slots, extract_sku_from_message
from app.chat.parts_search import rank_and_tier, search_by_sku_oem, search_parts
from app.db.deps import get_db
from app.logging_events import log_event
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    car_context: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    summary: str
    questions: list[dict[str, Any]] = Field(default_factory=list)
    bundles: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    next_step: str
    safety_notes: list[str] = Field(default_factory=list)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())
    car = req.car_context or {}

    extracted = extract_intent_and_slots(req.message, car)

    log_event(
        "query_created",
        {
            "session_id": session_id,
            "message": req.message[:200],
            "car_context": car,
            "intent": extracted.get("intent"),
            "part_type": extracted.get("part_type"),
        },
    )

    if extracted.get("questions"):
        log_event("clarification_asked", {"session_id": session_id, "questions": extracted["questions"]})
        part_label = extracted.get("part_type") or "запчасть"
        brand = car.get("brand", "")
        model = car.get("model", "")
        ctx_str = f"для {brand} {model}".strip() if (brand or model) else ""
        return ChatResponse(
            session_id=session_id,
            summary=f"Подбираю {part_label} {ctx_str}.".strip(),
            questions=extracted["questions"],
            bundles={},
            next_step="ask_clarification",
            safety_notes=[],
        )

    part_type = extracted.get("part_type") or req.message

    sku = extract_sku_from_message(req.message)
    if sku:
        parts = await search_by_sku_oem(sku, db)
        if not parts:
            log_event("no_results", {"session_id": session_id, "reason": "no_sku", "sku": sku})
            return ChatResponse(
                session_id=session_id,
                summary=f"По артикулу {sku} ничего не нашлось. Уточните марку авто, чтобы подобрать аналоги.",
                questions=[{"id": "q_clarify", "text": "Уточните марку авто или попробуйте другой артикул.", "expected_type": "string"}],
                bundles={},
                next_step="ask_clarification",
                safety_notes=[],
            )
    else:
        parts = await search_parts(part_type, car, db)

    if not parts:
        log_event("no_results", {"session_id": session_id, "reason": "no_data", "part_type": part_type})
        return ChatResponse(
            session_id=session_id,
            summary=f"По запросу «{part_type}» ничего не нашлось.",
            questions=[{"id": "q_clarify", "text": "Уточните марку авто или попробуйте другое название детали.", "expected_type": "string"}],
            bundles={},
            next_step="ask_clarification",
            safety_notes=[],
        )

    tiers = rank_and_tier(parts, car_brand=car.get("brand"), car_model=car.get("model"))

    log_event(
        "offers_shown",
        {
            "session_id": session_id,
            "economy_count": len(tiers["economy"]),
            "optimal_count": len(tiers["optimal"]),
            "oem_count": len(tiers["oem"]),
        },
    )

    safety: list[str] = []
    if not car.get("vin"):
        safety.append("Применимость подтверждена по марке/модели/году. Для 100% точности укажите VIN.")

    brand = car.get("brand", "")
    model = car.get("model", "")
    ctx_str = f"для {brand} {model}".strip() if (brand or model) else ""
    summary = f"Нашёл варианты {part_type} {ctx_str}.".strip()

    return ChatResponse(
        session_id=session_id,
        summary=summary,
        questions=[],
        bundles=tiers,
        next_step="show_offers",
        safety_notes=safety,
    )
