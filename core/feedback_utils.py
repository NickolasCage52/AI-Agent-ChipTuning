"""Утилиты для Feedback Loop: анонимизация, ErrorClass."""
from __future__ import annotations

import hashlib
from typing import Any


def anonymize_user_id(tg_user_id: int) -> str:
    """sha256 от user_id — не восстанавливается, но одинаковый для одного юзера."""
    return hashlib.sha256(str(tg_user_id).encode()).hexdigest()[:16]


class ErrorClass:
    """Классы ошибок для классификации feedback."""
    UNDERSTANDING = "understanding"
    EXTRACTION = "extraction"
    SEARCH = "search"
    RANKING = "ranking"
    DIALOGUE = "dialogue"
    UX = "ux"
    DATA = "data"
    LLM_PIPELINE = "llm_pipeline"


DISLIKE_TO_ERROR_CLASS: dict[str, str | None] = {
    "wrong_understanding": ErrorClass.UNDERSTANDING,
    "wrong_parts": ErrorClass.SEARCH,
    "wrong_car": ErrorClass.EXTRACTION,
    "wrong_vin_engine": ErrorClass.EXTRACTION,
    "bad_questions": ErrorClass.DIALOGUE,
    "no_price": ErrorClass.DATA,
    "no_delivery": ErrorClass.DATA,
    "bad_answer": ErrorClass.UX,
    "other": None,
}


def get_error_class(dislike_reason: str | None) -> str | None:
    """Маппинг причины дизлайка в класс ошибки."""
    if not dislike_reason:
        return None
    return DISLIKE_TO_ERROR_CLASS.get(dislike_reason)
