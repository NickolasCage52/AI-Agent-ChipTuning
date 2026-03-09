"""LLM-адаптер: только Ollama (sync)."""
from __future__ import annotations

import logging
import os
import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

_PII_PATTERNS = [
    (r"\b\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b", "[PHONE]"),
    (r"\b8[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b", "[PHONE]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
]


def mask_pii(text: str) -> str:
    """Маскировать PII в тексте."""
    if not text:
        return text
    for pattern, replacement in _PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def call_llm(prompt: str, system: str = "", timeout: int | None = None) -> str:
    """Sync вызов Ollama."""
    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    t = timeout if timeout is not None else OLLAMA_TIMEOUT

    with httpx.Client(timeout=t) as client:
        r = client.post(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 1024},
            },
        )
        r.raise_for_status()
        result = r.json().get("response", "")
        logger.debug("Ollama response length: %d", len(result))
        return result


