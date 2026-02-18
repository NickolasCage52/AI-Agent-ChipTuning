from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.schemas import ToolCallRecord
from app.settings import settings


class ToolLogger:
    def __init__(self, request_id: str | None) -> None:
        self.request_id = request_id
        self.records: list[dict[str, Any]] = []

    def add(self, rec: ToolCallRecord) -> None:
        self.records.append(rec.model_dump(mode="json"))


class CoreApiTools:
    def __init__(self, logger: ToolLogger) -> None:
        self.logger = logger
        self.base = settings.core_api_url.rstrip("/")

    async def _request(self, tool_name: str, path: str, *, json: Any | None = None, timeout_s: int = 30) -> Any:
        import time

        url = f"{self.base}{path}"
        started = time.perf_counter()
        record = ToolCallRecord(tool_name=tool_name, args=json or {}, duration_ms=0, request_id=self.logger.request_id)
        data: Any | None = None
        try:
            headers = {}
            if self.logger.request_id:
                headers["X-Request-Id"] = self.logger.request_id
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                r = await client.post(url, json=json, headers=headers)
            if r.status_code >= 400:
                record.error = f"HTTP {r.status_code}: {r.text}"
                raise RuntimeError(record.error)
            data = r.json()
            # keep summary small/stable
            if isinstance(data, dict):
                record.result_summary = {k: data.get(k) for k in list(data.keys())[:8]}
            else:
                record.result_summary = {"type": type(data).__name__}
            return data
        except Exception as e:
            record.error = str(e)
            raise
        finally:
            record.duration_ms = int((time.perf_counter() - started) * 1000)
            self.logger.add(record)
        return data

    # REQUIRED TOOLS (agent calls only these; all are HTTP to core-api)

    async def create_lead(self, channel: str, contact: dict, problem_text: str, car_hint: dict) -> Any:
        return await self._request("create_lead", "/internal/tools/create_lead", json={"channel": channel, "contact": contact, "problem_text": problem_text, "car_hint": car_hint})

    async def update_lead(self, lead_id: uuid.UUID, fields: dict) -> Any:
        return await self._request("update_lead", "/internal/tools/update_lead", json={"lead_id": str(lead_id), "fields": fields})

    async def get_catalog_jobs(self, query: str, car_context: dict | None = None) -> Any:
        return await self._request("get_catalog_jobs", "/internal/tools/get_catalog_jobs", json={"query": query, "car_context": car_context or {}})

    async def build_estimate(self, lead_id: uuid.UUID, jobs: list[dict], pricing_rules: list[dict], parts: list[dict]) -> Any:
        return await self._request("build_estimate", "/internal/tools/build_estimate", json={"lead_id": str(lead_id), "jobs": jobs, "pricing_rules": pricing_rules, "parts": parts})

    async def import_supplier_price(self, supplier_id: uuid.UUID, file: dict) -> Any:
        """
        Supports:
        - file={"filename": "...", "content_base64": "..."}  -> will POST multipart to core-api
        """
        filename = file.get("filename") or "price.csv"
        b64 = file.get("content_base64")
        if not b64:
            return {"note": "No content_base64 provided; use UI / admin import for MVP", "supplier_id": str(supplier_id)}

        return await self._request(
            "import_supplier_price",
            "/internal/tools/import_supplier_price",
            json={"supplier_id": str(supplier_id), "filename": filename, "content_base64": b64},
            timeout_s=60,
        )

    async def search_parts(self, query: str, car_context: dict | None = None) -> Any:
        return await self._request("search_parts", "/internal/tools/search_parts", json={"query": query, "car_context": car_context or {}})

    async def compare_supplier_offers(self, part_key: dict, constraints: dict | None = None) -> Any:
        return await self._request("compare_supplier_offers", "/internal/tools/compare_supplier_offers", json={"part_key": part_key, "constraints": constraints or {}})

    async def save_estimate(self, lead_id: uuid.UUID, draft_estimate: dict, ui: dict | None = None) -> Any:
        return await self._request(
            "save_estimate",
            "/internal/tools/save_estimate",
            json={"lead_id": str(lead_id), "estimate_id": draft_estimate.get("id"), "ui": ui},
        )

    async def request_approval(self, lead_id: uuid.UUID, draft_estimate: dict) -> Any:
        return await self._request("request_approval", "/internal/tools/request_approval", json={"lead_id": str(lead_id), "estimate_id": draft_estimate.get("id")})

    async def log_agent_run(self, lead_id: uuid.UUID, message: str, tool_calls: list[dict], outcome: dict) -> Any:
        return await self._request(
            "log_agent_run",
            "/internal/tools/log_agent_run",
            json={
                "lead_id": str(lead_id),
                "user_message": message,
                "agent_plan": outcome.get("agent_plan"),
                "tool_calls": tool_calls,
                "final_answer": outcome.get("final_answer"),
            },
        )

    async def append_event(self, lead_id: uuid.UUID, event_type: str, payload: dict | None) -> Any:
        # Do not record append_event as a "tool call" to avoid recursive noise; best-effort.
        url = f"{self.base}/internal/tools/append_event"
        headers = {}
        if self.logger.request_id:
            headers["X-Request-Id"] = self.logger.request_id
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={"lead_id": str(lead_id), "event_type": event_type, "payload": payload}, headers=headers)
        return r.json() if r.content else {"ok": r.status_code < 400}

