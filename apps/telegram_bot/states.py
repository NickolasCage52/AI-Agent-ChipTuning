"""FSM-состояния диалога Parts Assistant."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class PartsSearch(StatesGroup):
    idle = State()
    waiting_clarification = State()
    showing_results = State()
