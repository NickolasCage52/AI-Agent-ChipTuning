"""Обработчики команд /start, /help, /reset, /debug."""
from __future__ import annotations

import os
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from ..menus import START_MESSAGE, show_main_menu

router = Router()
ADMIN_TG_ID = os.getenv("ADMIN_TG_ID", "")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(START_MESSAGE, parse_mode="HTML")
    await show_main_menu(message)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📋 <b>Примеры хороших запросов:</b>\n\n"
        "• <i>Camry 50, передние колодки, аналоги</i>\n"
        "• <i>Kia Rio 2017 1.6, масляный фильтр</i>\n"
        "• <i>OEM 90915-YZZF2</i>\n"
        "• <i>Артикул BP02031</i>\n"
        "• <i>Lada Vesta 2021, полное ТО</i>\n"
        "• <i>VIN XTA21099082163141, нужны расходники</i>\n"
        "• <i>Солярис 2019, комплект расходников на ТО</i>\n\n"
        "<b>Команды:</b>\n"
        "/start — начать заново\n"
        "/reset — сбросить контекст\n"
        "/help — эта справка",
        parse_mode="HTML",
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🔄 Контекст сброшен. Начните новый поиск — напишите запрос.")
    await show_main_menu(message)


@router.message(Command("debug"))
async def cmd_debug(message: Message) -> None:
    """Диагностика системы (только для ADMIN_TG_ID)."""
    if ADMIN_TG_ID and str(message.from_user.id if message.from_user else "") != ADMIN_TG_ID:
        await message.answer("⛔ Команда недоступна.")
        return

    lines = ["🔧 <b>ДИАГНОСТИКА СИСТЕМЫ</b>\n"]

    # LLM
    try:
        from llm import health_check
        h = await health_check()
        if h.get("available") and (h.get("model_loaded") or h.get("model_available")):
            lines.append(f"✅ Ollama: доступна ({h.get('configured_model', '?')})")
        else:
            lines.append(f"⚠️ Ollama: {h.get('error', 'модель не загружена')}")
    except Exception as e:
        lines.append(f"❌ Ollama: {e}")

    # Прайс
    import sqlite3
    db_path = os.getenv("DB_PATH", "data/parts.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        for tbl in ["products", "products_defect"]:
            try:
                total = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                no_price = conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE price IS NULL OR price = 0").fetchone()[0]
                pct = (no_price / total * 100) if total else 0
                status = "⚠️" if pct > 5 else "✅"
                lines.append(f"{status} {tbl}: {total} строк, без цены: {no_price} ({pct:.1f}%)")
            except Exception as e:
                lines.append(f"❌ {tbl}: {e}")
        conn.close()
    else:
        lines.append("❌ БД не найдена")

    await message.answer("\n".join(lines), parse_mode="HTML")
