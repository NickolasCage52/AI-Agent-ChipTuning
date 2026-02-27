"""Поиск по БД поставщиков."""
from __future__ import annotations

from app.chat.parts_search import search_by_sku_oem, search_parts

__all__ = ["search_parts", "search_by_sku_oem"]
