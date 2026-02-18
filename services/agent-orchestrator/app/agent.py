from __future__ import annotations

import uuid
from typing import Any

import httpx

from app.model_client import ModelClient
from app.nlu import rule_based_nlu
from app.schemas import AgentAction, AgentCitation, AgentMessageIn, AgentMessageOut, AgentResponse, ToolCallRecord
from app.settings import settings
from app.tools import CoreApiTools, ToolLogger
from app.state_machine import AgentPlan, Intent, build_plan


async def rag_query(logger: ToolLogger, query: str, top_k: int = 3) -> list[dict[str, Any]]:
    url = f"{settings.rag_url.rstrip('/')}/api/rag/query"
    rec = ToolCallRecord(name="rag_query", params={"query": query, "top_k": top_k}, ok=False)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json={"query": query, "top_k": top_k})
        if r.status_code >= 400:
            rec.error = f"HTTP {r.status_code}: {r.text}"
            logger.add(rec)
            return []
        rec.ok = True
        rec.result = r.json()
        logger.add(rec)
        return rec.result.get("results", []) if isinstance(rec.result, dict) else []
    except Exception as e:
        rec.ok = False
        rec.error = str(e)
        logger.add(rec)
        return []


def _extract_car_hint(slots: dict[str, Any]) -> dict[str, Any]:
    return {
        "vin": slots.get("vin"),
        "brand": slots.get("brand"),
        "model": slots.get("model"),
        "year": slots.get("year"),
        "engine": slots.get("engine"),
        "mileage": slots.get("mileage"),
    }


def _questions_from_missing(missing: list[str]) -> list[str]:
    qs = []
    if "brand" in missing or "model" in missing:
        qs.append("Подскажите марку и модель авто?")
    if "year" in missing:
        qs.append("Какой год выпуска?")
    if "mileage" in missing:
        qs.append("Какой пробег (примерно)?")
    if "engine" in missing:
        qs.append("Какой двигатель/объём? (если знаете)")
    if "vin" in missing:
        qs.append("Пришлите VIN (17 символов), если есть — это ускорит точный подбор.")
    if "part_query" in missing:
        qs.append("Какая именно запчасть нужна (и желательно OEM/артикул, если есть)?")
    return qs[:2]


async def _emit_event(tools: CoreApiTools, lead_id: uuid.UUID, event_type: str, payload: dict[str, Any] | None) -> None:
    try:
        await tools.append_event(lead_id, event_type, payload)
    except Exception:
        return


def _format_source(rag_results: list[dict[str, Any]]) -> str:
    if not rag_results:
        return ""
    src = rag_results[0] or {}
    title = src.get("title") or "Документ"
    meta = src.get("metadata") or {}
    section = meta.get("section") or meta.get("chunk")
    section_txt = f"chunk {section}" if section is not None else "—"
    return f"Источник: {title} / {section_txt}"


def _citations_from_rag(rag_results: list[dict[str, Any]] | None) -> list[AgentCitation]:
    out: list[AgentCitation] = []
    for r in rag_results or []:
        title = str(r.get("title") or "Документ")
        meta = r.get("metadata") or {}
        section = meta.get("section")
        if section is None:
            ch = meta.get("chunk")
            section = f"chunk {ch}" if ch is not None else None
        out.append(AgentCitation(title=title, section=str(section) if section is not None else None))
    return out[:3]


def _fmt_money(v: Any) -> str:
    try:
        if v is None:
            return "—"
        return f"{float(v):.0f} ₽"
    except Exception:
        return "—"


def _pick_part_tiers(offers: list[dict[str, Any]], car_brand: str | None) -> dict[str, dict[str, Any] | None]:
    if not offers:
        return {"economy": None, "optimum": None, "oem": None}

    def price(o: dict[str, Any]) -> float:
        try:
            return float(o.get("price") or 1e18)
        except Exception:
            return 1e18

    # offers already sorted by stock desc, price asc, delivery asc (core-api)
    in_stock = [o for o in offers if (o.get("stock") or 0) > 0]
    pool = in_stock or offers

    economy = min(pool, key=price) if pool else None
    optimum = pool[0] if pool else None

    oem = None
    if car_brand:
        b = car_brand.lower()
        for o in pool:
            if str(o.get("brand") or "").lower() == b:
                oem = o
                break

    return {"economy": economy, "optimum": optimum, "oem": oem or optimum}


