import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_lead_appends_lead_created_event():
    # httpx 0.27.x ASGITransport doesn't support "lifespan" kwarg.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/internal/tools/create_lead",
            json={
                "channel": "web",
                "contact": {"name": "Test", "phone": "+70000000000"},
                "problem_text": "Нужно ТО",
                "car_hint": {"brand": "Kia", "model": "Rio", "year": 2017, "mileage": 120000},
            },
            headers={"X-Request-Id": "req-test-1"},
        )
        assert r.status_code == 200
        lead_id = r.json()["lead"]["id"]

        ev = await client.get(f"/api/leads/{lead_id}/events")
        assert ev.status_code == 200
        events = ev.json()
        assert any(e["event_type"] == "lead.created" for e in events)
        assert any(e["request_id"] == "req-test-1" for e in events)


@pytest.mark.asyncio
async def test_estimate_draft_emits_events_and_requires_approval():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/internal/tools/create_lead",
            json={"channel": "web", "contact": {}, "problem_text": "Нужно ТО", "car_hint": {"brand": "Kia", "model": "Rio", "year": 2017, "mileage": 120000}},
        )
        lead_id = r.json()["lead"]["id"]

        est = await client.post("/internal/tools/build_estimate", json={"lead_id": lead_id, "jobs": [], "pricing_rules": [], "parts": []})
        assert est.status_code == 200
        assert est.json()["estimate"]["requires_approval"] is True

        ev = await client.get(f"/api/leads/{lead_id}/events")
        events = ev.json()
        assert any(e["event_type"] == "estimate.draft_created" for e in events)
        assert any(e["event_type"] == "estimate.saved" for e in events)
