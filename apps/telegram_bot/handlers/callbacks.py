"""Обработка inline-кнопок выбора тира."""
from __future__ import annotations

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from core.logger import log_event, log_event_to_db

from ..states import PartsSearch

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("tier_"))
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
        price = f"{item.get('price', 0):,.0f} ₽".replace(",", " ") if item.get("price") else "уточнить"
        delivery = f"{item.get('delivery_days', '?')} дн."
        defect = " 🔸Некондиция" if item.get("is_defect") else ""
        lines.append(f"{i}. <b>{brand}</b> {art}{defect}\n   {desc}\n   💰 {price} | 🚚 {delivery}")

    lines.append("\nДля нового поиска — напишите запрос или /reset")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await state.set_state(PartsSearch.idle)
    await callback.answer()


@router.callback_query(F.data == "reset")
async def handle_reset(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("🔄 Сброс. Напишите новый запрос.")
    await callback.answer()
