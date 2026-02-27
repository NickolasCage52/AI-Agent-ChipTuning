"""Логирование событий Parts Assistant (файл + опционально БД)."""
from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger("parts_assistant")


def log_event(event_type: str, data: dict) -> None:
    """Логировать событие в файл."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        **data,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))


async def log_event_to_db(event_type: str, data: dict) -> None:
    """Сохранить событие в tg_search_history (если БД доступна)."""
    try:
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.db.session import AsyncSessionLocal
        from app.models import TgSearchHistory

        async with AsyncSessionLocal() as db:
            record = TgSearchHistory(
                tg_user_id=data.get("tg_user_id"),
                event_type=event_type,
                raw_query=data.get("raw_query") or data.get("query"),
                masked_query=data.get("masked_query") or data.get("query"),
                intent=data.get("intent"),
                slots=data.get("slots") or {},
                results=data.get("results") or {},
                selected_tier=data.get("tier"),
            )
            db.add(record)
            await db.commit()
    except ImportError:
        pass
    except Exception as e:
        logger.warning("Failed to save event to DB: %s", e)
