"""SQLite FSM storage — контекст не теряется при перезапуске."""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from aiogram.fsm.storage.base import BaseStorage, StorageKey

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "parts.db"))


def _key_str(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}"


def _get_conn() -> sqlite3.Connection:
    path = DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fsm_storage (
            key TEXT PRIMARY KEY,
            state TEXT,
            data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


class SQLiteStorage(BaseStorage):
    """FSM storage на SQLite."""

    def __init__(self, db_path: str | None = None):
        self._path = db_path or DB_PATH
        self._conn: sqlite3.Connection | None = None

    def _conn_get(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = _get_conn()
        return self._conn

    async def set_state(self, key: StorageKey, state: str | None = None) -> None:
        k = _key_str(key)
        state_val = state.state if hasattr(state, "state") and state else (state if isinstance(state, str) else None)
        conn = self._conn_get()
        cur = conn.execute("SELECT 1 FROM fsm_storage WHERE key=?", (k,))
        if cur.fetchone():
            conn.execute("UPDATE fsm_storage SET state=?, updated_at=CURRENT_TIMESTAMP WHERE key=?", (state_val, k))
        else:
            conn.execute(
                "INSERT INTO fsm_storage (key, state, data) VALUES (?, ?, '{}')",
                (k, state_val),
            )
        conn.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        k = _key_str(key)
        row = self._conn_get().execute("SELECT state FROM fsm_storage WHERE key=?", (k,)).fetchone()
        return row[0] if row and row[0] else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        k = _key_str(key)
        conn = self._conn_get()
        row = conn.execute("SELECT state FROM fsm_storage WHERE key=?", (k,)).fetchone()
        js = json.dumps(data, ensure_ascii=False)
        if row:
            conn.execute("UPDATE fsm_storage SET data=?, updated_at=CURRENT_TIMESTAMP WHERE key=?", (js, k))
        else:
            conn.execute("INSERT INTO fsm_storage (key, state, data) VALUES (?, NULL, ?)", (k, js))
        conn.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        k = _key_str(key)
        row = self._conn_get().execute("SELECT data FROM fsm_storage WHERE key=?", (k,)).fetchone()
        if not row or not row[0]:
            return {}
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return {}

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
