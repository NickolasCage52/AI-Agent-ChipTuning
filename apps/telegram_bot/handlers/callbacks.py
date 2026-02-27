"""Обработка inline-кнопок выбора тира."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from core.logger import log_event, log_event_to_db

from ..states import PartsSearch

router = Router()

TIER_LABELS = {
    "select_economy": ("economy", "🟢 Эконом"),
    "select_optimal": ("optimal", "🟡 Оптимум"),
    "select_oem": ("oem", "🔵 OEM"),
}


@router.callback_query(F.data.in_(list(TIER_LABELS.keys())))
async def handle_tier_selection(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None:
        return
    tier_key, tier_label = TIER_LABELS[callback.data]
    data = await state.get_data()
    tiers = data.get("last_tiers", {})
    selected = tiers.get(tier_key, [])

    user_id = callback.from_user.id if callback.from_user else 0
    log_event("option_selected", {
        "tg_user_id": user_id,
        "tier": tier_key,
        "items": [i.get("sku") for i in selected if i.get("sku")],
    })
    await log_event_to_db("option_selected", {
        "tg_user_id": user_id,
        "tier": tier_key,
    })

    if not selected:
        await callback.answer("Нет данных по этому варианту", show_alert=True)
        return

    items_text = "\n".join([
        f"• <b>{i.get('display_name') or i.get('name', '?')}</b> — {i.get('price', '?')} ₽"
        f" | {i.get('brand', '')} | срок: {i.get('delivery_days', '?')} дн."
        for i in selected
    ])

    await callback.message.answer(
        f"✅ Выбран вариант: <b>{tier_label}</b>\n\n"
        f"{items_text}\n\n"
        "Для нового поиска — просто напишите запрос или /reset",
        parse_mode="HTML",
    )
    await state.set_state(PartsSearch.idle)
    await callback.answer()


@router.callback_query(F.data == "reset")
async def handle_reset_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("🔄 Сброс. Напишите новый запрос.")
    await callback.answer()