def _offer_to_part_item(o: dict[str, Any]) -> dict[str, Any]:
    return {
        "sku": o.get("sku"),
        "oem": o.get("oem"),
        "name": o.get("name") or "Запчасть",
        "brand": o.get("brand"),
        "qty": 1,
        "unit_price": float(o.get("price") or 0),
        "supplier_id": o.get("supplier_id"),
        "delivery_days": o.get("delivery_days"),
        "stock": o.get("stock"),
    }


def _estimate_ui_from_estimate(
    est_obj: dict[str, Any] | None,
    *,
    parts_tiers: dict[str, dict[str, Any] | None] | None = None,
) -> dict[str, Any] | None:
    if not est_obj or not isinstance(est_obj, dict):
        return None

    items = est_obj.get("items") or {}
    jobs = (items.get("jobs") or []) if isinstance(items, dict) else []
    parts = (items.get("parts") or []) if isinstance(items, dict) else []
    totals = (items.get("totals") or {}) if isinstance(items, dict) else {}

    jobs_ui = []
    for j in jobs or []:
        jobs_ui.append(
            {
                "name": j.get("name") or "Работа",
                "qty": int(j.get("qty") or 1),
                "unit_price": float(j.get("unit_price")) if j.get("unit_price") is not None else None,
                "total": float(j.get("total")) if j.get("total") is not None else None,
            }
        )

    parts_ui: dict[str, list[dict[str, Any]]] = {"economy": [], "optimum": [], "oem": []}
    if parts_tiers:
        for tier in ("economy", "optimum", "oem"):
            o = parts_tiers.get(tier)
            if not o:
                continue
            try:
                unit_price = float(o.get("price") or 0)
            except Exception:
                unit_price = None
            parts_ui[tier] = [
                {
                    "name": o.get("name") or "Запчасть",
                    "brand": o.get("brand"),
                    "oem": o.get("oem"),
                    "sku": o.get("sku"),
                    "qty": 1,
                    "unit_price": unit_price,
                    "total": unit_price,
                    "supplier_id": o.get("supplier_id"),
                    "stock": o.get("stock"),
                    "delivery_days": o.get("delivery_days"),
                }
            ]
    else:
        # fallback: show whatever is in estimate as "optimum"
        for p in parts or []:
            parts_ui["optimum"].append(
                {
                    "name": p.get("name") or "Запчасть",
                    "brand": p.get("brand"),
                    "oem": p.get("oem"),
                    "sku": p.get("sku"),
                    "qty": int(p.get("qty") or 1),
                    "unit_price": float(p.get("unit_price")) if p.get("unit_price") is not None else None,
                    "total": float(p.get("total")) if p.get("total") is not None else None,
                    "supplier_id": p.get("supplier_id"),
                    "stock": p.get("stock"),
                    "delivery_days": p.get("delivery_days"),
                }
            )

    def _f(v: Any) -> float | None:
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    total_fallback = _f(totals.get("total")) if isinstance(totals, dict) else None
    if total_fallback is None:
        total_fallback = _f(est_obj.get("total_price"))

    return {
        "jobs": jobs_ui,
        "parts": parts_ui,
        "totals": {
            "jobs_total": _f(totals.get("jobs_total")) if isinstance(totals, dict) else None,
            "parts_total": _f(totals.get("parts_total")) if isinstance(totals, dict) else None,
            "total": total_fallback,
        },
        "requires_approval": bool(est_obj.get("requires_approval", True)),
    }


