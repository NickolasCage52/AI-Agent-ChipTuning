from __future__ import annotations

import uuid
from typing import Any

import httpx
from fastapi import Body, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.logging_config import setup_logging
from app.settings import settings
from app.telegram import parse_update
from app.widget_assets import widget_html, widget_js


setup_logging()
app = FastAPI(title="autoshop channel-gateway", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


@app.get("/health")
def health() -> dict:
    return {"ok": True}


async def _core_post(path: str, request_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = settings.core_api_url.rstrip("/") + path
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers={"X-Request-Id": request_id})
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"core-api error: {r.status_code} {r.text}")
    return r.json()


async def _agent_post(request_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = settings.agent_url.rstrip("/") + "/api/agent/message"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload, headers={"X-Request-Id": request_id})
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"agent error: {r.status_code} {r.text}")
    return r.json()


async def _append_event(request_id: str, lead_id: str, event_type: str, payload: dict[str, Any]) -> None:
    await _core_post("/internal/tools/append_event", request_id, {"lead_id": lead_id, "event_type": event_type, "payload": payload})


@app.post("/webhooks/telegram/{secret}")
async def telegram_webhook(secret: str, request: Request, update: dict = Body(...)) -> dict:
    if secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=404, detail="Not found")
    msg = parse_update(update)
    if not msg:
        return {"ok": True}

    rid = request.state.request_id
    lead_id = None
    # try to find active lead for tg user
    try:
        resp = await _core_post("/internal/tools/find_active_lead_by_tg", rid, {"tg_id": msg.tg_id})
        lead_id = resp.get("lead_id")
    except Exception:
        lead_id = None

    agent_payload = {
        "channel": "tg",
        "lead_id": lead_id,
        "message": msg.text,
        "client_contact": {"tg_id": msg.tg_id, "name": msg.name},
    }
    agent_resp = await _agent_post(rid, agent_payload)
    lead_id = agent_resp.get("lead_id")

    if lead_id:
        await _append_event(rid, lead_id, "telegram.update_received", {"text": msg.text, "tg_id": msg.tg_id, "chat_id": msg.chat_id})

    # reply via Telegram API
    if settings.telegram_bot_token:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json={"chat_id": msg.chat_id, "text": agent_resp.get("answer", "—")})
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"telegram sendMessage failed: {r.status_code} {r.text}")

    if lead_id:
        await _append_event(rid, lead_id, "telegram.reply_sent", {"text_preview": (agent_resp.get("answer") or "")[:200], "chat_id": msg.chat_id})

    return {"ok": True, "lead_id": lead_id}


@app.get("/telegram/set-webhook")
async def telegram_set_webhook(request: Request) -> dict:
    if not settings.telegram_bot_token or not settings.public_base_url:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN and PUBLIC_BASE_URL are required")
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/setWebhook"
    hook = settings.public_base_url.rstrip("/") + f"/webhooks/telegram/{settings.telegram_webhook_secret}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json={"url": hook})
    return {"webhook_url": hook, "telegram_response": r.json()}


@app.get("/widget.js")
async def get_widget_js(request: Request) -> Response:
    base = settings.public_base_url or "http://localhost:8004"
    return Response(content=widget_js(base), media_type="application/javascript")


@app.get("/widget")
async def get_widget(request: Request) -> Response:
    base = settings.public_base_url or "http://localhost:8004"
    return Response(content=widget_html(base), media_type="text/html; charset=utf-8")


@app.post("/api/widget/session")
async def widget_create_session(request: Request, metadata: dict | None = Body(default=None)) -> dict:
    rid = request.state.request_id
    resp = await _core_post("/internal/tools/create_widget_session", rid, {"channel": "widget", "metadata": metadata or {}})
    # resp: {session_id, lead_id}
    await _append_event(rid, resp["lead_id"], "widget.session_created", {"session_id": resp["session_id"], "metadata": metadata or {}})
    return resp


@app.post("/api/widget/message")
async def widget_message(request: Request, payload: dict = Body(...)) -> dict:
    rid = request.state.request_id
    session_id = payload.get("session_id")
    message = (payload.get("message") or "").strip()
    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message are required")
    sess = await _core_post("/internal/tools/get_widget_session", rid, {"session_id": session_id})
    lead_id = sess["lead_id"]
    await _append_event(rid, lead_id, "widget.message_received", {"session_id": session_id, "message": message})
    agent_resp = await _agent_post(rid, {"channel": "widget", "lead_id": lead_id, "message": message})
    await _append_event(rid, lead_id, "widget.reply_sent", {"session_id": session_id, "text_preview": (agent_resp.get("answer") or "")[:200]})
    return agent_resp

