"""Применить новую версию промпта или откатить."""
from __future__ import annotations

import argparse
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in __import__("sys").path:
    __import__("sys").path.insert(0, _root)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reason", type=str, help="Причина изменения (для create_new_version)")
    ap.add_argument("--rollback", type=str, help="Версия для отката (например 1.0.0)")
    args = ap.parse_args()

    from llm.prompt_manager import get_prompt_manager
    pm = get_prompt_manager()

    if args.rollback:
        pm.rollback_to_version(args.rollback)
        print(f"Rolled back to version {args.rollback}")
        return

    if args.reason:
        ver = pm.create_new_version({}, source="manual", reason=args.reason)
        print(f"Created new version: {ver}")
        return

    print("Usage: --reason 'описание' для новой версии, или --rollback 1.0.0 для отката")


if __name__ == "__main__":
    main()
