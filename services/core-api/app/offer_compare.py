from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


def _d(v: Any, default: Decimal) -> Decimal:
    try:
        if v is None:
            return default
        return Decimal(str(v))
    except Exception:
        return default


def _i(v: Any, default: int) -> int:
    try:
        if v is None:
            return default
        return int(v)
    except Exception:
        return default


def rank_offers(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Sort priority:
    1) in-stock first (stock > 0)
    2) lower price
    3) lower delivery_days
    """

    def key(o: dict[str, Any]):
        stock = _i(o.get("stock"), 0)
        in_stock = 0 if stock > 0 else 1
        price = _d(o.get("price"), Decimal("999999999"))
        delivery = _i(o.get("delivery_days"), 999999)
        return (in_stock, price, delivery)

    return sorted(offers, key=key)

