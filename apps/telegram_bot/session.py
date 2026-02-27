"""Хранение контекста пользователя (опционально в БД)."""
from __future__ import annotations

# MVP: используем только FSM data, персистенцию в tg_sessions можно добавить позже
# load_session / save_session — заглушки для совместимости с handlers


def load_session(tg_user_id: int) -> dict | None:
    """Загрузить контекст сессии из БД (опционально)."""
    return None


def save_session(tg_user_id: int, data: dict) -> None:
    """Сохранить контекст сессии в БД (опционально)."""
    pass
