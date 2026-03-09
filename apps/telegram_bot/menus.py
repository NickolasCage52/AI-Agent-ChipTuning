"""Стартовое меню и шаблоны кнопок."""
from __future__ import annotations

from typing import Union

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

MAIN_MENU_TEXT = "Чем могу помочь?"

DISLIKE_REASONS = [
    ("❌ Неправильно понял запрос", "wrong_understanding"),
    ("🔧 Не те запчасти", "wrong_parts"),
    ("🚗 Не учёл марку/модель/год", "wrong_car"),
    ("🔑 Не учёл VIN/двигатель", "wrong_vin_engine"),
    ("❓ Плохие уточняющие вопросы", "bad_questions"),
    ("💰 Нет цены", "no_price"),
    ("📦 Нет срока", "no_delivery"),
    ("👎 Плохой ответ в целом", "bad_answer"),
    ("💬 Другое", "other"),
]

LIKE_CATEGORIES = [
    ("✅ Ответ полезный", "useful"),
    ("🎯 Подбор точный", "accurate"),
    ("👌 Всё ок", "ok"),
]


def start_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура стартового меню со сценариями."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔧 Полное ТО", callback_data="scenario_maintenance"),
                InlineKeyboardButton(text="🔍 Подбор запчасти", callback_data="scenario_free"),
            ],
            [
                InlineKeyboardButton(text="📋 Есть артикул", callback_data="scenario_article"),
                InlineKeyboardButton(text="🔢 Есть OEM номер", callback_data="scenario_oem"),
            ],
            [
                InlineKeyboardButton(text="🚗 Есть VIN", callback_data="scenario_vin"),
                InlineKeyboardButton(text="❓ Задать вопрос", callback_data="scenario_question"),
            ],
        ],
    )


async def show_main_menu(target: Union[Message, CallbackQuery]) -> None:
    """
    Показать стартовое меню. Вызывать после завершения диалога.
    target — Message или CallbackQuery (используется .message).
    """
    message = target.message if isinstance(target, CallbackQuery) else target
    await message.answer(MAIN_MENU_TEXT, reply_markup=start_menu_keyboard())


def results_keyboard() -> InlineKeyboardMarkup:
    """Кнопки после показа результатов."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Эконом", callback_data="tier_economy"),
                InlineKeyboardButton(text="🟡 Оптимум", callback_data="tier_optimal"),
                InlineKeyboardButton(text="🔵 OEM", callback_data="tier_oem"),
            ],
            [
                InlineKeyboardButton(text="🔄 Уточнить запрос", callback_data="reset"),
                InlineKeyboardButton(text="🆕 Новый поиск", callback_data="reset"),
            ],
        ],
    )


def feedback_request_keyboard() -> InlineKeyboardMarkup:
    """Кнопки оценки подбора. cycle_id берётся из FSM state."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Подошло", callback_data="feedback_like"),
                InlineKeyboardButton(text="👎 Не подошло", callback_data="feedback_dislike"),
            ],
        ],
    )


def like_category_keyboard() -> InlineKeyboardMarkup:
    """Кнопки после лайка."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t, callback_data=f"like_cat_{cat}")
                for t, cat in LIKE_CATEGORIES
            ],
        ],
    )


def dislike_reasons_keyboard() -> InlineKeyboardMarkup:
    """Кнопки причин дизлайка."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=f"dislike_reason_{reason}")]
            for t, reason in DISLIKE_REASONS
        ],
    )


def after_feedback_keyboard() -> InlineKeyboardMarkup:
    """После лайка: новый поиск / главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Новый поиск", callback_data="reset"),
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="reset"),
            ],
        ],
    )


def after_dislike_keyboard() -> InlineKeyboardMarkup:
    """После дизлайка: уточнить / главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Уточнить запрос", callback_data="reset"),
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="reset"),
            ],
        ],
    )


def skip_comment_keyboard() -> InlineKeyboardMarkup:
    """Кнопка пропустить комментарий."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пропустить", callback_data="dislike_skip")]
        ],
    )


async def show_feedback_request(target: Union[Message, CallbackQuery]) -> None:
    """Показать запрос оценки подбора. cycle_id берётся из FSM state вызывающего."""
    msg = target.message if isinstance(target, CallbackQuery) else target
    await msg.answer("Как вам этот подбор?", reply_markup=feedback_request_keyboard())


START_MESSAGE = """👋 Добро пожаловать в ИИ-подборщик запчастей!

Я помогу подобрать запчасти из нашего прайс-листа.
Найду лучшие варианты: Эконом / Оптимум / Оригинал.

Выберите сценарий или напишите запрос свободно:"""


SCENARIO_PROMPTS = {
    "maintenance": "📋 <b>Полное ТО</b>\n\nОпишите автомобиль для подбора комплекта расходников:\n"
    "Марка, модель, год (и двигатель если нужно).\n\n"
    "Пример: <i>Lada Vesta 2021, 1.6</i>",
    "article": "📋 <b>Поиск по артикулу</b>\n\nВведите артикул детали:",
    "oem": "📋 <b>Поиск по OEM номеру</b>\n\nВведите OEM-номер (например 90915-YZZF2):",
    "vin": "📋 <b>Поиск по VIN</b>\n\nВведите VIN автомобиля (17 символов):",
    "free": "🔍 <b>Подбор запчасти</b>\n\nНапишите что нужно, например:\n"
    "• <i>Передние колодки Camry 50</i>\n"
    "• <i>Масляный фильтр Kia Rio 2017</i>",
    "question": "❓ <b>Задать вопрос</b>\n\nНапишите ваш вопрос — я постараюсь помочь как эксперт по авто.",
    "help": "📋 <b>Помощь</b>\n\nПримеры запросов и команды.",
}
