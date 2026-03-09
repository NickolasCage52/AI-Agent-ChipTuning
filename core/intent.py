"""Извлечение intent и слотов из запроса пользователя через LLM (Ollama)."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.pii_masker import mask_pii

logger = logging.getLogger(__name__)

FALLBACK_RESULT = {
    "intent": "parts_search",
    "part_query": "",
    "part_type": "",
    "article": None,
    "oem_number": None,
    "constraints": {},
    "car_context": {},
    "missing_critical": ["part_type"],
    "questions": [{"id": "q1", "text": "Что именно вам нужно? Укажите название детали или артикул."}],
    "summary": "Не удалось распознать запрос",
}


def _parse_llm_response(raw: str) -> dict[str, Any]:
    """Надёжный парсинг JSON из ответа LLM."""
    if not raw or not isinstance(raw, str):
        return {}
    text = raw.strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    logger.warning("Не удалось распарсить ответ LLM: %s", text[:200] if text else "(empty)")
    return {}

try:
    from llm import generate as llm_generate
except ImportError:
    from core.llm_adapter import call_llm as llm_generate

try:
    from llm.prompt_manager import get_prompt_manager
except ImportError:
    get_prompt_manager = None


async def extract_intent_and_slots(
    query: str,
    car_context: dict[str, Any] | None = None,
    clarification_answers: list[str] | None = None,
) -> dict[str, Any]:
    """Вызвать LLM (Ollama) для извлечения intent и слотов."""
    masked = mask_pii(query)
    context_str = ""
    if car_context:
        context_str = f"\nКонтекст авто: {car_context}"
    if clarification_answers:
        context_str += f"\nОтветы на уточнения: {clarification_answers}"

    full_query = f"Запрос пользователя: {masked}{context_str}"

    system_prompt = "Ты — эксперт по автозапчастям. Извлекаешь intent и слоты. Отвечай только JSON."
    if get_prompt_manager:
        system_prompt, _ = get_prompt_manager().get_active_prompt()

    try:
        raw = await llm_generate(prompt=full_query, system=system_prompt, timeout=45)
    except Exception as e:
        logger.warning("Ollama недоступна: %s. Используем rule-based fallback.", e)
        return _fallback_extract(query, car_context, clarification_answers)

    raw = str(raw).strip() if raw else ""
    result = _parse_llm_response(raw)
    if not result:
        result = dict(FALLBACK_RESULT)
        result["part_query"] = query
        result["car_context"] = car_context or {}
    if not isinstance(result.get("car_context"), dict):
        result["car_context"] = car_context or {}
    if not isinstance(result.get("questions"), list):
        result["questions"] = []

    # Мержим car из clarification_answers, если LLM не извлёк
    if clarification_answers and not result.get("car_context", {}).get("brand"):
        for ans in clarification_answers:
            parsed = _extract_car_from_text(ans)
            for k, v in parsed.items():
                if v and not result.get("car_context", {}).get(k):
                    result.setdefault("car_context", {})[k] = v
    # Дополнить questions из missing_critical, если LLM не задал вопросов
    if not result.get("questions") and result.get("missing_critical"):
        missing = result["missing_critical"]
        fallback_questions = []
        if "brand" in missing or "model" in missing or "year" in missing:
            fallback_questions.append(
                {"id": "q1", "text": "Для точного подбора укажите: марка, модель и год автомобиля?"}
            )
        if "part_type" in missing and len(fallback_questions) < 2:
            fallback_questions.append(
                {"id": "q2", "text": "Что именно нужно? Укажите название детали или артикул."}
            )
        if fallback_questions:
            result["questions"] = fallback_questions[:2]

    return result


def _extract_car_from_text(text: str) -> dict[str, str | None]:
    """Извлекает brand, model, year из текста: 'Kia Rio 2017', '1. Kia, Rio, 2017'."""
    if not text or not text.strip():
        return {}
    t = re.sub(r"^\d+\.\s*", "", text.strip())
    t = re.sub(r",\s*", " ", t)
    car: dict[str, str | None] = {}
    year_m = re.search(r"\b(19|20)\d{2}\b", t)
    if year_m:
        car["year"] = year_m.group(0)
    brands = (
        "kia toyota hyundai honda nissan mazda ford vw volkswagen bmw mercedes audi skoda "
        "renault chevrolet mitsubishi suzuki lexus infiniti opel peugeot citroen fiat lada daewoo"
    ).split()
    # Regex "Brand Model Year" — надёжнее для "Kia Rio 2017"
    brand_model_year = re.search(
        r"([a-zа-яё]+)\s+([a-zа-яё0-9]+)\s+(19|20)\d{2}\b",
        t,
        re.IGNORECASE,
    )
    if brand_model_year:
        b, m = brand_model_year.group(1), brand_model_year.group(2)
        if b.lower() in brands:
            car["brand"] = b
            car["model"] = m
    if not car.get("brand"):
        words = t.split()
        for i, w in enumerate(words):
            wl = w.lower()
            if wl in brands:
                car["brand"] = w
                if i + 1 < len(words) and not re.match(r"^\d{4}$", words[i + 1]):
                    car["model"] = words[i + 1]
                break
    return car


def _fallback_extract(
    query: str,
    car_context: dict | None,
    clarification_answers: list[str] | None = None,
) -> dict[str, Any]:
    """Rule-based извлечение при недоступности LLM."""
    q = (query or "").lower().strip()
    car = dict(car_context or {})
    # Извлекаем авто из запроса и ответов на уточнения
    for src in [query] + (clarification_answers or []):
        parsed = _extract_car_from_text(src)
        for k, v in parsed.items():
            if v and not car.get(k):
                car[k] = v
    sku = extract_sku_from_message(query or "")
    # general_question — приветствия, вопросы про бота, общие вопросы про авто
    general_triggers = [
        "привет", "здравствуй", "хай", "салют", "спасибо", "благодарю",
        "как ты", "что умеешь", "что можешь", "ии работа", "бот работа",
        "как работаешь", "помощь", "помоги", "подскажи",
        "как часто", "что такое грм", "что такое дроссель", "что такое",
    ]
    q_lower = (query or "").lower().strip()
    # Короткие общие вопросы без артикула — general_question
    parts_search_patterns = ["колодк", "фильтр", "свеч", "стойк", "артикул", "oem"]
    looks_like_parts_search = any(p in q_lower for p in parts_search_patterns) and any(
        c in q_lower for c in ["camry", "rio", "kia", "toyota", "веста", "для", "на ", "подбор"]
    )
    if any(t in q_lower for t in general_triggers) and not sku and len(q_lower) < 80 and not looks_like_parts_search:
        return {
            "intent": "general_question",
            "part_query": query,
            "part_type": "",
            "article": None,
            "oem_number": None,
            "car_context": car or {},
            "missing_critical": [],
            "questions": [],
            "summary": "Общий вопрос",
        }
    result: dict[str, Any] = {
        "intent": "parts_search",
        "part_query": query,
        "part_type": q[:100] if q else "запчасть",
        "article": sku if sku else None,
        "oem_number": sku if sku and any(c in q for c in ["oem", "оригинал", "oe"]) else None,
        "car_context": car,
        "missing_critical": [],
        "questions": [],
        "summary": f"Ищу: {query[:50]}" if query else "Уточните запрос",
    }
    synonyms = {
        "колодк": "тормозные колодки",
        "тормоз": "тормозные колодки",
        "тормоза": "тормозные колодки",
        "фильтр масл": "масляный фильтр",
        "масляник": "масляный фильтр",
        "масляный фильтр": "масляный фильтр",
        "масл": "масляный фильтр",
        "фильтр воздуш": "воздушный фильтр",
        "грм": "комплект ГРМ",
        "свеч": "свечи зажигания",
        "ходовк": "подвеска",
        "ходовая": "подвеска",
        "расходник": "расходные материалы",
    }
    for k, v in synonyms.items():
        if k in q:
            result["part_type"] = v
            result["part_query"] = v  # для поиска в прайсе
            break
    if not car.get("brand") and not car.get("model") and not sku:
        result["missing_critical"] = ["brand", "model"]
        result["questions"] = [
            {"id": "q1", "text": "Для точного подбора укажите: марка, модель и год автомобиля?"},
        ]
    # Есть авто, но не указана деталь — спросить
    part_synonyms = ["колодк", "тормоз", "фильтр", "свеч", "грм", "масл", "диск", "стойк", "аморт"]
    has_part = any(p in q for p in part_synonyms) or sku
    if car.get("brand") and not has_part:
        result["missing_critical"] = list(result.get("missing_critical", [])) + ["part_type"]
        if not result.get("questions"):
            result["questions"] = [
                {"id": "q1", "text": "Что именно нужно? Укажите название детали (например: колодки, фильтр)."},
            ]
    return result


def extract_sku_from_message(message: str) -> str | None:
    """Извлекает артикул/OEM из сообщения."""
    m = re.search(
        r"\b([A-Z0-9]{4,}[-][A-Z0-9]+|[0-9]{4,}[-][0-9]+|[A-Z0-9]{5,})\b",
        message,
        re.IGNORECASE,
    )
    return m.group(0) if m else None
