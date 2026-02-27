"""LLM-адаптер (Gemini) с таймаутами и ретраями."""
from __future__ import annotations

from app.llm.gemini_adapter import call_gemini

__all__ = ["call_gemini"]
