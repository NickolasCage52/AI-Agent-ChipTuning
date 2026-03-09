"""Генерация отчётов по feedback."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys_path = _root not in __import__("sys").path and _root or None
if sys_path:
    __import__("sys").path.insert(0, _root)

from storage.feedback_repository import export_dataset
from storage.improvement_advisor import build_quality_report


def _run(coro):
    return asyncio.run(coro)


def report_quality(days: int) -> dict:
    return _run(build_quality_report(days))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--export-csv", action="store_true")
    ap.add_argument("--output", default="reports")
    ap.add_argument("--report", choices=["quality", "errors", "synonyms", "prompt-hints", "bad-cases", "good-cases"])
    args = ap.parse_args()

    os.makedirs(args.output, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d")
    report_path = os.path.join(args.output, f"feedback_{ts}.json")

    if args.export_csv:
        csv_path = os.path.join(args.output, f"feedback_{ts}.csv")
        _run(export_dataset(csv_path, days=args.days))
        print(f"CSV saved: {csv_path}")
        return

    if args.report == "quality" or not args.report:
        data = report_quality(args.days)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"\nReport saved: {report_path}")
        return

    if args.report == "errors":
        data = report_quality(args.days)
        print("Топ причин дизлайков:")
        for r in data.get("top_dislike_reasons", []):
            print(f"  {r['reason']}: {r['count']}")
        return

    if args.report in ("synonyms", "prompt-hints", "bad-cases", "good-cases"):
        import asyncio
        from storage.feedback_repository import get_bad_examples, get_good_examples
        from storage.improvement_advisor import get_synonym_suggestions, get_prompt_improvement_suggestions
        if args.report == "synonyms":
            rows = _run(get_synonym_suggestions())
            print("Рекомендуемые синонимы (слова из неудачных запросов):")
            for r in rows[:15]:
                print(f"  {r['word']}: {r['count']}")
        elif args.report == "prompt-hints":
            rows = _run(get_prompt_improvement_suggestions())
            print("Рекомендации по промпту:")
            for r in rows:
                print(f"  {r['key']}: {r['reason']}")
        elif args.report == "bad-cases":
            rows = _run(get_bad_examples(limit=10))
            print("Худшие кейсы:")
            for r in rows:
                print(f"  cycle={r['cycle_id'][:8]} reason={r['dislike_reason']} comment={r.get('user_comment', '')[:50]}")
        elif args.report == "good-cases":
            rows = _run(get_good_examples(limit=10))
            print("Лучшие кейсы:")
            for r in rows:
                print(f"  cycle={r['cycle_id'][:8]} category={r.get('like_category', '')}")
        return


if __name__ == "__main__":
    main()
