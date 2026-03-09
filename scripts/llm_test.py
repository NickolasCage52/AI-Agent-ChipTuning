#!/usr/bin/env python3
"""Тест LLM: Ollama и извлечение сущностей."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


async def test_ollama():
    """Проверить Ollama напрямую."""
    try:
        import httpx
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        r = await httpx.AsyncClient(timeout=30).post(
            f"{base.rstrip('/')}/api/generate",
            json={
                "model": model,
                "prompt": "Ответь одним словом: работаешь?",
                "stream": False,
            },
        )
        resp = r.json().get("response", "нет ответа")
        print(f"✅ Ollama: {resp[:80]}")
        return True
    except Exception as e:
        print(f"❌ Ollama недоступна: {e}")
        return False


async def test_router():
    """Проверить router (только Ollama)."""
    try:
        from llm import generate
        start = __import__("time").time()
        out = await generate("Скажи 'ок' одним словом", system="Ты помощник.", timeout=15)
        latency = __import__("time").time() - start
        print(f"✅ Router: ответ за {latency:.1f}s, len={len(out)}")
        return True
    except Exception as e:
        print(f"❌ Router: {e}")
        return False


async def test_entity_extraction():
    """Проверить извлечение сущностей."""
    from core.intent import extract_intent_and_slots
    tests = [
        "Нужны передние колодки на Camry 50",
        "Kia Rio 2017, масляный фильтр",
        "OEM 90915-YZZF2",
    ]
    for q in tests:
        print(f"\nЗапрос: {q}")
        try:
            r = await extract_intent_and_slots(q)
            print(f"  intent: {r.get('intent')}")
            print(f"  part_type: {r.get('part_type')}")
            print(f"  car: {r.get('car_context')}")
            print(f"  summary: {r.get('summary', '')[:60]}...")
        except Exception as e:
            print(f"  Ошибка: {e}")


async def main():
    print("=== LLM TEST ===\n")
    await test_ollama()
    await test_router()
    print("\n=== Entity extraction ===")
    await test_entity_extraction()


if __name__ == "__main__":
    asyncio.run(main())
