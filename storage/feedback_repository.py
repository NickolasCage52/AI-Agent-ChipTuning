"""CRUD для feedback и dialogue_cycles."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DB_PATH", os.path.join(_root, "data", "parts.db"))


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    return sqlite3.connect(DB_PATH)


@dataclass
class DialogueCycle:
    id: str
    session_id: str
    tg_user_hash: str
    started_at: str | None = None
    finished_at: str | None = None
    attempt_count: int = 0
    final_status: str | None = None
    intent: str | None = None
    slots_json: str | None = None
    all_messages_json: str | None = None
    all_bot_responses_json: str | None = None
    search_candidates_json: str | None = None
    tiers_shown_json: str | None = None
    tier_selected: str | None = None
    llm_model: str | None = None
    prompt_version: str | None = None
    adaptive_overlay_version: str | None = None
    fallback_used: int = 0
    llm_input_safe: str | None = None
    llm_output_raw: str | None = None
    total_latency_ms: int | None = None
    created_at: str | None = None


@dataclass
class Feedback:
    cycle_id: str
    tg_user_hash: str
    rating: str  # like | dislike
    like_category: str | None = None
    dislike_reason: str | None = None
    user_comment: str | None = None
    error_class: str | None = None
    is_good_example: int = 0
    is_bad_example: int = 0
    requires_manual_review: int = 0


async def save_dialogue_cycle(cycle: DialogueCycle) -> str:
    """Сохранить цикл диалога. Возвращает cycle_id."""
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO dialogue_cycles (
                id, session_id, tg_user_hash, started_at, finished_at, attempt_count,
                final_status, intent, slots_json, all_messages_json, all_bot_responses_json,
                search_candidates_json, tiers_shown_json, tier_selected, llm_model,
                prompt_version, adaptive_overlay_version, fallback_used, llm_input_safe,
                llm_output_raw, total_latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cycle.id, cycle.session_id, cycle.tg_user_hash, cycle.started_at,
                cycle.finished_at, cycle.attempt_count, cycle.final_status, cycle.intent,
                cycle.slots_json, cycle.all_messages_json, cycle.all_bot_responses_json,
                cycle.search_candidates_json, cycle.tiers_shown_json, cycle.tier_selected,
                cycle.llm_model, cycle.prompt_version, cycle.adaptive_overlay_version,
                cycle.fallback_used, cycle.llm_input_safe, cycle.llm_output_raw,
                cycle.total_latency_ms,
            ),
        )
        conn.commit()
        return cycle.id
    finally:
        conn.close()


async def update_dialogue_cycle(
    cycle_id: str,
    *,
    attempt_count: int | None = None,
    final_status: str | None = None,
    finished_at: str | None = None,
    intent: str | None = None,
    slots_json: str | None = None,
    all_messages_json: str | None = None,
    all_bot_responses_json: str | None = None,
    tiers_shown_json: str | None = None,
    tier_selected: str | None = None,
    llm_model: str | None = None,
    prompt_version: str | None = None,
) -> None:
    """Обновить поля цикла диалога."""
    updates = []
    values = []
    if attempt_count is not None:
        updates.append("attempt_count = ?")
        values.append(attempt_count)
    if final_status is not None:
        updates.append("final_status = ?")
        values.append(final_status)
    if finished_at is not None:
        updates.append("finished_at = ?")
        values.append(finished_at)
    if intent is not None:
        updates.append("intent = ?")
        values.append(intent)
    if slots_json is not None:
        updates.append("slots_json = ?")
        values.append(slots_json)
    if all_messages_json is not None:
        updates.append("all_messages_json = ?")
        values.append(all_messages_json)
    if all_bot_responses_json is not None:
        updates.append("all_bot_responses_json = ?")
        values.append(all_bot_responses_json)
    if tiers_shown_json is not None:
        updates.append("tiers_shown_json = ?")
        values.append(tiers_shown_json)
    if tier_selected is not None:
        updates.append("tier_selected = ?")
        values.append(tier_selected)
    if llm_model is not None:
        updates.append("llm_model = ?")
        values.append(llm_model)
    if prompt_version is not None:
        updates.append("prompt_version = ?")
        values.append(prompt_version)

    if not updates:
        return
    values.append(cycle_id)
    conn = _get_conn()
    try:
        conn.execute(
            f"UPDATE dialogue_cycles SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        conn.commit()
    finally:
        conn.close()


async def get_dialogue_cycle(cycle_id: str) -> DialogueCycle | None:
    """Получить цикл по id."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT id, session_id, tg_user_hash, started_at, finished_at, attempt_count, "
            "final_status, intent, slots_json, all_messages_json, all_bot_responses_json, "
            "search_candidates_json, tiers_shown_json, tier_selected, llm_model, prompt_version, "
            "adaptive_overlay_version, fallback_used, llm_input_safe, llm_output_raw, total_latency_ms, created_at "
            "FROM dialogue_cycles WHERE id = ?",
            (cycle_id,),
        ).fetchone()
        if not row:
            return None
        return DialogueCycle(
            id=row[0], session_id=row[1], tg_user_hash=row[2], started_at=row[3],
            finished_at=row[4], attempt_count=row[5] or 0, final_status=row[6],
            intent=row[7], slots_json=row[8], all_messages_json=row[9], all_bot_responses_json=row[10],
            search_candidates_json=row[11], tiers_shown_json=row[12], tier_selected=row[13],
            llm_model=row[14], prompt_version=row[15], adaptive_overlay_version=row[16],
            fallback_used=row[17] or 0, llm_input_safe=row[18], llm_output_raw=row[19],
            total_latency_ms=row[20], created_at=row[21],
        )
    finally:
        conn.close()


