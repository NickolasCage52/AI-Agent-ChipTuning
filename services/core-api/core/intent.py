"""Intent и slot extraction — async-обёртка над app.chat.intent_extractor."""
from __future__ import annotations

import asyncio
from typing import Any

from app.chat.intent_extractor import extract_intent_and_slots, extract_sku_from_message


async def extract_intent_and_slots_async(
    message: str, car_context: dict[str, Any], clarification_answers: list[str] | None = None
) -> dict[str, Any]:
    """Async-обёртка над sync extract_intent_and_slots."""
    if clarification_answers:
        combined = f"{message}\nОтветы на уточнения: {' | '.join(clarification_answers)}"
    else:
        combined = message
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract_intent_and_slots, combined, car_context)


__all__ = ["extract_intent_and_slots_async", "extract_sku_from_message"]
