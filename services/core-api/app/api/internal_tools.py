from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.repositories.agent_runs import AgentRunRepository
from app.repositories.catalog import CatalogRepository
from app.repositories.estimates import EstimateRepository
from app.repositories.leads import LeadRepository
from app.repositories.parts import PartsRepository
from app.repositories.suppliers import SupplierRepository
from app.repositories.events import LeadEventRepository
from app.repositories.widget_sessions import WidgetSessionRepository
from app.schemas.tools import (
    ToolAppendEventIn,
    ToolAppendEventOut,
    ToolCreateWidgetSessionIn,
    ToolCreateWidgetSessionOut,
    ToolFindActiveLeadByTgIn,
    ToolFindActiveLeadByTgOut,
    ToolBuildEstimateIn,
    ToolBuildEstimateOut,
    ToolCompareSupplierOffersIn,
    ToolCompareSupplierOffersOut,
    ToolCreateLeadIn,
    ToolCreateLeadOut,
    ToolGetCatalogJobsIn,
    ToolGetCatalogJobsOut,
    ToolGetPricingRulesOut,
    ToolImportSupplierPriceIn,
    ToolImportSupplierPriceOut,
    ToolLogAgentRunIn,
    ToolLogAgentRunOut,
    ToolRequestApprovalIn,
    ToolRequestApprovalOut,
    ToolSaveEstimateIn,
    ToolSaveEstimateOut,
    ToolSearchPartsIn,
    ToolSearchPartsOut,
    ToolUpdateLeadIn,
    ToolUpdateLeadOut,
    ToolGetWidgetSessionIn,
    ToolGetWidgetSessionOut,
)
from app.supplier_import import parse_supplier_price

router = APIRouter(prefix="/internal/tools", tags=["internal-tools"])


