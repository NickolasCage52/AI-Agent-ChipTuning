"""Обработка текстовых сообщений."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.db.session import AsyncSessionLocal
from core.intent import extract_intent_and_slots_async, extract_sku_from_message
from core.search import search_parts, search_by_sku_oem
from core.ranker import build_tiers
from core.pii_masker import mask_pii
from core.logger import log_event, log_event_to_db

from ..states import PartsSearch
from ..formatter import format_results, format_clarification

router = Router()
logger = logging.getLogger(__name__)


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

    log_event("query_created", {
        "tg_user_id": user_id,
        "query": masked_text,
        "state": current_state,
    })
    await log_event_to_db("query_created", {"tg_user_id": user_id, "query": masked_text})

    # Если ожидаем ответ на уточнение
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
        result = await extract_intent_and_slots_async(
            original_query,
            car_context,
            clarification_answers=clarification_answers if clarification_answers else None,
        )
    except Exception as e:
        logger.exception("Intent extraction failed: %s", e)
        await message.answer(
            "⚠️ Не удалось обработать запрос. Попробуйте переформулировать или напишите /reset"
        )
        return

    # Обновить car_context из ответа Gemini
    if result.get("car_context"):
        for k, v in result["car_context"].items():
            if v:
                car_context[k] = v
        await state.update_data(car_context=car_context)

    part_type = result.get("part_type") or original_query
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
        clarification_text = format_clarification(summary, questions)
        await message.answer(clarification_text, parse_mode="HTML")
        return

    # Достаточно данных — поиск
    await message.bot.send_chat_action(message.chat.id, "typing")

    sku = extract_sku_from_message(raw_text)
    async with AsyncSessionLocal() as db:
        try:
            if sku:
                search_results = await search_by_sku_oem(sku, db, limit=20)
            else:
                search_results = await search_parts(part_type, car_context, db, limit=50)
        except Exception as e:
            logger.exception("Search failed: %s", e)
            await message.answer(
                "🔍 Не удалось найти варианты по вашему запросу.\n"
                "Попробуйте уточнить марку/модель/год или напишите артикул детали."
            )
            await log_event_to_db("no_results", {"tg_user_id": user_id, "reason": str(e)})
            return

    if not search_results:
        await message.answer(
            f"😔 По запросу <i>{part_type}</i> ничего не найдено.\n\n"
            "Попробуйте:\n"
            "• Уточнить тип детали\n"
            "• Указать артикул или OEM-номер\n"
            "• Написать /reset и начать заново",
            parse_mode="HTML",
        )
        await log_event_to_db("no_results", {"tg_user_id": user_id, "reason": "empty_results"})
        return

    tiers = build_tiers(
        search_results,
        car_brand=car_context.get("brand"),
        car_model=car_context.get("model"),
    )

    summary = result.get("summary", "") or f"Нашёл варианты {part_type}."
    safety_notes: list[str] = []
    if not car_context.get("vin"):
        safety_notes.append("Применимость подтверждена по марке/модели/году. Для 100% точности укажите VIN.")

    response_text = format_results(
        summary=summary,
        part_type=part_type,
        car_context=car_context,
        tiers=tiers,
        safety_notes=safety_notes,
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Эконом", callback_data="select_economy"),
                InlineKeyboardButton(text="🟡 Оптимум", callback_data="select_optimal"),
                InlineKeyboardButton(text="🔵 OEM", callback_data="select_oem"),
            ],
            [
                InlineKeyboardButton(text="🔄 Новый поиск", callback_data="reset"),
            ],
        ]
    )

    await state.update_data(
        last_tiers=tiers,
        last_part_type=part_type,
        clarification_count=0,
        clarification_answers=[],
    )
    await state.set_state(PartsSearch.showing_results)

    log_event("offers_shown", {
        "tg_user_id": user_id,
        "tiers_count": sum(len(v) for v in tiers.values()),
        "part_type": part_type,
    })
    await log_event_to_db("offers_shown", {
        "tg_user_id": user_id,
        "results": tiers,
        "intent": result.get("intent"),
    })

    await message.answer(response_text, parse_mode="HTML", reply_markup=keyboard)
