"""Архивация старых feedback (старше N дней)."""
from __future__ import annotations

import argparse
import asyncio
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in __import__("sys").path:
    __import__("sys").path.insert(0, _root)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()

    async def run():
        from storage.feedback_repository import archive_old_feedback
        n = await archive_old_feedback(older_than_days=args.days)
        print(f"Archived {n} feedback records older than {args.days} days")

    asyncio.run(run())


if __name__ == "__main__":
    main()
