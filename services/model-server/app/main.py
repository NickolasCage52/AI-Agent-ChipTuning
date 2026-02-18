from __future__ import annotations

import json
import re
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException

from app.settings import settings
from app.logging_config import setup_logging


setup_logging()
app = FastAPI(title="autoshop model-server (stub)", version="0.1.0")


def _stub_nlu(text: str) -> dict[str, Any]:
    t = (text or "").lower()
    intent = "unknown"
    if any(x in t for x in ["то", "техобслуж", "замена масла", "масло"]):
        intent = "maintenance"
    elif any(x in t for x in ["стук", "скрип", "вибра", "шум", "поворот"]):
        intent = "symptom"
    elif any(x in t for x in ["колодк", "запчаст", "нужн", "тормоз", "фильтр"]):
        intent = "part"

    slots: dict[str, Any] = {}
    year = re.search(r"\b(19[8-9]\d|20[0-2]\d)\b", t)
    if year:
        slots["year"] = int(year.group(1))
    mil = re.search(r"\b(\d{1,3})(\s?)(к|k)\b", t)
    if mil:
        slots["mileage"] = int(mil.group(1)) * 1000
    if "kia" in t:
        slots["brand"] = "Kia"
    if "rio" in t:
        slots["model"] = "Rio"
    if "camry" in t:
        slots["brand"] = "Toyota"
        slots["model"] = "Camry 50" if "50" in t else "Camry"
    if intent == "part":
        slots["part_query"] = text

    return {"intent": intent, "slots": slots}


@app.get("/health")
def health() -> dict:
    return {"ok": True, "mode": "stub" if not settings.ollama_url else "ollama_proxy"}


@app.post("/v1/chat/completions")
async def chat_completions(payload: dict) -> dict:
    """
    Minimal OpenAI-compatible endpoint for agent's NLU/formatting.
    MVP: returns JSON in choices[0].message.content.
    """
    # optional: proxy to Ollama if configured
    if settings.ollama_url and settings.ollama_model:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    f"{settings.ollama_url.rstrip('/')}/api/chat",
                    json={
                        "model": settings.ollama_model,
                        "messages": payload.get("messages", []),
                        "stream": False,
                        "options": {"temperature": payload.get("temperature", 0.0)},
                    },
                )
            if r.status_code >= 400:
                raise HTTPException(status_code=502, detail=f"Ollama error: {r.status_code} {r.text}")
            data = r.json()
            content = (data.get("message") or {}).get("content") or "{}"
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Ollama unavailable: {e}") from e
    else:
        # stub: last user message
        msgs = payload.get("messages") or []
        user_text = ""
        for m in reversed(msgs):
            if m.get("role") == "user":
                user_text = m.get("content") or ""
                break
        content = json.dumps(_stub_nlu(user_text), ensure_ascii=False)

    return {
        "id": "chatcmpl-mvp",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    }

