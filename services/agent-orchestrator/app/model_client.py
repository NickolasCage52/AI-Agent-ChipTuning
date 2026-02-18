from __future__ import annotations

from typing import Any

import httpx

from app.schemas import NluResult
from app.settings import settings


SYSTEM_NLU_PROMPT = """You are an on-prem service desk NLU module for an автосервис.
Return ONLY valid JSON object: {"intent": "...", "slots": {...}}.
Intents: maintenance, symptom, part.
Slots (optional): brand, model, year, mileage, vin, part_query.
If unsure, set intent="unknown".
"""


class ModelClient:
    def __init__(self) -> None:
        self.base = settings.model_server_url.rstrip("/")

    async def nlu(self, message: str) -> NluResult:
        url = f"{self.base}/v1/chat/completions"
        payload = {
            "model": "mvp",
            "messages": [
                {"role": "system", "content": SYSTEM_NLU_PROMPT},
                {"role": "user", "content": message},
            ],
            "temperature": 0.0,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
        if r.status_code >= 400:
            raise RuntimeError(f"model-server HTTP {r.status_code}: {r.text}")
        data: dict[str, Any] = r.json()
        # expected OpenAI-like response
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        try:
            return NluResult.model_validate_json(content)
        except Exception:
            # fallback: accept direct format
            return NluResult.model_validate(data.get("nlu", {"intent": "unknown", "slots": {}}))

