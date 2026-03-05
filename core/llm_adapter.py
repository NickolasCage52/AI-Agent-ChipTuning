"""Gemini-адаптер с таймаутами и ретраями (async). Поддерживает google-genai и google-generativeai."""
from __future__ import annotations

import asyncio
import logging
import os

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Не retry при 4xx/429 — retry бесполезен
def _is_fatal_api_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True
    s = str(exc).lower()
    return (
        "403" in s or "404" in s or "429" in s
        or "permission_denied" in s or "not_found" in s or "resource_exhausted" in s
        or "leaked" in s
    )

# gemini-1.5-flash даёт 404 в v1beta — используем gemini-2.0-flash
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-pro"]


def _call_google_genai(prompt: str, system: str, model: str, timeout_ms: int) -> str:
    """Новый SDK: google-genai. Использует только GEMINI_API_KEY."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY не установлен в .env")
    # SDK берёт GOOGLE_API_KEY если оба заданы — временно убираем, чтобы использовался GEMINI_API_KEY
    saved_google = os.environ.pop("GOOGLE_API_KEY", None)
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout_ms),
        )
        config = types.GenerateContentConfig(system_instruction=system if system else None)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        return response.text if hasattr(response, "text") and response.text else str(response)
    finally:
        if saved_google is not None:
            os.environ["GOOGLE_API_KEY"] = saved_google


def _call_legacy_genai(prompt: str, system: str, model: str, timeout: int) -> str:
    """Легаси SDK: google-generativeai."""
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY не установлен в .env")
    genai.configure(api_key=api_key)
    gm = genai.GenerativeModel(model_name=model, system_instruction=system or None)
    response = gm.generate_content(prompt)
    return response.text if response.text else str(response)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=3),
    retry=retry_if_exception(lambda e: isinstance(e, Exception) and not _is_fatal_api_error(e)),
)
async def call_gemini(prompt: str, system: str = "", timeout: int = 18) -> str:
    """Вызов Gemini (async). Пробует google-genai, затем google-generativeai."""
    models_to_try = [MODEL_NAME] + [m for m in FALLBACK_MODELS if m != MODEL_NAME]
    last_error = None

    for model in models_to_try:
        try:
            # 1. Пробуем новый SDK (google-genai)
            try:
                def _task() -> str:
                    return _call_google_genai(prompt, system, model, timeout * 1000)

                loop = asyncio.get_event_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, _task),
                    timeout=timeout + 5,
                )
            except ImportError:
                pass

            # 2. Fallback на google-generativeai
            def _legacy_task() -> str:
                return _call_legacy_genai(prompt, system, model, timeout)

            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, _legacy_task),
                timeout=timeout + 5,
            )
        except Exception as e:
            last_error = e
            err_msg = str(e) or f"{type(e).__name__}"
            logger.warning("Gemini model %s failed: %s", model, err_msg)
            if _is_fatal_api_error(e):
                break
            continue

    raise last_error or RuntimeError("Gemini API недоступен")
