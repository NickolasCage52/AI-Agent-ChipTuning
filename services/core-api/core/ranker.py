"""Ранжирование и сборка 3 тиров (economy, optimal, oem)."""
from __future__ import annotations

from typing import Any

from app.chat.parts_search import rank_and_tier


def build_tiers(
    parts: list[dict[str, Any]],
    car_brand: str | None = None,
    car_model: str | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Собрать 3 тира из списка запчастей."""
    return rank_and_tier(parts, car_brand=car_brand, car_model=car_model, weights=weights)


__all__ = ["build_tiers"]
