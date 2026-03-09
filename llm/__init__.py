"""LLM слой: только Ollama."""
from .router import generate, health_check

__all__ = ["generate", "health_check"]