@router.post("/create_lead", response_model=ToolCreateLeadOut)
async def tool_create_lead(payload: ToolCreateLeadIn, request: Request, db: AsyncSession = Depends(get_db)) -> ToolCreateLeadOut:
    repo = LeadRepository(db)
    ev = LeadEventRepository(db)
    lead = await repo.create_lead(payload.channel, payload.contact, payload.problem_text, payload.car_hint)
    await ev.append(
        lead_id=lead.id,
        event_type="lead.created",
        payload={"channel": payload.channel, "problem_text": payload.problem_text, "car_hint": payload.car_hint.model_dump(), "contact": payload.contact.model_dump()},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    lead_expanded = await repo.get_expanded(lead.id)
    assert lead_expanded is not None
    return ToolCreateLeadOut(lead=lead_expanded)


@router.post("/update_lead", response_model=ToolUpdateLeadOut)
async def tool_update_lead(payload: ToolUpdateLeadIn, request: Request, db: AsyncSession = Depends(get_db)) -> ToolUpdateLeadOut:
    repo = LeadRepository(db)
    ev = LeadEventRepository(db)
    lead = await repo.get(payload.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    data = payload.fields.model_dump(exclude_unset=True)
    contact = data.pop("contact", None)
    car_hint = data.pop("car_hint", None)
    await repo.update_lead_fields(lead, data)
    if contact:
        await repo.update_client(lead.client_id, contact)
    if car_hint:
        await repo.upsert_lead_car(lead, car_hint)

    await ev.append(
        lead_id=lead.id,
        event_type="lead.updated",
        payload={"fields": payload.fields.model_dump(exclude_unset=True)},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    lead_expanded = await repo.get_expanded(lead.id)
    assert lead_expanded is not None
    return ToolUpdateLeadOut(lead=lead_expanded)


@router.post("/get_catalog_jobs", response_model=ToolGetCatalogJobsOut)
async def tool_get_catalog_jobs(payload: ToolGetCatalogJobsIn, db: AsyncSession = Depends(get_db)) -> ToolGetCatalogJobsOut:
    repo = CatalogRepository(db)
    jobs = await repo.search_jobs(payload.query)
    return ToolGetCatalogJobsOut(jobs=jobs)


@router.post("/get_pricing_rules", response_model=ToolGetPricingRulesOut)
async def tool_get_pricing_rules(db: AsyncSession = Depends(get_db)) -> ToolGetPricingRulesOut:
    repo = CatalogRepository(db)
    rules = await repo.list_pricing_rules()
    return ToolGetPricingRulesOut(rules=rules)


@router.post("/build_estimate", response_model=ToolBuildEstimateOut)
async def tool_build_estimate(payload: ToolBuildEstimateIn, request: Request, db: AsyncSession = Depends(get_db)) -> ToolBuildEstimateOut:
    repo = EstimateRepository(db)
    ev = LeadEventRepository(db)
    try:
        est = await repo.build_and_save(
            lead_id=payload.lead_id,
            jobs=payload.jobs,
            parts=payload.parts,
            pricing_rules=payload.pricing_rules,
            notes=payload.notes,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Lead not found")
    await ev.append(
        lead_id=payload.lead_id,
        event_type="estimate.draft_created",
        payload={"estimate_id": str(est.id), "total_price": float(est.total_price), "requires_approval": est.requires_approval},
        request_id=getattr(request.state, "request_id", None),
    )
    await ev.append(
        lead_id=payload.lead_id,
        event_type="estimate.saved",
        payload={"estimate_id": str(est.id)},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    await db.refresh(est)
    return ToolBuildEstimateOut(estimate=est)


@router.post("/save_estimate", response_model=ToolSaveEstimateOut)
async def tool_save_estimate(payload: ToolSaveEstimateIn, db: AsyncSession = Depends(get_db)) -> ToolSaveEstimateOut:
    # MVP: persist optional UI DTO for premium rendering (tiers, totals, etc.)
    if payload.estimate_id and payload.ui:
        repo = EstimateRepository(db)
        try:
            await repo.attach_ui(payload.estimate_id, payload.ui)
        except ValueError:
            raise HTTPException(status_code=404, detail="Estimate not found")
        await db.commit()
    return ToolSaveEstimateOut(ok=True)


@router.post("/request_approval", response_model=ToolRequestApprovalOut)
async def tool_request_approval(payload: ToolRequestApprovalIn, request: Request, db: AsyncSession = Depends(get_db)) -> ToolRequestApprovalOut:
    repo = LeadRepository(db)
    ev = LeadEventRepository(db)
    lead = await repo.get(payload.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await repo.update_lead_fields(lead, {"status": "estimated"})
    await ev.append(
        lead_id=payload.lead_id,
        event_type="estimate.approval_requested",
        payload={"estimate_id": str(payload.estimate_id) if payload.estimate_id else None},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    return ToolRequestApprovalOut(ok=True)


@router.post("/import_supplier_price", response_model=ToolImportSupplierPriceOut)
async def tool_import_supplier_price(payload: ToolImportSupplierPriceIn, request: Request, db: AsyncSession = Depends(get_db)) -> ToolImportSupplierPriceOut:
    repo = SupplierRepository(db)
    supplier = await repo.get_supplier(payload.supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    content = payload.decode()
    offers = parse_supplier_price(payload.filename, content)
    imported = await repo.upsert_offers(payload.supplier_id, offers)
    # no lead_id here; event emitted via public import endpoints tied to a lead in UI flows.
    await db.commit()
    return ToolImportSupplierPriceOut(supplier_id=payload.supplier_id, imported=imported)


@router.post("/search_parts", response_model=ToolSearchPartsOut)
async def tool_search_parts(payload: ToolSearchPartsIn, db: AsyncSession = Depends(get_db)) -> ToolSearchPartsOut:
    repo = PartsRepository(db)
    offers = await repo.search(payload.query)
    return ToolSearchPartsOut(offers=offers)


@router.post("/compare_supplier_offers", response_model=ToolCompareSupplierOffersOut)
async def tool_compare_supplier_offers(payload: ToolCompareSupplierOffersIn, db: AsyncSession = Depends(get_db)) -> ToolCompareSupplierOffersOut:
    repo = PartsRepository(db)
    sku = payload.part_key.get("sku")
    oem = payload.part_key.get("oem")
    offers = await repo.compare(sku=sku, oem=oem)
    return ToolCompareSupplierOffersOut(offers=offers)


@router.post("/log_agent_run", response_model=ToolLogAgentRunOut)
async def tool_log_agent_run(payload: ToolLogAgentRunIn, request: Request, db: AsyncSession = Depends(get_db)) -> ToolLogAgentRunOut:
    repo = AgentRunRepository(db)
    await repo.create(
        lead_id=payload.lead_id,
        user_message=payload.user_message,
        agent_plan=payload.agent_plan,
        tool_calls=[x.model_dump(mode="json") for x in payload.tool_calls],
        final_answer=payload.final_answer,
    )
    await db.commit()
    return ToolLogAgentRunOut(ok=True)


@router.post("/append_event", response_model=ToolAppendEventOut)
async def tool_append_event(payload: ToolAppendEventIn, request: Request, db: AsyncSession = Depends(get_db)) -> ToolAppendEventOut:
    ev = LeadEventRepository(db)
    await ev.append(
        lead_id=payload.lead_id,
        event_type=payload.event_type,
        payload=payload.payload,
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    return ToolAppendEventOut(ok=True)


@router.post("/find_active_lead_by_tg", response_model=ToolFindActiveLeadByTgOut)
async def tool_find_active_lead_by_tg(payload: ToolFindActiveLeadByTgIn, db: AsyncSession = Depends(get_db)) -> ToolFindActiveLeadByTgOut:
    # Find latest lead for client with tg_id where status != closed
    from sqlalchemy import select
    from app.models import Client, Lead

    stmt = (
        select(Lead)
        .join(Client, Client.id == Lead.client_id)
        .where(Client.tg_id == payload.tg_id)
        .where(Lead.status != "closed")
        .order_by(Lead.updated_at.desc())
        .limit(1)
    )
    lead = (await db.execute(stmt)).scalar_one_or_none()
    return ToolFindActiveLeadByTgOut(lead_id=lead.id if lead else None)


@router.post("/create_widget_session", response_model=ToolCreateWidgetSessionOut)
async def tool_create_widget_session(payload: ToolCreateWidgetSessionIn, request: Request, db: AsyncSession = Depends(get_db)) -> ToolCreateWidgetSessionOut:
    # Create new lead snapshot + widget session mapping
    from app.schemas.common import CarHint, ClientContact

    leads = LeadRepository(db)
    events = LeadEventRepository(db)
    sessions = WidgetSessionRepository(db)

    lead = await leads.create_lead(
        payload.channel,
        contact=ClientContact(),
        problem_text="Widget session",
        car_hint=CarHint(),
    )
    ws = await sessions.create(lead_id=lead.id, metadata=payload.metadata)
    await events.append(
        lead_id=lead.id,
        event_type="widget.session_created",
        payload={"session_id": str(ws.id), "metadata": payload.metadata},
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    return ToolCreateWidgetSessionOut(session_id=ws.id, lead_id=lead.id)


@router.post("/get_widget_session", response_model=ToolGetWidgetSessionOut)
async def tool_get_widget_session(payload: ToolGetWidgetSessionIn, db: AsyncSession = Depends(get_db)) -> ToolGetWidgetSessionOut:
    sessions = WidgetSessionRepository(db)
    ws = await sessions.get(payload.session_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Session not found")
    await sessions.touch(payload.session_id)
    await db.commit()
    return ToolGetWidgetSessionOut(session_id=ws.id, lead_id=ws.lead_id)

