from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.agent import handle_agent_message
from app.logging_config import setup_logging
from app.schemas import AgentMessageIn, AgentMessageOut


setup_logging()
app = FastAPI(title="autoshop agent-orchestrator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True}

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    rid = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = rid
    response = await call_next(request)
    response.headers["X-Request-Id"] = rid
    return response


@app.post("/api/agent/message", response_model=AgentMessageOut)
async def agent_message(payload: AgentMessageIn, request: Request) -> AgentMessageOut:
    return await handle_agent_message(payload, request_id=getattr(request.state, "request_id", None))


@app.post("/api/telegram/webhook", response_model=AgentMessageOut)
async def telegram_webhook(payload: dict, request: Request) -> AgentMessageOut:
    # MVP: accept Telegram-like payload: {message: {text, from:{id, first_name}, chat:{id}}}
    msg = (payload.get("message") or {}).get("text") or ""
    user = (payload.get("message") or {}).get("from") or {}
    tg_id = user.get("id")
    name = user.get("first_name") or user.get("username")
    agent_in = AgentMessageIn(channel="telegram", lead_id=None, message=msg, client_contact={"tg_id": tg_id, "name": name})
    return await handle_agent_message(agent_in, request_id=getattr(request.state, "request_id", None))

