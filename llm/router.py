"""Роутер LLM: только Ollama."""
from __future__ import annotations

import logging

from core.llm_adapter import call_llm, health_check

logger = logging.getLogger(__name__)


async def generate(prompt: str, system: str = "", timeout: int = 45) -> str:
    """Вызов LLM — только Ollama."""
    return await call_llm(prompt, system, timeout=timeout)


__all__ = ["generate", "health_check"]
