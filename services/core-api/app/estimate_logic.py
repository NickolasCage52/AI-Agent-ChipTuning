from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.domain.pricing.engine import apply_total_rules, parse_rules

def _to_decimal(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def apply_pricing_rules(
    jobs: list[dict[str, Any]],
    parts: list[dict[str, Any]],
    pricing_rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    parts_markup_pct = Decimal("0")
    jobs_discount_pct = Decimal("0")
    discount_keywords: set[str] = set()

    for r in pricing_rules or []:
        rt = (r.get("rule_type") or r.get("type") or "").strip()
        params = r.get("params") or {}
        if rt == "parts_markup_pct":
            parts_markup_pct = _to_decimal(params.get("pct", 0))
        if rt == "jobs_discount_pct":
            jobs_discount_pct = _to_decimal(params.get("pct", 0))
            for kw in params.get("when_tags_contains", []) or []:
                discount_keywords.add(str(kw).lower())
        if rt == "percent_add_total":
            # handled later in build_draft_estimate totals stage
            pass
        if rt == "percent_add_jobs":
            pct = _to_decimal(params.get("percent", 0))
            if pct:
                k = (Decimal("100") + pct) / Decimal("100")
                for j in jobs:
                    j["unit_price"] = float((_to_decimal(j.get("unit_price")) * k).quantize(Decimal("0.01")))

    # parts markup
    if parts_markup_pct:
        k = (Decimal("100") + parts_markup_pct) / Decimal("100")
        for p in parts:
            p["unit_price"] = float((_to_decimal(p.get("unit_price")) * k).quantize(Decimal("0.01")))

    # jobs discount (only if job tags contain keyword)
    if jobs_discount_pct and discount_keywords:
        k = (Decimal("100") - jobs_discount_pct) / Decimal("100")
        for j in jobs:
            tags = j.get("tags") or {}
            keywords = []
            if isinstance(tags, dict):
                keywords = tags.get("keywords") or []
                if isinstance(keywords, str):
                    keywords = [keywords]
            if any(str(x).lower() in discount_keywords for x in keywords):
                j["unit_price"] = float((_to_decimal(j.get("unit_price")) * k).quantize(Decimal("0.01")))

    return jobs, parts


def build_draft_estimate(
    lead_id: str,
    jobs: list[dict[str, Any]],
    parts: list[dict[str, Any]],
    pricing_rules: list[dict[str, Any]] | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    jobs = [dict(x) for x in (jobs or [])]
    parts = [dict(x) for x in (parts or [])]
    pricing_rules = pricing_rules or []

    jobs, parts = apply_pricing_rules(jobs, parts, pricing_rules)

    job_items: list[dict[str, Any]] = []
    part_items: list[dict[str, Any]] = []

    jobs_total = Decimal("0")
    parts_total = Decimal("0")

    for j in jobs:
        qty = _to_decimal(j.get("qty", 1))
        unit = _to_decimal(j.get("unit_price", j.get("price", 0)))
        total = (qty * unit).quantize(Decimal("0.01"))
        jobs_total += total
        job_items.append(
            {
                "type": "job",
                "code": j.get("code") or j.get("id") or "JOB",
                "name": j.get("name") or "Работа",
                "qty": float(qty),
                "unit_price": float(unit.quantize(Decimal("0.01"))),
                "total": float(total),
                "tags": j.get("tags"),
            }
        )

    for p in parts:
        qty = _to_decimal(p.get("qty", 1))
        unit = _to_decimal(p.get("unit_price", p.get("price", 0)))
        total = (qty * unit).quantize(Decimal("0.01"))
        parts_total += total
        part_items.append(
            {
                "type": "part",
                "sku": p.get("sku"),
                "oem": p.get("oem"),
                "name": p.get("name") or "Запчасть",
                "brand": p.get("brand"),
                "qty": float(qty),
                "unit_price": float(unit.quantize(Decimal("0.01"))),
                "total": float(total),
                "supplier_id": p.get("supplier_id"),
                "delivery_days": p.get("delivery_days"),
                "stock": p.get("stock"),
            }
        )

    total = (jobs_total + parts_total).quantize(Decimal("0.01"))
    total = apply_total_rules(total, parse_rules(pricing_rules))

    items = {
        "jobs": job_items,
        "parts": part_items,
        "totals": {
            "jobs_total": float(jobs_total.quantize(Decimal("0.01"))),
            "parts_total": float(parts_total.quantize(Decimal("0.01"))),
            "total": float(total),
        },
        "notes": notes,
        "policies": [
            "Диагноз не утверждается без осмотра.",
            "Любые действия, влияющие на деньги/закуп: черновик → требует подтверждения → подтверждение оператором.",
        ],
    }

    return {
        "lead_id": lead_id,
        "items": items,
        "total_price": float(total),
        "requires_approval": True,
    }

