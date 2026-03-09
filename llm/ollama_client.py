"""Ollama API client с health check и ретраями."""
from __future__ import annotations

import logging
import os
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


async def health_check() -> dict:
    """Проверить доступность Ollama и модели."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE.rstrip('/')}/api/tags")
            r.raise_for_status()
            data = r.json()
            models = [m["name"] for m in data.get("models", [])]
            model_base = OLLAMA_MODEL.split(":")[0]
            available = (
                OLLAMA_MODEL in models
                or any(model_base in m for m in models)
            )
            return {
                "available": True,
                "model_loaded": available,
                "models": models,
                "configured_model": OLLAMA_MODEL,
            }
    except Exception as e:
        return {"available": False, "error": str(e), "configured_model": OLLAMA_MODEL}


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
async def generate(
    prompt: str,
    system: str = "",
    temperature: float = 0.1,
    timeout: int = 45,
) -> str:
    """Вызов Ollama с таймаутом и ретраями."""
    start = time.time()
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": temperature, "top_p": 0.9},
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{OLLAMA_BASE.rstrip('/')}/api/generate", json=payload)
        r.raise_for_status()
        result = r.json().get("response", "")
        latency = time.time() - start
        logger.debug("Ollama latency: %.1fs, len: %d", latency, len(result))
        return result.strip()
