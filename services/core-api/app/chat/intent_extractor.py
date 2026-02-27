from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from app.llm.gemini_adapter import call_gemini

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Ты — ИИ-ассистент автосервиса. Анализируй запрос и возвращай ТОЛЬКО валидный JSON без markdown-блоков.

JSON-схема:
{
  "intent": "parts_search | maintenance_parts | symptom_to_parts",
  "part_type": "нормализованное название детали или null",
  "side_axle": "front|rear|left|right|null",
  "brand_preference": "oem|analog|any",
  "constraints": {"max_price": null, "max_delivery_days": null, "in_stock": true},
  "missing_fields": ["список недостающих слотов"],
  "questions": [
    {"id": "q1", "text": "Конкретный вопрос клиенту?", "expected_type": "string"}
  ],
  "confidence": 0.0-1.0,
  "vehicle": {"brand": "", "model": "", "year": null},
  "summary": "краткое понимание запроса в 1 предложении"
}

Если в сообщении указаны марка/модель/год авто — заполни vehicle. summary — для отображения пользователю.

КРИТИЧНО: questions — КОНКРЕТНЫЕ вопросы (макс 2). НЕ пиши "уточните детали". Пиши точно: "Укажите марку и модель автомобиля?", "Какой год выпуска?", "Передние или задние колодки нужны?".
Если нет brand/model/year в контексте авто — задай вопрос "Укажите марку, модель и год автомобиля?".
part_type: "колодки" → "тормозные колодки", "фильтр" → "масляный фильтр".
"""

SYNONYMS: dict[str, str] = {
    "колодки": "тормозные колодки",
    "тормоза": "тормозные колодки",
    "фильтр": "масляный фильтр",
    "масло": "моторное масло",
    "грм": "комплект ГРМ",
    "ремень": "ремень ГРМ",
    "свечи": "свечи зажигания",
    "амортизатор": "амортизатор",
    "стойка": "стойка амортизатора",
    "масляный фильтр": "масляный фильтр",
    "air filter": "воздушный фильтр",
    "oil filter": "масляный фильтр",
    "brake pad": "тормозные колодки",
}


def normalize_part_type(text: str) -> str:
    if not text:
        return ""
    text_lower = text.lower().strip()
    for key, value in SYNONYMS.items():
        if key in text_lower:
            return value
    return text.strip()


def _questions_from_missing(missing: list[str]) -> list[dict[str, str]]:
    """Сформировать конкретные вопросы по списку недостающих слотов."""
    qs: list[dict[str, str]] = []
    if "brand" in missing or "model" in missing:
        qs.append({"id": "q1", "text": "Укажите марку и модель автомобиля?", "expected_type": "string"})
    if "year" in missing and len(qs) < 2:
        qs.append({"id": "q2", "text": "Какой год выпуска?", "expected_type": "string"})
    if "mileage" in missing and len(qs) < 2:
        qs.append({"id": "q3", "text": "Какой пробег (примерно)?", "expected_type": "string"})
    if "part_type" in missing and len(qs) < 2:
        qs.append({"id": "q4", "text": "Какую именно запчасть нужно подобрать?", "expected_type": "string"})
    return qs[:2]


def _fallback_extract(message: str, car_context: dict[str, Any]) -> dict[str, Any]:
    """Rule-based fallback когда Gemini недоступен."""
    m = message.lower()
    intent = "parts_search"
    if any(x in m for x in ["то", "техобслуж", "масло", "oil"]):
        intent = "maintenance_parts"
    elif any(x in m for x in ["стук", "скрип", "шум", "вибра"]):
        intent = "symptom_to_parts"

    part_type = normalize_part_type(message)
    if not part_type and intent == "maintenance_parts":
        part_type = "масляный фильтр"
    if not part_type:
        part_type = message[:80] or "запчасть"
    missing = []
    if not car_context.get("brand"):
        missing.append("brand")
    if not car_context.get("model"):
        missing.append("model")
    if not car_context.get("year"):
        missing.append("year")

    questions = []
    if "brand" in missing or "model" in missing:
        questions.append({"id": "q1", "text": "Подскажите марку и модель авто?", "expected_type": "string"})
    if "year" in missing and len(questions) < 2:
        questions.append({"id": "q2", "text": "Какой год выпуска?", "expected_type": "string"})
    if not part_type and len(questions) < 2:
        questions.append({"id": "q3", "text": "Какую запчасть нужно подобрать?", "expected_type": "string"})
    questions = questions[:2]

    return {
        "intent": intent,
        "part_type": part_type,
        "questions": questions,
        "missing_fields": missing,
        "confidence": 0.5,
    }


def extract_intent_and_slots(message: str, car_context: dict[str, Any]) -> dict[str, Any]:
    if not os.environ.get("GEMINI_API_KEY"):
        return _fallback_extract(message, car_context)

    car_str = (
        f"Авто: {car_context.get('brand', '')} {car_context.get('model', '')} "
        f"{car_context.get('year', '') or ''} {car_context.get('engine', '') or ''}"
    ).strip()
    prompt = f"{car_str}\nЗапрос: {message}"

    raw = ""
    try:
        raw = call_gemini(prompt, system=SYSTEM_PROMPT)
        raw = raw.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
        raw = raw.strip()
        result = json.loads(raw)
    except Exception as e:
        logger.warning("Gemini parse failed: %s | raw[:200]=%s", e, raw[:200] if raw else "")
        result = _fallback_extract(message, car_context)

    # Если Gemini вернул missing_fields но пустые questions — дополняем
    if result.get("missing_fields") and not result.get("questions"):
        result["questions"] = _questions_from_missing(result["missing_fields"])

    if result.get("part_type"):
        result["part_type"] = normalize_part_type(str(result["part_type"])) or result["part_type"]

    if result.get("questions"):
        result["questions"] = result["questions"][:2]

    # Слить vehicle в car_context
    vehicle = result.get("vehicle") or {}
    if isinstance(vehicle, dict):
        result["car_context"] = {k: v for k, v in vehicle.items() if v}

    return result


def extract_sku_from_message(message: str) -> str | None:
    """Извлекает артикул/OEM из сообщения."""
    match = re.search(
        r"\b([A-Z0-9]{5,}[-][A-Z0-9]+|[0-9]{5,}[-][0-9]+)\b",
        message,
        re.IGNORECASE,
    )
    return match.group(0) if match else None
