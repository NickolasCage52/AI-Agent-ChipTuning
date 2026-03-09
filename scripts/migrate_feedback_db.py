"""Миграция БД: добавляет таблицы для Feedback Loop и Prompt Versioning.
Не удаляет существующие таблицы."""
from __future__ import annotations

import os
import sqlite3
import sys

# Добавить корень проекта в path
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

DB_PATH = os.getenv("DB_PATH", os.path.join(_root, "data", "parts.db"))


def run_migration() -> None:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)

    conn.executescript("""
-- Циклы диалога
CREATE TABLE IF NOT EXISTS dialogue_cycles (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    tg_user_hash TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    attempt_count INTEGER DEFAULT 0,
    final_status TEXT,
    intent TEXT,
    slots_json TEXT,
    all_messages_json TEXT,
    all_bot_responses_json TEXT,
    search_candidates_json TEXT,
    tiers_shown_json TEXT,
    tier_selected TEXT,
    llm_model TEXT,
    prompt_version TEXT,
    adaptive_overlay_version TEXT,
    fallback_used INTEGER DEFAULT 0,
    llm_input_safe TEXT,
    llm_output_raw TEXT,
    total_latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Обратная связь
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id TEXT NOT NULL,
    tg_user_hash TEXT NOT NULL,
    rating TEXT NOT NULL,
    like_category TEXT,
    dislike_reason TEXT,
    user_comment TEXT,
    error_class TEXT,
    is_good_example INTEGER DEFAULT 0,
    is_bad_example INTEGER DEFAULT 0,
    requires_manual_review INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cycle_id) REFERENCES dialogue_cycles(id)
);

-- Версии промптов
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
);

-- Изменения адаптивного слоя
CREATE TABLE IF NOT EXISTS overlay_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_version TEXT,
    change_type TEXT,
    change_key TEXT,
    old_value TEXT,
    new_value TEXT,
    based_on_feedback_count INTEGER,
    auto_generated INTEGER DEFAULT 0,
    approved INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Архив старых feedback
CREATE TABLE IF NOT EXISTS feedback_archive (
    id INTEGER PRIMARY KEY,
    cycle_id TEXT NOT NULL,
    tg_user_hash TEXT NOT NULL,
    rating TEXT NOT NULL,
    like_category TEXT,
    dislike_reason TEXT,
    user_comment TEXT,
    error_class TEXT,
    is_good_example INTEGER DEFAULT 0,
    is_bad_example INTEGER DEFAULT 0,
    requires_manual_review INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_feedback_cycle ON feedback(cycle_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_cycles_status ON dialogue_cycles(final_status);
CREATE INDEX IF NOT EXISTS idx_cycles_intent ON dialogue_cycles(intent);
CREATE INDEX IF NOT EXISTS idx_cycles_created ON dialogue_cycles(created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_active ON prompt_versions(is_active);
""")

    # Начальная версия 1.0.0 для отката
    core_path = os.path.join(_root, "config", "prompt_core.txt")
    overlay_path = os.path.join(_root, "config", "prompt_overlay.yaml")
    core_text = "Ты — эксперт по автозапчастям."
    overlay_text = "version: '1.0.0'\noverlay: {}"
    if os.path.exists(core_path):
        with open(core_path, encoding="utf-8") as f:
            core_text = f.read()
    if os.path.exists(overlay_path):
        with open(overlay_path, encoding="utf-8") as f:
            overlay_text = f.read()
    conn.execute(
        """INSERT OR IGNORE INTO prompt_versions (version, prompt_core, prompt_overlay, change_source, is_active)
           VALUES ('1.0.0', ?, ?, 'manual', 1)""",
        (core_text, overlay_text),
    )

    # SQL views для аналитики
    conn.executescript("""
-- Процент успешных диалогов
CREATE VIEW IF NOT EXISTS v_quality_summary AS
SELECT
    DATE(created_at) as day,
    COUNT(*) as total,
    SUM(CASE WHEN final_status = 'success' THEN 1 ELSE 0 END) as success,
    SUM(CASE WHEN final_status = 'failed' THEN 1 ELSE 0 END) as failed,
    ROUND(100.0 * SUM(CASE WHEN final_status = 'success' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as success_rate
FROM dialogue_cycles
GROUP BY DATE(created_at);

-- Частые причины дизлайков
CREATE VIEW IF NOT EXISTS v_top_dislike_reasons AS
SELECT dislike_reason, error_class, COUNT(*) as cnt
FROM feedback WHERE rating = 'dislike'
GROUP BY dislike_reason ORDER BY cnt DESC;

-- Проблемные интенты
CREATE VIEW IF NOT EXISTS v_intent_quality AS
SELECT
    dc.intent,
    COUNT(*) as total,
    SUM(CASE WHEN f.rating = 'like' THEN 1 ELSE 0 END) as likes,
    SUM(CASE WHEN f.rating = 'dislike' THEN 1 ELSE 0 END) as dislikes
FROM dialogue_cycles dc
LEFT JOIN feedback f ON f.cycle_id = dc.id
GROUP BY dc.intent;
""")

    conn.commit()
    conn.close()
    print(f"OK: Feedback DB migration applied to {DB_PATH}")


if __name__ == "__main__":
    run_migration()
