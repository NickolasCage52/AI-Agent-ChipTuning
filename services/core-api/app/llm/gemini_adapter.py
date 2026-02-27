from __future__ import annotations

import logging
import os
import re
import time
from typing import Optional

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
    (r"\b(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b", "[PHONE]"),
    (r"\b[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+(?:\s[А-ЯЁ][а-яё]+)?\b", "[NAME]"),
]


def mask_pii(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in PII_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text


def _get_api_key() -> Optional[str]:
    return os.environ.get("GEMINI_API_KEY")


def _get_model() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")


def _create_client(timeout_ms: int = 15000) -> genai.Client:
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_ms),
    )


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def call_gemini(prompt: str, system: str = "", timeout: int = 15) -> str:
    client = _create_client(timeout_ms=timeout * 1000)
    model_name = _get_model()
    masked_prompt = mask_pii(prompt)

    config = types.GenerateContentConfig(
        system_instruction=system if system else None,
    )

    start = time.time()
    response = client.models.generate_content(
        model=model_name,
        contents=masked_prompt,
        config=config,
    )
    elapsed = time.time() - start
    logger.info("Gemini response in %.2fs | model=%s", elapsed, model_name)

    return response.text if hasattr(response, "text") and response.text else str(response)
