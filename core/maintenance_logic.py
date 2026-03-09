"""Логика подбора комплекта ТО по уровням (базовое / стандартное / полное)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "maintenance_config.yaml"


def _load_config() -> dict[str, Any]:
    """Загрузить конфиг ТО."""
    try:
        import yaml
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def get_maintenance_parts(level: str = "full") -> list[dict[str, Any]]:
    """
    Вернуть список деталей для ТО по уровню.
    level: "basic" | "standard" | "full"
    """
    cfg = _load_config()
    levels = cfg.get("maintenance_levels", {})
    result: list[dict[str, Any]] = []

    def add_items(items: list) -> None:
        for it in items:
            if isinstance(it, dict) and "name" in it:
                result.append(it)

    # Basic first
    basic = levels.get("basic", [])
    if isinstance(basic, list):
        add_items(basic)

    if level in ("standard", "full"):
        std = levels.get("standard", {})
        if isinstance(std, dict) and "items" in std:
            add_items(std["items"])

    if level == "full":
        full = levels.get("full", {})
        if isinstance(full, dict) and "items" in full:
            add_items(full["items"])

    return result


def build_maintenance_search_queries(
    level: str = "full",
    car_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Построить список поисковых запросов для комплекта ТО.
    Возвращает [{name, search_terms, priority}, ...]
    """
    parts = get_maintenance_parts(level)
    return [
        {
            "name": p["name"],
            "search_terms": p.get("search_terms", [p["name"]]),
            "priority": p.get("priority", "required"),
            "mileage_trigger": p.get("mileage_trigger"),
        }
        for p in parts
    ]
