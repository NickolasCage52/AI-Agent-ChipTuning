"""LLM-адаптер: только Ollama (async, httpx, tenacity)."""
from __future__ import annotations

import logging
import os

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))


async def health_check() -> dict:
    """Проверить доступность Ollama."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            model_available = any(OLLAMA_MODEL.split(":")[0] in m for m in models)
            return {
                "available": True,
                "model_available": model_available,
                "model_loaded": model_available,
                "models": models,
                "configured_model": OLLAMA_MODEL,
            }
    except Exception as e:
        return {"available": False, "error": str(e), "configured_model": OLLAMA_MODEL}


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=3))
async def call_llm(prompt: str, system: str = "", timeout: int | None = None) -> str:
    """Единственная точка вызова LLM — только Ollama."""
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    t = max(timeout or OLLAMA_TIMEOUT, 90)

    try:
        async with httpx.AsyncClient(timeout=t) as client:
            r = await client.post(
                f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 1024,
                    },
                },
            )
            r.raise_for_status()
            result = r.json().get("response", "")
            logger.debug("Ollama response length: %d", len(result))
            return result
    except Exception as e:
        logger.error("Ollama error: %s", e)
        raise
