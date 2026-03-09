"""Версионирование и управление промптами (core + overlay)."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_root = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", _root / "config"))
CORE_PATH = CONFIG_DIR / "prompt_core.txt"
OVERLAY_PATH = CONFIG_DIR / "prompt_overlay.yaml"
DB_PATH = os.getenv("DB_PATH", str(_root / "data" / "parts.db"))


def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _load_core() -> str:
    """Загрузить неизменяемое ядро."""
    if CORE_PATH.exists():
        return CORE_PATH.read_text(encoding="utf-8").strip()
    logger.warning("prompt_core.txt not found, using fallback")
    return "Ты — эксперт по автозапчастям. Извлекаешь intent и слоты. Отвечай только JSON."


def _load_overlay() -> dict:
    """Загрузить overlay из YAML."""
    if OVERLAY_PATH.exists():
        with open(OVERLAY_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {"version": "1.0.0", "overlay": {}}


def _save_overlay(data: dict) -> None:
    """Сохранить overlay в YAML."""
    OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OVERLAY_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _render_overlay(overlay: dict) -> str:
    """Преобразовать overlay dict в текст для промпта."""
    parts = []
    ov = overlay.get("overlay", overlay) if isinstance(overlay.get("overlay"), dict) else overlay
    if not isinstance(ov, dict):
        return ""

    # Синонимы
    syn = ov.get("synonyms", [])
    if syn:
        parts.append("\nДополнительные синонимы:")
        for s in syn:
            raw = s.get("raw", [])
            norm = s.get("normalized", "")
            if isinstance(raw, str):
                raw = [raw]
            if raw and norm:
                parts.append(f"- {raw} → {norm}")

    # Few-shot примеры
    examples = ov.get("few_shot_examples", [])
    if examples:
        parts.append("\nПримеры хороших запросов:")
        for ex in examples[:5]:
            if isinstance(ex, dict):
                q = ex.get("query", ex.get("text", str(ex)))
                parts.append(f"  Запрос: {q}")
            else:
                parts.append(f"  {ex}")

    # Clarification templates (информационно)
    ct = ov.get("clarification_templates", {})
    if ct:
        parts.append("\nШаблоны уточнений: " + ", ".join(f"{k}={v[:30]}..." if len(str(v)) > 30 else f"{k}={v}" for k, v in list(ct.items())[:3]))

    return "\n".join(parts) if parts else ""


class PromptManager:
    """Управление core + overlay, версионирование."""

    def __init__(self) -> None:
        self._core = _load_core()
        self._overlay = _load_overlay()

    def _ensure_prompt_versions(self) -> None:
        """Создать таблицу и начальную запись при необходимости."""
        conn = _get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE,
                    prompt_core TEXT NOT NULL,
                    prompt_overlay TEXT,
                    change_source TEXT,
                    change_reason TEXT,
                    based_on_feedback_ids TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rolled_back_at TIMESTAMP
                )
            """)
            row = conn.execute(
                "SELECT id FROM prompt_versions WHERE is_active = 1"
            ).fetchone()
            if not row:
                # Вставить текущий overlay как версию 1.0.0
                overlay_yaml = yaml.dump(self._overlay, allow_unicode=True, sort_keys=False)
                conn.execute(
                    """INSERT OR IGNORE INTO prompt_versions
                       (version, prompt_core, prompt_overlay, change_source, is_active)
                       VALUES (?, ?, ?, 'manual', 1)""",
                    (self._overlay.get("version", "1.0.0"), self._core, overlay_yaml),
                )
                conn.commit()
        finally:
            conn.close()

    def get_active_prompt(self) -> tuple[str, str]:
        """Вернуть (system_prompt, version)."""
        self._core = _load_core()
        self._overlay = _load_overlay()
        overlay_text = _render_overlay(self._overlay)
        version = str(self._overlay.get("version", "1.0.0"))
        if overlay_text:
            full = f"{self._core}\n\n{overlay_text}"
        else:
            full = self._core
        return full, version

    def create_new_version(
        self,
        changes: dict,
        source: str = "manual",
        reason: str = "",
        feedback_ids: list[int] | None = None,
    ) -> str:
        """Создать новую версию overlay. Применяет changes поверх текущего overlay."""
        self._overlay = _load_overlay()
        ov = self._overlay.get("overlay", {})
        if not isinstance(ov, dict):
            ov = {}

        # Глубокое слияние changes в overlay
        for key, value in changes.items():
            if key in ("version", "created_at", "change_source"):
                continue
            if key == "overlay" and isinstance(value, dict):
                for k, v in value.items():
                    ov[k] = v
            elif key != "overlay":
                ov[key] = value

        self._overlay["overlay"] = ov
        # Инкремент версии
        cur_ver = self._overlay.get("version", "1.0.0")
        parts = cur_ver.split(".")
        if len(parts) == 3:
            try:
                patch = int(parts[2]) + 1
                new_ver = f"{parts[0]}.{parts[1]}.{patch}"
            except ValueError:
                new_ver = f"{cur_ver}.1"
        else:
            new_ver = "1.0.1"
        self._overlay["version"] = new_ver
        self._overlay["change_source"] = source
        self._overlay["change_reason"] = reason

        _save_overlay(self._overlay)
        overlay_yaml = yaml.dump(self._overlay, allow_unicode=True, sort_keys=False)

        self._ensure_prompt_versions()
        conn = _get_conn()
        try:
            for attempt in range(10):
                try:
                    conn.execute("UPDATE prompt_versions SET is_active = 0 WHERE 1=1")
                    conn.execute(
                        """INSERT INTO prompt_versions
                           (version, prompt_core, prompt_overlay, change_source, change_reason,
                            based_on_feedback_ids, is_active)
                           VALUES (?, ?, ?, ?, ?, ?, 1)""",
                        (
                            new_ver,
                            self._core,
                            overlay_yaml,
                            source,
                            reason,
                            json.dumps(feedback_ids) if feedback_ids else None,
                        ),
                    )
                    conn.commit()
                    break
                except Exception as e:
                    if "UNIQUE" in str(e) or "IntegrityError" in str(type(e).__name__):
                        parts = new_ver.split(".")
                        try:
                            p = int(parts[-1]) + 1
                            new_ver = ".".join(parts[:-1] + [str(p)])
                        except (ValueError, IndexError):
                            new_ver = f"{new_ver}.1"
                    else:
                        raise
        finally:
            conn.close()
        return new_ver

    def rollback_to_version(self, version: str) -> None:
        """Откатить overlay к указанной версии."""
        conn = _get_conn()
        try:
            row = conn.execute(
                "SELECT prompt_overlay FROM prompt_versions WHERE version = ?",
                (version,),
            ).fetchone()
            if not row:
                raise ValueError(f"Version {version} not found")
            overlay_content = row[0]
            data = yaml.safe_load(overlay_content)
            _save_overlay(data)
            self._overlay = data
            conn.execute("UPDATE prompt_versions SET is_active = 0 WHERE 1=1")
            conn.execute(
                "UPDATE prompt_versions SET is_active = 1, rolled_back_at = NULL WHERE version = ?",
                (version,),
            )
            conn.execute(
                "UPDATE prompt_versions SET rolled_back_at = datetime('now') WHERE version != ?",
                (version,),
            )
            conn.commit()
        finally:
            conn.close()

    def get_version_history(self) -> list[dict]:
        """Список всех версий overlay."""
        conn = _get_conn()
        try:
            rows = conn.execute(
                """SELECT version, change_source, change_reason, is_active, created_at, rolled_back_at
                   FROM prompt_versions ORDER BY created_at DESC LIMIT 50"""
            ).fetchall()
            return [
                {
                    "version": r[0],
                    "change_source": r[1],
                    "change_reason": r[2],
                    "is_active": bool(r[3]),
                    "created_at": r[4],
                    "rolled_back_at": r[5],
                }
                for r in rows
            ]
        finally:
            conn.close()


# Синглтон для использования в intent.py
_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    global _manager
    if _manager is None:
        _manager = PromptManager()
    return _manager
