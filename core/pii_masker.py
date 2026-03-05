"""PII-маскирование для запросов и логов."""
from __future__ import annotations

import re

_PATTERNS = [
    (r"\b\+7[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b", "[PHONE]"),
    (r"\b8[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\b", "[PHONE]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
]


def mask_pii(text: str) -> str:
    if not text:
        return text
    for pattern, replacement in _PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text
