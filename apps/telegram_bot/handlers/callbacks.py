"""Обработка inline-кнопок выбора тира и сценариев."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from core.price_search import NOT_IN_PRICELIST
from core.logger import log_event, log_event_to_db
from core.feedback_utils import anonymize_user_id, get_error_class

from ..menus import (
    SCENARIO_PROMPTS,
    show_main_menu,
    show_feedback_request,
    like_category_keyboard,
    dislike_reasons_keyboard,
    after_feedback_keyboard,
    after_dislike_keyboard,
    skip_comment_keyboard,
)
from ..states import PartsSearch
from storage.feedback_repository import save_feedback, update_dialogue_cycle, Feedback

router = Router()
logger = logging.getLogger(__name__)


def _safe_callback(handler):
    """Обёртка: перехват ошибок в callback, чтобы бот не падал."""
    async def wrapped(callback: CallbackQuery, state: FSMContext) -> None:
        try:
            await handler(callback, state)
        except Exception as e:
            logger.error("Ошибка в callback %s: %s", callback.data, e, exc_info=True)
            await callback.answer("Произошла ошибка. Попробуйте /reset", show_alert=True)

    return wrapped


@router.callback_query(F.data.startswith("scenario_"))
@_safe_callback
async def handle_scenario(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка выбора сценария из стартового меню."""
    scenario = callback.data.replace("scenario_", "") if callback.data else ""
    if scenario == "help":
        await callback.message.answer(
            "📋 <b>Примеры хороших запросов:</b>\n\n"
            "• Camry 50, передние колодки, аналоги\n"
            "• Kia Rio 2017 1.6, масляный фильтр\n"
            "• OEM 90915-YZZF2\n"
            "• Артикул BP02031\n"
            "• Lada Vesta 2021, полное ТО\n\n"
            "/start — меню\n/reset — сброс",
            parse_mode="HTML",
        )
        await show_main_menu(callback)
        await callback.answer()
        return
    prompt = SCENARIO_PROMPTS.get(scenario, SCENARIO_PROMPTS["free"])
    await state.update_data(scenario=scenario)
    await callback.message.answer(prompt, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("tier_"))
@_safe_callback
async def handle_tier(callback: CallbackQuery, state: FSMContext) -> None:
    tier = callback.data.replace("tier_", "") if callback.data else ""
    data = await state.get_data()
    tiers = data.get("last_tiers", {})
    items = tiers.get(tier, [])

    labels = {"economy": "🟢 Эконом", "optimal": "🟡 Оптимум", "oem": "🔵 OEM"}
    label = labels.get(tier, tier)

    user_id = callback.from_user.id if callback.from_user else 0
    log_event("option_selected", {"tg_user_id": user_id, "tier": tier})
    await log_event_to_db("option_selected", {"tg_user_id": user_id, "tier": tier})

    if not items:
        await callback.answer("Нет позиций в этом варианте", show_alert=True)
        return

    lines = [f"✅ Выбран: <b>{label}</b>\n"]
    for i, item in enumerate(items[:3], 1):
        brand = item.get("brand", "")
        art = item.get("article_raw") or item.get("article", "")
        desc = (item.get("description") or item.get("nomenclature") or "")[:60]
        price = f"{item.get('price', 0):,.0f} ₽".replace(",", " ") if item.get("price") else NOT_IN_PRICELIST
        delivery = f"{item.get('delivery_days')} дн." if item.get("delivery_days") is not None else NOT_IN_PRICELIST
        defect = " 🔸Некондиция" if item.get("is_defect") else ""
        lines.append(f"{i}. <b>{brand}</b> {art}{defect}\n   {desc}\n   💰 {price} | 🚚 {delivery}")

    lines.append("\nДля нового поиска — напишите запрос или /reset")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    cycle_id = data.get("cycle_id")
    if cycle_id:
        await update_dialogue_cycle(
            cycle_id,
            tier_selected=tier,
            final_status="success",
        )
    await state.update_data(cycle_attempt_count=0)
    await state.set_state(PartsSearch.idle)
    await show_main_menu(callback)
    await callback.answer()


@router.callback_query(F.data == "feedback_like")
@_safe_callback
async def handle_feedback_like(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь нажал 👍 — показать категории лайка."""
    data = await state.get_data()
    cycle_id = data.get("cycle_id")
    if not cycle_id:
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await state.set_state(PartsSearch.waiting_like_category)
    await callback.message.answer("Спасибо! Что именно понравилось?", reply_markup=like_category_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("like_cat_"))
@_safe_callback
async def handle_like_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор категории лайка → сохранить → предложить новый поиск."""
    cat = callback.data.replace("like_cat_", "") if callback.data else "ok"
    data = await state.get_data()
    cycle_id = data.get("cycle_id")
    user_id = callback.from_user.id if callback.from_user else 0
    tg_user_hash = anonymize_user_id(user_id)
    if cycle_id:
        fb = Feedback(cycle_id=cycle_id, tg_user_hash=tg_user_hash, rating="like", like_category=cat)
        await save_feedback(fb)
        await update_dialogue_cycle(cycle_id, final_status="success")
    await callback.message.answer("Отлично! Начать новый подбор?", reply_markup=after_feedback_keyboard())
    await state.set_state(PartsSearch.idle)
    await callback.answer()


@router.callback_query(F.data == "feedback_dislike")
@_safe_callback
async def handle_feedback_dislike(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь нажал 👎 — показать причины."""
    data = await state.get_data()
    cycle_id = data.get("cycle_id")
    if not cycle_id:
        await callback.answer("Сессия истекла", show_alert=True)
        return
    await state.set_state(PartsSearch.waiting_dislike_reason)
    await callback.message.answer("Жаль. Что пошло не так?", reply_markup=dislike_reasons_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("dislike_reason_"))
@_safe_callback
async def handle_dislike_reason(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор причины дизлайка → запросить комментарий или пропустить."""
    reason = callback.data.replace("dislike_reason_", "") if callback.data else "other"
    await state.update_data(dislike_reason=reason)
    await state.set_state(PartsSearch.waiting_dislike_comment)
    await callback.message.answer(
        "Напишите, что именно вы хотели получить?",
        reply_markup=skip_comment_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "dislike_skip")
@_safe_callback
async def handle_dislike_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропустить комментарий → сохранить feedback → предложить уточнить."""
    await _save_dislike_and_finish(callback, state, user_comment=None)


async def _save_dislike_and_finish(
    callback: CallbackQuery, state: FSMContext, user_comment: str | None = None
) -> None:
    """Сохранить дизлайк и показать кнопки после."""
    data = await state.get_data()
    cycle_id = data.get("cycle_id")
    reason = data.get("dislike_reason", "other")
    user_id = callback.from_user.id if callback.from_user else 0
    tg_user_hash = anonymize_user_id(user_id)
    error_class = get_error_class(reason)
    if cycle_id:
        fb = Feedback(
            cycle_id=cycle_id,
            tg_user_hash=tg_user_hash,
            rating="dislike",
            dislike_reason=reason,
            user_comment=user_comment,
            error_class=error_class,
        )
        await save_feedback(fb)
        await update_dialogue_cycle(cycle_id, final_status="failed")
    msg = callback.message
    await msg.answer("Понял. Хотите скорректировать подбор?", reply_markup=after_dislike_keyboard())
    await state.set_state(PartsSearch.idle)


@router.callback_query(F.data == "reset")
@_safe_callback
async def handle_reset(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("🔄 Сброс. Напишите новый запрос.")
    await show_main_menu(callback)
    await callback.answer()
