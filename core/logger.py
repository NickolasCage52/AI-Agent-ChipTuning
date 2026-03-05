"""Логирование событий Parts Assistant (без зависимости от PostgreSQL)."""
from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger("parts_assistant")


def log_event(event_type: str, data: dict) -> None:
    """Логировать событие в файл/stdout."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        **data,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))


async def log_event_to_db(event_type: str, data: dict) -> None:
    """Заглушка: сохранение в БД отключено для режима price-only."""
    pass
