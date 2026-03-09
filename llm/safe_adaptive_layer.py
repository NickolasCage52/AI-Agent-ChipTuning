"""Безопасный адаптивный слой — только разрешённые автоматические изменения."""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_root = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
OVERLAY_PATH = CONFIG_DIR / "prompt_overlay.yaml"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "parts.db"

SAFE_MUTATION_KEYS = {
    "synonyms",
    "few_shot_examples",
    "clarification_templates",
    "normalization_hints",
    "ranking_weights",
}

PROTECTED_KEYS = {
    "core_role",
    "data_source_rules",
    "search_logic",
    "output_format",
}


def _load_overlay() -> dict:
    if OVERLAY_PATH.exists():
        with open(OVERLAY_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {"version": "1.0.0", "overlay": {}}


def _save_overlay(data: dict) -> None:
    OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OVERLAY_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _log_overlay_change(
    prompt_version: str,
    change_type: str,
    change_key: str,
    old_value: str,
    new_value: str,
    based_on_feedback_count: int = 0,
    auto_generated: int = 1,
) -> None:
    """Записать изменение в overlay_changes."""
    import sqlite3
    import os
    db_path = os.getenv("DB_PATH", str(DB_PATH))
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO overlay_changes
               (prompt_version, change_type, change_key, old_value, new_value,
                based_on_feedback_count, auto_generated, approved)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                prompt_version,
                change_type,
                change_key,
                old_value[:500] if old_value else "",
                new_value[:500] if new_value else "",
                based_on_feedback_count,
                auto_generated,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Failed to log overlay change: %s", e)


async def apply_safe_adaptation(suggestions: list[dict]) -> str:
    """
    Применить безопасные автоматические улучшения.
    Возвращает новый version string.
    Логирует всё в overlay_changes.
    """
    if not suggestions:
        return _load_overlay().get("version", "1.0.0")

    data = _load_overlay()
    ov = data.get("overlay", {})
    if not isinstance(ov, dict):
        ov = {}

    version = data.get("version", "1.0.0")
    applied = 0

    for s in suggestions:
        key = s.get("key") or s.get("change_key")
        if not key:
            continue
        if key in PROTECTED_KEYS:
            logger.warning("Blocked auto-mutation of protected key: %s", key)
            continue
        if key not in SAFE_MUTATION_KEYS:
            logger.warning("Unknown mutation key: %s, skipping", key)
            continue

        old_val = ov.get(key)
        new_val = s.get("value") or s.get("new_value")
        change_type = s.get("change_type", "heuristic")
        feedback_count = s.get("based_on_feedback_count", 0)

        if new_val is not None:
            ov[key] = new_val
            _log_overlay_change(
                prompt_version=version,
                change_type=change_type,
                change_key=key,
                old_value=str(old_val)[:200] if old_val else "",
                new_value=str(new_val)[:200] if new_val else "",
                based_on_feedback_count=feedback_count,
                auto_generated=1,
            )
            applied += 1

    if applied > 0:
        data["overlay"] = ov
        parts = version.split(".")
        try:
            patch = int(parts[-1]) + 1
            new_ver = ".".join(parts[:-1] + [str(patch)])
        except (ValueError, IndexError):
            new_ver = f"{version}.1"
        data["version"] = new_ver
        data["change_source"] = "auto_feedback"
        _save_overlay(data)
        return new_ver
    return version
