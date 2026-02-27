"""Обработчики команд /start, /help, /reset."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👋 Привет! Я помогу подобрать запчасти для вашего автомобиля.\n\n"
        "Просто напишите что нужно, например:\n"
        "• <i>Нужны колодки на Toyota Camry 2016</i>\n"
        "• <i>Масляный фильтр Kia Rio 2017</i>\n"
        "• <i>Комплект ГРМ, нужны аналоги</i>\n\n"
        "Я уточню детали и подберу варианты по цене.",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📋 <b>Как пользоваться:</b>\n\n"
        "1. Напишите запрос: что нужно + марка/модель/год авто\n"
        "2. Отвечайте на уточняющие вопросы (их будет не больше 2)\n"
        "3. Выберите вариант: Эконом / Оптимум / OEM\n\n"
        "<b>Команды:</b>\n"
        "/start — начать заново\n"
        "/reset — сбросить контекст авто\n"
        "/help — эта справка",
        parse_mode="HTML",
    )


@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🔄 Контекст сброшен. Начните новый поиск — напишите запрос.")
