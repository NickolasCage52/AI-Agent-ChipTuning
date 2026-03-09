"""Обработка текстовых сообщений (поиск только по прайсам)."""
from __future__ import annotations

import json
import logging
import uuid

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from core.intent import extract_intent_and_slots, extract_sku_from_message
from core.price_search import build_tiers, search
from core.feedback_utils import anonymize_user_id, get_error_class

GENERAL_QUESTION_SYSTEM = (
    "Ты — опытный автомеханик и эксперт по запчастям. Отвечаешь кратко и по делу на русском языке. "
    "Если вопрос про подбор запчастей — предложи воспользоваться поиском по прайсу. "
    "Не выдумывай цены и наличие — их ты не знаешь."
)
from core.pii_masker import mask_pii
from core.logger import log_event, log_event_to_db

from ..formatter import format_clarification, format_no_results, format_results
from ..menus import results_keyboard, show_main_menu, show_feedback_request
from ..states import PartsSearch
from storage.feedback_repository import (
    DialogueCycle,
    save_dialogue_cycle,
    update_dialogue_cycle,
)

router = Router()
logger = logging.getLogger(__name__)


def _normalize_questions(questions: list) -> list[str]:
    """Нормализация questions: dict {text} или строка."""
    if not questions:
        return []
    result = []
    for q in questions:
        if isinstance(q, dict):
            result.append(q.get("text") or q.get("question") or str(q))
        elif isinstance(q, str):
            result.append(q)
        else:
            result.append(str(q))
    return result


@router.message(F.text)
async def handle_message(message: Message, state: FSMContext) -> None:
    try:
        await _handle_message_impl(message, state)
    except Exception as e:
        logger.error("Необработанная ошибка в handle_message: %s", e, exc_info=True)
        await message.answer(
            "⚠️ Произошла ошибка при обработке запроса. Попробуйте ещё раз или напишите /reset"
        )


