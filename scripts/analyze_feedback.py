"""Анализ feedback и рекомендации."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in __import__("sys").path:
    __import__("sys").path.insert(0, _root)


def _run(coro):
    return asyncio.run(coro)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--export-csv", action="store_true")
    ap.add_argument("--suggest-synonyms", action="store_true")
    ap.add_argument("--suggest-prompt-improvements", action="store_true")
    ap.add_argument("--good-cases", action="store_true")
    ap.add_argument("--bad-cases", action="store_true")
    args = ap.parse_args()

    if args.export_csv:
        from storage.feedback_repository import export_dataset
        os.makedirs("reports", exist_ok=True)
        path = os.path.join("reports", f"feedback_{datetime.now().strftime('%Y%m%d')}.csv")
        _run(export_dataset(path, days=args.days))
        print(f"Exported: {path}")
        return

    if args.suggest_synonyms:
        from storage.improvement_advisor import get_synonym_suggestions
        rows = _run(get_synonym_suggestions())
        print("Слова для добавления в синонимы (из неудачных запросов):")
        for r in rows[:20]:
            print(f"  {r['word']} (встреч: {r['count']})")
        return

    if args.suggest_prompt_improvements:
        from storage.improvement_advisor import get_prompt_improvement_suggestions
        rows = _run(get_prompt_improvement_suggestions())
        print("Рекомендации по улучшению промпта:")
        for r in rows:
            print(f"  {r['key']}: {r['reason']}")
        return

    if args.good_cases:
        from storage.feedback_repository import get_good_examples
        rows = _run(get_good_examples(limit=20))
        print("Хорошие примеры для few-shot:")
        for r in rows:
            print(f"  cycle={r['cycle_id'][:8]} category={r.get('like_category')}")
        return

    if args.bad_cases:
        from storage.feedback_repository import get_bad_examples
        rows = _run(get_bad_examples(limit=20))
        print("Плохие кейсы для разбора:")
        for r in rows:
            print(f"  cycle={r['cycle_id'][:8]} reason={r['dislike_reason']} comment={r.get('user_comment', '')[:60]}")
        return

    from storage.improvement_advisor import build_quality_report
    data = _run(build_quality_report(args.days))
    os.makedirs("reports", exist_ok=True)
    path = os.path.join("reports", f"feedback_{datetime.now().strftime('%Y%m%d')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    main()
