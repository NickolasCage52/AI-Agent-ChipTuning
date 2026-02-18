from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TelegramMessage:
    tg_id: int
    chat_id: int
    text: str
    name: str | None = None
    username: str | None = None


def parse_update(update: dict[str, Any]) -> TelegramMessage | None:
    msg = update.get("message") or update.get("edited_message") or {}
    text = msg.get("text")
    if not text:
        return None
    user = msg.get("from") or {}
    chat = msg.get("chat") or {}
    tg_id = user.get("id")
    chat_id = chat.get("id")
    if tg_id is None or chat_id is None:
        return None
    name = user.get("first_name") or user.get("last_name")
    return TelegramMessage(
        tg_id=int(tg_id),
        chat_id=int(chat_id),
        text=str(text),
        name=name,
        username=user.get("username"),
    )

