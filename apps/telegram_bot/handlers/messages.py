"""Обработка текстовых сообщений (поиск только по прайсам)."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext

from core.intent import extract_intent_and_slots, extract_sku_from_message
from core.price_search import build_tiers, search
from core.pii_masker import mask_pii
from core.logger import log_event, log_event_to_db

from ..formatter import format_clarification, format_no_results, format_results
from ..states import PartsSearch

router = Router()
logger = logging.getLogger(__name__)


def _results_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Эконом", callback_data="tier_economy"),
                InlineKeyboardButton(text="🟡 Оптимум", callback_data="tier_optimal"),
                InlineKeyboardButton(text="🔵 OEM", callback_data="tier_oem"),
            ],
            [InlineKeyboardButton(text="🔄 Новый поиск", callback_data="reset")],
        ]
    )


@router.message(F.text)
async def handle_message(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id if message.from_user else 0
    raw_text = (message.text or "").strip()
    if not raw_text:
        return

    masked_text = mask_pii(raw_text)
    current_state = await state.get_state()
    data = await state.get_data()

    await message.bot.send_chat_action(message.chat.id, "typing")

    log_event("query_created", {"tg_user_id": user_id, "query": masked_text, "state": current_state})
    await log_event_to_db("query_created", {"tg_user_id": user_id, "query": masked_text})

    clarification_answers = data.get("clarification_answers", [])
    original_query = data.get("original_query", raw_text)
    is_waiting_clarification = current_state and "waiting_clarification" in str(current_state)

    if is_waiting_clarification:
        clarification_answers = list(clarification_answers) + [raw_text]
        await state.update_data(clarification_answers=clarification_answers)
    else:
        original_query = raw_text
        await state.update_data(original_query=original_query)

    car_context = dict(data.get("car_context") or {})

    try:
        result = await extract_intent_and_slots(
            query=masked_text,
            car_context=car_context,
            clarification_answers=clarification_answers if clarification_answers else None,
        )
    except Exception as e:
        logger.exception("Intent extraction failed: %s", e)
        await message.answer(
            "⚠️ Не удалось обработать запрос. Попробуйте переформулировать или напишите /reset"
        )
        return

    if result.get("car_context"):
        for k, v in result["car_context"].items():
            if v:
                car_context[k] = v
        await state.update_data(car_context=car_context)

    part_type = result.get("part_type") or result.get("part_query") or original_query
    questions = result.get("questions") or []
    clarification_count = data.get("clarification_count", 0)

    if questions and clarification_count < 2:
        await state.update_data(
            clarification_count=clarification_count + 1,
            pending_questions=questions,
            last_result=result,
        )
        await state.set_state(PartsSearch.waiting_clarification)
        log_event("clarification_asked", {"tg_user_id": user_id, "questions": [q.get("text") for q in questions]})
        summary = result.get("summary", "") or f"Подбираю {part_type}."
        await message.answer(format_clarification(summary, questions), parse_mode="HTML")
        return

    await message.bot.send_chat_action(message.chat.id, "typing")

    # Приоритет: нормализованный part_type (колодки/тормоза → тормозные колодки), иначе part_query
    search_query = result.get("part_type") or result.get("part_query") or masked_text
    article = result.get("article") or ""
    oem = result.get("oem_number") or ""
    brand_pref = result.get("brand_pref")
    brand = "" if brand_pref in ("oem", "analog", None) else str(brand_pref or "")

    sku = extract_sku_from_message(raw_text)
    if sku:
        article = sku
        oem = sku

    try:
        items = search(
            query=search_query,
            article=article,
            oem=oem,
            brand=brand,
            max_results=50,
        )
    except Exception as e:
        logger.exception("Search failed: %s", e)
        await message.answer(
            "🔍 Ошибка поиска. Попробуйте позже или напишите /reset"
        )
        await log_event_to_db("no_results", {"tg_user_id": user_id, "reason": str(e)})
        return

    if not items:
        await message.answer(
            format_no_results(part_type or search_query),
            parse_mode="HTML",
        )
        await log_event_to_db("no_results", {"tg_user_id": user_id, "reason": "empty_results"})
        await state.clear()
        return

    tiers = build_tiers(items)

    summary = result.get("summary", "") or f"Нашёл варианты {part_type}."
    safety_note = ""
    if not car_context.get("vin"):
        safety_note = "Применимость — по марке/модели. Для 100% точности укажите VIN."

    response_text = format_results(
        summary=summary,
        part_type=part_type,
        tiers=tiers,
        safety_note=safety_note,
    )

    await state.update_data(
        car_context=car_context,
        last_tiers={
            "economy": [i.to_dict() for i in tiers["economy"]],
            "optimal": [i.to_dict() for i in tiers["optimal"]],
            "oem": [i.to_dict() for i in tiers["oem"]],
        },
        last_part_type=part_type,
        clarification_count=0,
        clarification_answers=[],
    )
    await state.set_state(PartsSearch.showing_results)

    log_event(
        "offers_shown",
        {"tg_user_id": user_id, "tiers_count": sum(len(v) for v in tiers.values()), "part_type": part_type},
    )
    await log_event_to_db("offers_shown", {"tg_user_id": user_id, "intent": result.get("intent")})

    await message.answer(response_text, parse_mode="HTML", reply_markup=_results_keyboard())