async def handle_agent_message(payload: AgentMessageIn, *, request_id: str | None) -> AgentMessageOut:
    logger = ToolLogger(request_id)
    tools = CoreApiTools(logger)

    lead_id: uuid.UUID | None = payload.lead_id
    actions: list[AgentAction] = []
    intent: Intent = "unknown"
    slots: dict[str, Any] = {}

    try:
        if settings.use_model_nlu:
            model = ModelClient()
            try:
                nlu = await model.nlu(payload.message)
                if not nlu.intent or nlu.intent == "unknown":
                    nlu = rule_based_nlu(payload.message)
            except Exception:
                nlu = rule_based_nlu(payload.message)
        else:
            nlu = rule_based_nlu(payload.message)

        intent = nlu.intent if nlu.intent in ("to_service", "parts_search", "problem_symptom", "unknown") else "unknown"
        slots = nlu.slots or {}

        # Ensure lead exists early (contract: lead_id always present)
        contact = payload.client_contact.model_dump(mode="json") if payload.client_contact else {}
        car_hint = _extract_car_hint(slots)
        if lead_id:
            fields: dict[str, Any] = {"problem_text": payload.message}
            if contact and any(v is not None for v in contact.values()):
                fields["contact"] = contact
            if any(v is not None for v in car_hint.values()):
                fields["car_hint"] = car_hint
            try:
                await tools.update_lead(lead_id, fields)
            except Exception:
                lead = await tools.create_lead(payload.channel, contact, payload.message, car_hint)
                lead_id = uuid.UUID(lead["lead"]["id"])
                actions.append(AgentAction(type="lead_created", payload={"lead_id": str(lead_id)}))
        else:
            lead = await tools.create_lead(payload.channel, contact, payload.message, car_hint)
            lead_id = uuid.UUID(lead["lead"]["id"])
            actions.append(AgentAction(type="lead_created", payload={"lead_id": str(lead_id)}))

        plan: AgentPlan = build_plan(intent, slots, require_approval=settings.require_approval)
        await _emit_event(tools, lead_id, "agent.message_received", {"channel": payload.channel, "message": payload.message, "intent": intent})
        await _emit_event(tools, lead_id, "agent.plan_created", plan.model_dump(mode="json"))

        if plan.missing_slots:
            qs = _questions_from_missing(plan.missing_slots)
            answer_text = "Чтобы корректно посчитать работы и подобрать расходники, нужно уточнить пару деталей по авто."
            next_step = "Ответьте на вопросы — после этого соберу черновик сметы и отправлю оператору на подтверждение."
            response = AgentResponse(
                answer_text=answer_text,
                questions=qs,
                estimate_ui=None,
                next_step=next_step,
                citations=[],
            )
            answer = response.answer_text
            # tool_called events for any tool calls already recorded (create_lead/update_lead)
            for rec in logger.records:
                await _emit_event(tools, lead_id, "agent.tool_called", rec)
            await _emit_event(tools, lead_id, "agent.final_answer_sent", {"answer_preview": answer[:200], "requires_approval": False})
            outcome = {"agent_plan": plan.model_dump(mode="json"), "final_answer": answer}
            await tools.log_agent_run(lead_id, payload.message, logger.records, outcome)
            return AgentMessageOut(lead_id=lead_id, answer=answer, response=response, actions=actions, requires_approval=False)

        source_line = ""
        pricing_rules: list[dict[str, Any]] = []

        if intent == "to_service":
            jobs_resp = await tools.get_catalog_jobs("ТО", car_context=slots)
            jobs = jobs_resp.get("jobs", []) if isinstance(jobs_resp, dict) else []
            chosen = jobs[:1] if jobs else []
            job_items = [
                {
                    "code": j["code"],
                    "name": j["name"],
                    "qty": 1,
                    "unit_price": float(j.get("base_price", 0) or 0),
                    "tags": j.get("tags"),
                }
                for j in chosen
            ]

            offers_resp = await tools.search_parts("Фильтр масляный", car_context=slots)
            offers = offers_resp.get("offers", []) if isinstance(offers_resp, dict) else []
            tiers = _pick_part_tiers(offers, slots.get("brand"))
            selected_offer = tiers.get("optimum")
            parts_items = [_offer_to_part_item(selected_offer)] if selected_offer else []

            est = await tools.build_estimate(lead_id, jobs=job_items, pricing_rules=pricing_rules, parts=parts_items)
            est_obj = est.get("estimate") if isinstance(est, dict) else None
            if settings.require_approval:
                await tools.request_approval(lead_id, est_obj or {})
            est_ui = _estimate_ui_from_estimate(est_obj, parts_tiers=tiers)
            await tools.save_estimate(lead_id, est_obj or {}, ui=est_ui)

            followup_qs = []
            if not slots.get("vin"):
                followup_qs.append("Пришлите VIN (17 символов) — уточню расходники и совместимость.")
            if not slots.get("engine"):
                followup_qs.append("Какой двигатель/объём? (если знаете)")

            answer_text = "Собрал предварительный черновик по ТО. Итог уточняется по выбранным расходникам и осмотру."
            next_step = "Выберите комплект расходников (если нужно) — затем оператор подтвердит смету и предложит удобное время."
            response = AgentResponse(
                answer_text=answer_text,
                questions=followup_qs[:2],
                estimate_ui=est_ui,
                next_step=next_step,
                citations=[],
            )
            answer = response.answer_text
            for rec in logger.records:
                await _emit_event(tools, lead_id, "agent.tool_called", rec)
            await _emit_event(tools, lead_id, "agent.final_answer_sent", {"answer_preview": answer[:200], "requires_approval": True})
            outcome = {"agent_plan": plan.model_dump(mode="json"), "final_answer": answer}
            await tools.log_agent_run(lead_id, payload.message, logger.records, outcome)
            return AgentMessageOut(
                lead_id=lead_id,
                answer=answer,
                response=response,
                actions=actions,
                requires_approval=bool(settings.require_approval and (est_obj or {}).get("requires_approval", True)),
                draft_estimate=est_obj,
            )

        if intent == "problem_symptom":
            rag_results = await rag_query(logger, payload.message, top_k=2)
            if rag_results:
                source_line = _format_source(rag_results)
            citations = _citations_from_rag(rag_results)

            jobs_resp = await tools.get_catalog_jobs("подвеск", car_context=slots)
            jobs = jobs_resp.get("jobs", []) if isinstance(jobs_resp, dict) else []
            chosen = jobs[:1] if jobs else []
            job_items = [
                {
                    "code": j["code"],
                    "name": j["name"],
                    "qty": 1,
                    "unit_price": float(j.get("base_price", 0) or 0),
                    "tags": j.get("tags"),
                }
                for j in chosen
            ]

            est = await tools.build_estimate(lead_id, jobs=job_items, pricing_rules=pricing_rules, parts=[])
            est_obj = est.get("estimate") if isinstance(est, dict) else None
            if settings.require_approval:
                await tools.request_approval(lead_id, est_obj or {})
            est_ui = _estimate_ui_from_estimate(est_obj)
            await tools.save_estimate(lead_id, est_obj or {}, ui=est_ui)

            answer_text = (
                "Начнём с диагностики: без осмотра диагноз не утверждаем. "
                "Возможные причины стука при повороте: стойка стабилизатора, шаровая, рулевой наконечник, опорный подшипник."
            )
            next_step = "Ответьте на 1–2 уточнения — затем оператор подтвердит черновик и предложит запись."
            response = AgentResponse(
                answer_text=answer_text,
                questions=[
                    "Где/когда проявляется стук (скорость, неровности, торможение)?",
                    "Были ли удары/ремонт по подвеске недавно?",
                ],
                estimate_ui=est_ui,
                next_step=next_step,
                citations=citations,
            )
            answer = response.answer_text
            for rec in logger.records:
                await _emit_event(tools, lead_id, "agent.tool_called", rec)
            await _emit_event(tools, lead_id, "agent.final_answer_sent", {"answer_preview": answer[:200], "requires_approval": True})
            outcome = {"agent_plan": plan.model_dump(mode="json"), "final_answer": answer}
            await tools.log_agent_run(lead_id, payload.message, logger.records, outcome)
            return AgentMessageOut(
                lead_id=lead_id,
                answer=answer,
                response=response,
                actions=actions,
                requires_approval=bool(settings.require_approval and (est_obj or {}).get("requires_approval", True)),
                draft_estimate=est_obj,
            )

        # intent == parts_search
        part_query = slots.get("part_query") or payload.message
        offers_resp = await tools.search_parts(part_query, car_context=slots)
        offers = offers_resp.get("offers", []) if isinstance(offers_resp, dict) else []
        tiers = _pick_part_tiers(offers, slots.get("brand"))
        selected_offer = tiers.get("optimum") or tiers.get("economy")
        parts_items = [_offer_to_part_item(selected_offer)] if selected_offer else []

        est_obj = None
        if parts_items:
            est = await tools.build_estimate(lead_id, jobs=[], pricing_rules=pricing_rules, parts=parts_items)
            est_obj = est.get("estimate") if isinstance(est, dict) else None
            if settings.require_approval:
                await tools.request_approval(lead_id, est_obj or {})
            est_ui = _estimate_ui_from_estimate(est_obj, parts_tiers=tiers) if est_obj else None
            await tools.save_estimate(lead_id, est_obj or {}, ui=est_ui)

        summary = "Подобрал варианты запчастей у поставщиков (предварительно)." if offers else "Пока нет офферов в импортированных прайсах."
        next_step = (
            "Если выбираете вариант — оператор подтвердит черновик и оформит заказ (approval)."
            if est_obj
            else "Импортируйте прайс в админке и повторите подбор."
        )

        response = AgentResponse(
            answer_text=summary,
            questions=["Уточните комплектацию/двигатель или VIN (для точного подбора)."] if not slots.get("vin") else [],
            estimate_ui=est_ui if est_obj else None,
            next_step=next_step,
            citations=[],
        )
        answer = response.answer_text
        outcome = {"agent_plan": {"intent": intent, "slots": slots, "lead_id": str(lead_id)}, "final_answer": answer}
        for rec in logger.records:
            await _emit_event(tools, lead_id, "agent.tool_called", rec)
        await _emit_event(tools, lead_id, "agent.final_answer_sent", {"answer_preview": answer[:200], "requires_approval": bool(est_obj)})
        outcome = {"agent_plan": plan.model_dump(mode="json"), "final_answer": answer}
        await tools.log_agent_run(lead_id, payload.message, logger.records, outcome)
        return AgentMessageOut(
            lead_id=lead_id,
            answer=answer,
            response=response,
            actions=actions,
            requires_approval=bool(settings.require_approval and (est_obj or {}).get("requires_approval", True)),
            draft_estimate=est_obj,
        )

    except Exception as e:
        # Best-effort auditing + safe response
        if not lead_id:
            lead = await tools.create_lead(payload.channel, {}, payload.message, {})
            lead_id = uuid.UUID(lead["lead"]["id"])

        answer_text = "Что-то пошло не так, попробуйте ещё раз. Я сохранил обращение — оператор увидит его в панели."
        response = AgentResponse(
            answer_text=answer_text,
            questions=[],
            estimate_ui=None,
            next_step="Повторите запрос через минуту или оставьте телефон — оператор свяжется.",
            citations=[],
        )
        answer = response.answer_text
        outcome = {"agent_plan": {"intent": intent, "slots": slots, "error": str(e)}, "final_answer": answer}
        try:
            await _emit_event(tools, lead_id, "agent.final_answer_sent", {"answer_preview": answer[:200], "requires_approval": False, "error": str(e)})
            await tools.log_agent_run(lead_id, payload.message, logger.records, outcome)
        except Exception:
            pass
        return AgentMessageOut(lead_id=lead_id, answer=answer, response=response, actions=actions, requires_approval=False)

