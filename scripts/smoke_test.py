#!/usr/bin/env python3
"""Smoke-test для проверки 4 ключевых сценариев Parts Assistant /api/chat."""

import json
import sys

import requests

BASE_URL = "http://localhost:8000"

SCENARIOS = [
    {
        "name": "Колодки на Camry 50",
        "payload": {
            "message": "Нужны колодки",
            "car_context": {"brand": "Toyota", "model": "Camry", "year": 2018},
        },
        "expect_intent": "parts_search",
        "expect_part": "колодки",
    },
    {
        "name": "Фильтр масляный Kia Rio 2017",
        "payload": {
            "message": "Ищу фильтр масляный",
            "car_context": {"brand": "Kia", "model": "Rio", "year": 2017},
        },
        "expect_intent": "parts_search",
    },
    {
        "name": "Комплект ГРМ аналоги",
        "payload": {
            "message": "Нужен комплект ГРМ, подберите аналоги",
            "car_context": {"brand": "Volkswagen", "model": "Polo", "year": 2015},
        },
        "expect_intent": "parts_search",
    },
    {
        "name": "Поиск по артикулу",
        "payload": {
            "message": "Артикул 04465-33480, покажи варианты и что быстрее",
            "car_context": {},
        },
        "expect_intent": "parts_search",
    },
]


def run() -> None:
    passed = 0
    failed = 0

    for s in SCENARIOS:
        print(f"\n{'='*50}")
        print(f"Сценарий: {s['name']}")
        try:
            r = requests.post(f"{BASE_URL}/api/chat", json=s["payload"], timeout=20)
            r.raise_for_status()
            data = r.json()

            questions_count = len(data.get("questions", []))
            has_bundles = bool(data.get("bundles"))
            next_step = data.get("next_step", "")

            print(f"  OK Ответ получен")
            print(f"  Резюме: {(data.get('summary', '') or '')[:80]}")
            print(f"  Вопросов: {questions_count} (макс 2: {'OK' if questions_count <= 2 else 'FAIL'})")
            print(f"  Варианты: {'есть' if has_bundles else 'нет'}")
            print(f"  Next step: {next_step}")

            if questions_count > 2:
                print(f"  FAIL: Слишком много вопросов ({questions_count})")
                failed += 1
            else:
                passed += 1

        except requests.RequestException as e:
            print(f"  FAIL: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    err = e.response.json()
                    print(f"  Detail: {json.dumps(err, ensure_ascii=False)[:200]}")
                except Exception:
                    print(f"  Body: {e.response.text[:200]}")
            failed += 1
        except Exception as e:
            print(f"  FAIL: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Результат: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run()
