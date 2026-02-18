from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, agent_proxy, agent_runs, catalog, documents, estimates, events, internal_tools, leads, parts, suppliers
from app.logging_config import setup_logging
from app.seed import ensure_seed


setup_logging()
app = FastAPI(title="autoshop core-api", version="0.1.0")

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

app.include_router(leads.router)
app.include_router(catalog.router)
app.include_router(suppliers.router)
app.include_router(parts.router)
app.include_router(estimates.router)
app.include_router(agent_runs.router)
app.include_router(agent_proxy.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(internal_tools.router)
app.include_router(events.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.on_event("startup")
async def _startup_seed() -> None:
    await ensure_seed()