async def _handle_message_impl(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id if message.from_user else 0
    raw_text = (message.text or "").strip()
    if not raw_text:
        return

    current_state = await state.get_state()
    data = await state.get_data()

    if current_state and "waiting_dislike_comment" in str(current_state):
        from storage.feedback_repository import save_feedback, Feedback
        from ..menus import after_dislike_keyboard
        cycle_id = data.get("cycle_id")
        reason = data.get("dislike_reason", "other")
        tg_user_hash = anonymize_user_id(user_id)
        error_class = get_error_class(reason)
        if cycle_id:
            fb = Feedback(
                cycle_id=cycle_id,
                tg_user_hash=tg_user_hash,
                rating="dislike",
                dislike_reason=reason,
                user_comment=raw_text[:500],
                error_class=error_class,
            )
            await save_feedback(fb)
            await update_dialogue_cycle(cycle_id, final_status="failed")
        await message.answer("Понял. Хотите скорректировать подбор?", reply_markup=after_dislike_keyboard())
        await state.set_state(PartsSearch.idle)
        return

    masked_text = mask_pii(raw_text)

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

    # general_question — ответ через LLM как эксперта-автомеханика
    if result.get("intent") == "general_question":
        try:
            try:
                from llm import generate as llm_generate
            except ImportError:
                from core.llm_adapter import call_llm as llm_generate
            reply = await llm_generate(
                prompt=masked_text,
                system=GENERAL_QUESTION_SYSTEM,
                timeout=25,
            )
            await message.answer(reply.strip() or "Не удалось сформировать ответ.")
        except Exception as e:
            logger.warning("LLM for general_question failed: %s", e)
            await message.answer(
                "Извините, не удалось обработать вопрос. Попробуйте переформулировать или воспользуйтесь поиском по артикулу."
            )
        await show_main_menu(message)
        return

    part_type = result.get("part_type") or result.get("part_query") or original_query
    questions_raw = result.get("questions") or []
    questions = _normalize_questions(questions_raw) if questions_raw else []
    questions_for_display = [{"text": q} for q in questions] if questions else []
    clarification_count = data.get("clarification_count", 0)
    cycle_id = data.get("cycle_id")

    if questions and clarification_count < 2:
        if not cycle_id:
            cycle_id = str(uuid.uuid4())
            session_id = str(message.chat.id)
            tg_user_hash = anonymize_user_id(user_id)
            cycle = DialogueCycle(
                id=cycle_id,
                session_id=session_id,
                tg_user_hash=tg_user_hash,
                intent=result.get("intent"),
                slots_json=json.dumps(result, ensure_ascii=False),
                all_messages_json=json.dumps([raw_text], ensure_ascii=False),
            )
            await save_dialogue_cycle(cycle)
        await state.update_data(
            clarification_count=clarification_count + 1,
            pending_questions=questions_for_display,
            last_result=result,
            cycle_id=cycle_id,
        )
        await state.set_state(PartsSearch.waiting_clarification)
        log_event("clarification_asked", {"tg_user_id": user_id, "questions": questions})
        summary = result.get("summary", "") or f"Подбираю {part_type}."
        await message.answer(format_clarification(summary, questions_for_display), parse_mode="HTML")
        return

    if not cycle_id:
        cycle_id = str(uuid.uuid4())
        session_id = str(message.chat.id)
        tg_user_hash = anonymize_user_id(user_id)
        cycle = DialogueCycle(
            id=cycle_id,
            session_id=session_id,
            tg_user_hash=tg_user_hash,
            intent=result.get("intent"),
            slots_json=json.dumps(result, ensure_ascii=False),
            all_messages_json=json.dumps(
                (data.get("clarification_answers") or []) + [raw_text],
                ensure_ascii=False,
            ),
        )
        await save_dialogue_cycle(cycle)
        await state.update_data(cycle_id=cycle_id)

    await message.bot.send_chat_action(message.chat.id, "typing")

    # Приоритет: нормализованный part_type, иначе part_query. Для ТО — из maintenance_logic.
    search_query = result.get("part_type") or result.get("part_query") or masked_text
    if result.get("intent") == "maintenance_parts":
        from core.maintenance_logic import build_maintenance_search_queries
        maintenance_parts = build_maintenance_search_queries("full", car_context)
        if maintenance_parts:
            first_term = maintenance_parts[0].get("search_terms", ["масляный фильтр"])[0]
            if not search_query or search_query in ("полное то", "расходники", "то", "обслуживание"):
                search_query = first_term
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
        await show_main_menu(message)
        return

    tiers = build_tiers(items)

    attempt_count = data.get("cycle_attempt_count", 0) + 1
    prompt_version = "1.0.0"
    try:
        from llm.prompt_manager import get_prompt_manager
        _, prompt_version = get_prompt_manager().get_active_prompt()
    except Exception:
        pass
    llm_model = "ollama"
    try:
        from llm import health_check
        h = await health_check()
        llm_model = "ollama" if h.get("available") else "fallback"
    except Exception:
        llm_model = "llm"

    tiers_dict = {
        "economy": [i.to_dict() for i in tiers["economy"]],
        "optimal": [i.to_dict() for i in tiers["optimal"]],
        "oem": [i.to_dict() for i in tiers["oem"]],
    }
    all_messages = (data.get("clarification_answers") or []) + [raw_text]
    all_bot_responses = data.get("cycle_bot_responses") or []

    await update_dialogue_cycle(
        cycle_id,
        attempt_count=attempt_count,
        intent=result.get("intent"),
        slots_json=json.dumps(result, ensure_ascii=False),
        all_messages_json=json.dumps(all_messages, ensure_ascii=False),
        tiers_shown_json=json.dumps(tiers_dict, ensure_ascii=False),
        llm_model=llm_model,
        prompt_version=prompt_version,
    )

    summary = result.get("summary", "") or f"Нашёл варианты {part_type}."
    safety_note = ""
    if not car_context.get("vin"):
        safety_note = "Применимость — по марке/модели. Для 100% точности укажите VIN."

    single_item = len(items) == 1
    response_text = format_results(
        summary=summary,
        part_type=part_type,
        tiers=tiers,
        safety_note=safety_note,
        single_item=single_item,
    )

    await state.update_data(
        car_context=car_context,
        last_tiers=tiers_dict,
        last_part_type=part_type,
        clarification_count=0,
        clarification_answers=[],
        cycle_attempt_count=attempt_count,
    )
    await state.set_state(PartsSearch.showing_results)

    log_event(
        "offers_shown",
        {"tg_user_id": user_id, "tiers_count": sum(len(v) for v in tiers.values()), "part_type": part_type},
    )
    await log_event_to_db("offers_shown", {"tg_user_id": user_id, "intent": result.get("intent")})

    await message.answer(response_text, parse_mode="HTML", reply_markup=results_keyboard())
    await state.set_state(PartsSearch.waiting_feedback)
    await show_feedback_request(message)
