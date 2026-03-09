"""Анализ feedback DB и рекомендации по улучшению."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DB_PATH", os.path.join(_root, "data", "parts.db"))


def _get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


@dataclass
class Suggestion:
    key: str
    change_type: str
    value: any
    reason: str
    based_on_feedback_count: int = 0


async def get_synonym_suggestions() -> list[dict]:
    """На основе частых dislike 'wrong_understanding' — какие слова не распознаются."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT f.user_comment, dc.all_messages_json
               FROM feedback f
               JOIN dialogue_cycles dc ON dc.id = f.cycle_id
               WHERE f.rating = 'dislike' AND f.dislike_reason = 'wrong_understanding'
               ORDER BY f.created_at DESC LIMIT 100"""
        ).fetchall()
        words = []
        for r in rows:
            comment = (r[0] or "").lower()
            msgs = json.loads(r[1]) if r[1] else []
            for m in msgs:
                if isinstance(m, str):
                    words.extend(m.lower().split())
            if comment:
                words.extend(comment.split())
        counter = Counter(w for w in words if len(w) > 3 and w.replace("-", "").isalnum())
        return [{"word": w, "count": c} for w, c in counter.most_common(20)]
    finally:
        conn.close()


async def get_prompt_improvement_suggestions() -> list[dict]:
    """На основе частых ошибок — что стоит добавить в промпт."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT dislike_reason, error_class, COUNT(*) as cnt, GROUP_CONCAT(DISTINCT user_comment)
               FROM feedback WHERE rating = 'dislike'
               GROUP BY dislike_reason"""
        ).fetchall()
        suggestions = []
        for reason, err_class, cnt, comments in rows:
            if reason == "wrong_understanding":
                suggestions.append({
                    "key": "synonyms",
                    "reason": f"Частые нераспознанные запросы ({cnt}), добавить синонимы",
                    "feedback_count": cnt,
                })
            elif reason == "bad_questions":
                suggestions.append({
                    "key": "clarification_templates",
                    "reason": f"Плохие уточняющие вопросы ({cnt}), улучшить шаблоны",
                    "feedback_count": cnt,
                })
            elif reason == "wrong_parts":
                suggestions.append({
                    "key": "search_logic",
                    "reason": f"Не те запчасти ({cnt}) — защищённый ключ, только ручное исправление",
                    "feedback_count": cnt,
                })
        return suggestions
    finally:
        conn.close()


async def get_clarification_suggestions() -> list[dict]:
    """Какие уточняющие вопросы приводят к повторным попыткам."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT dc.attempt_count, dc.slots_json, dc.all_messages_json
               FROM dialogue_cycles dc
               WHERE dc.attempt_count >= 2
               ORDER BY dc.created_at DESC LIMIT 50"""
        ).fetchall()
        return [
            {"attempt_count": r[0], "slots": r[1], "messages": r[2]}
            for r in rows
        ]
    finally:
        conn.close()


async def build_quality_report(days: int = 30) -> dict:
    """Сводный отчёт по качеству за период."""
    conn = _get_conn()
    try:
        cutoff = f"-{days} days"
        total = conn.execute(
            "SELECT COUNT(*) FROM dialogue_cycles WHERE created_at >= datetime('now', ?)",
            (cutoff,),
        ).fetchone()[0]
        with_feedback = conn.execute(
            """SELECT COUNT(DISTINCT dc.id) FROM dialogue_cycles dc
               JOIN feedback f ON f.cycle_id = dc.id
               WHERE dc.created_at >= datetime('now', ?)""",
            (cutoff,),
        ).fetchone()[0]
        likes = conn.execute(
            """SELECT COUNT(*) FROM feedback
               WHERE rating = 'like' AND created_at >= datetime('now', ?)""",
            (cutoff,),
        ).fetchone()[0]
        dislikes = conn.execute(
            """SELECT COUNT(*) FROM feedback
               WHERE rating = 'dislike' AND created_at >= datetime('now', ?)""",
            (cutoff,),
        ).fetchone()[0]
        success = conn.execute(
            "SELECT COUNT(*) FROM dialogue_cycles WHERE final_status = 'success' AND created_at >= datetime('now', ?)",
            (cutoff,),
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM dialogue_cycles WHERE final_status = 'failed' AND created_at >= datetime('now', ?)",
            (cutoff,),
        ).fetchone()[0]
        top_reasons = conn.execute(
            """SELECT dislike_reason, COUNT(*) FROM feedback
               WHERE rating = 'dislike' AND created_at >= datetime('now', ?)
               GROUP BY dislike_reason ORDER BY 2 DESC LIMIT 5""",
            (cutoff,),
        ).fetchall()
        return {
            "days": days,
            "total_cycles": total,
            "cycles_with_feedback": with_feedback,
            "likes": likes,
            "dislikes": dislikes,
            "success_count": success,
            "failed_count": failed,
            "success_rate": round(100 * success / total, 1) if total else 0,
            "feedback_rate": round(100 * with_feedback / total, 1) if total else 0,
            "top_dislike_reasons": [{"reason": r[0], "count": r[1]} for r in top_reasons],
        }
    finally:
        conn.close()