async def save_feedback(feedback: Feedback) -> int:
    """Сохранить feedback. Возвращает id записи."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO feedback (cycle_id, tg_user_hash, rating, like_category, dislike_reason,
               user_comment, error_class, is_good_example, is_bad_example, requires_manual_review)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feedback.cycle_id, feedback.tg_user_hash, feedback.rating,
                feedback.like_category, feedback.dislike_reason, feedback.user_comment,
                feedback.error_class, feedback.is_good_example, feedback.is_bad_example,
                feedback.requires_manual_review,
            ),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


async def get_bad_examples(limit: int = 50) -> list[dict]:
    """Плохие примеры для анализа."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT f.id, f.cycle_id, f.dislike_reason, f.user_comment, f.error_class,
                      dc.intent, dc.slots_json, dc.all_messages_json
               FROM feedback f
               JOIN dialogue_cycles dc ON dc.id = f.cycle_id
               WHERE f.rating = 'dislike'
               ORDER BY f.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0], "cycle_id": r[1], "dislike_reason": r[2], "user_comment": r[3],
                "error_class": r[4], "intent": r[5], "slots_json": r[6], "all_messages_json": r[7],
            }
            for r in rows
        ]
    finally:
        conn.close()


async def get_good_examples(limit: int = 50) -> list[dict]:
    """Хорошие примеры для few-shot."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT f.id, f.cycle_id, f.like_category, dc.intent, dc.slots_json, dc.all_messages_json
               FROM feedback f
               JOIN dialogue_cycles dc ON dc.id = f.cycle_id
               WHERE f.rating = 'like'
               ORDER BY f.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0], "cycle_id": r[1], "like_category": r[2], "intent": r[3],
                "slots_json": r[4], "all_messages_json": r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


async def get_frequent_errors(days: int = 30) -> list[dict]:
    """Частые ошибки за период."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT dislike_reason, error_class, COUNT(*) as cnt
               FROM feedback WHERE rating = 'dislike' AND created_at >= datetime('now', ?)
               GROUP BY dislike_reason ORDER BY cnt DESC""",
            (f"-{days} days",),
        ).fetchall()
        return [{"dislike_reason": r[0], "error_class": r[1], "count": r[2]} for r in rows]
    finally:
        conn.close()


async def get_search_misses(days: int = 30) -> list[dict]:
    """Пропуски поиска (wrong_parts, wrong_car, wrong_vin_engine)."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT f.dislike_reason, dc.slots_json, dc.intent
               FROM feedback f
               JOIN dialogue_cycles dc ON dc.id = f.cycle_id
               WHERE f.rating = 'dislike' AND f.dislike_reason IN ('wrong_parts', 'wrong_car', 'wrong_vin_engine')
               AND f.created_at >= datetime('now', ?)""",
            (f"-{days} days",),
        ).fetchall()
        return [{"dislike_reason": r[0], "slots_json": r[1], "intent": r[2]} for r in rows]
    finally:
        conn.close()


async def mark_for_review(cycle_id: str) -> None:
    """Пометить feedback для ручного разбора."""
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE feedback SET requires_manual_review = 1 WHERE cycle_id = ?",
            (cycle_id,),
        )
        conn.commit()
    finally:
        conn.close()


async def export_dataset(output_path: str, days: int = 90) -> None:
    """Экспорт feedback для анализа/дообучения."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT dc.id, dc.intent, dc.slots_json, dc.all_messages_json, dc.all_bot_responses_json,
                      f.rating, f.dislike_reason, f.user_comment, f.error_class, f.like_category,
                      f.is_good_example, f.is_bad_example, dc.prompt_version, dc.llm_model
               FROM dialogue_cycles dc
               LEFT JOIN feedback f ON f.cycle_id = dc.id
               WHERE dc.created_at >= datetime('now', ?)""",
            (f"-{days} days",),
        ).fetchall()
        import csv
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "cycle_id", "intent", "slots", "user_query", "bot_response", "rating",
                "dislike_reason", "user_comment", "error_class", "like_category",
                "is_good_example", "is_bad_example", "prompt_version", "model",
            ])
            for r in rows:
                msgs = json.loads(r[3]) if r[3] else []
                resp = json.loads(r[4]) if r[4] else []
                user_query = msgs[-1] if msgs else ""
                bot_response = resp[-1] if resp else ""
                w.writerow([
                    r[0], r[1], r[2], user_query, bot_response, r[5] or "", r[6] or "",
                    r[7] or "", r[8] or "", r[9] or "", r[10] or 0, r[11] or 0, r[12] or "", r[13] or "",
                ])
    finally:
        conn.close()


async def archive_old_feedback(older_than_days: int = 90) -> int:
    """Перенести feedback старше N дней в feedback_archive. Возвращает кол-во перенесённых."""
    cutoff = (datetime.utcnow() - timedelta(days=older_than_days)).isoformat()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, cycle_id, tg_user_hash, rating, like_category, dislike_reason, "
            "user_comment, error_class, is_good_example, is_bad_example, requires_manual_review, created_at "
            "FROM feedback WHERE created_at < ?",
            (cutoff,),
        ).fetchall()
        count = 0
        for r in rows:
            conn.execute(
                """INSERT OR IGNORE INTO feedback_archive
                   (id, cycle_id, tg_user_hash, rating, like_category, dislike_reason,
                    user_comment, error_class, is_good_example, is_bad_example, requires_manual_review, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                r,
            )
            conn.execute("DELETE FROM feedback WHERE id = ?", (r[0],))
            count += 1
        conn.commit()
        return count
    finally:
        conn.close()
