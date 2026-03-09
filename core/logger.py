"""Логирование событий Parts Assistant (SQLite debug_logs)."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime

logger = logging.getLogger("parts_assistant")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "parts.db"))


def _ensure_debug_logs():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS debug_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            tg_user_id INTEGER,
            event_type TEXT NOT NULL,
            payload_json TEXT,
            llm_backend TEXT,
            latency_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_event(event_type: str, data: dict) -> None:
    """Логировать событие в файл/stdout."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        **data,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))


async def log_event_to_db(
    event_type: str,
    data: dict,
    session_id: str | None = None,
    llm_backend: str | None = None,
    latency_ms: int | None = None,
) -> None:
    """Сохранить событие в таблицу debug_logs."""
    try:
        _ensure_debug_logs()
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """INSERT INTO debug_logs (session_id, tg_user_id, event_type, payload_json, llm_backend, latency_ms)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                data.get("tg_user_id"),
                event_type,
                json.dumps(data, ensure_ascii=False),
                llm_backend,
                latency_ms,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("log_event_to_db failed: %s", e)
