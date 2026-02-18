from app.estimate_logic import build_draft_estimate


def test_build_draft_estimate_applies_markup_and_discount():
    jobs = [
        {"code": "TO_OIL_FILTER", "name": "ТО: масло", "qty": 1, "unit_price": 2000, "tags": {"keywords": ["maintenance"]}},
        {"code": "DIAG", "name": "Диагностика", "qty": 1, "unit_price": 1000, "tags": {"keywords": ["diagnostics"]}},
    ]
    parts = [{"sku": "P1", "name": "Фильтр", "qty": 1, "unit_price": 1000, "stock": 1}]
    rules = [
        {"rule_type": "parts_markup_pct", "params": {"pct": 10}},
        {"rule_type": "jobs_discount_pct", "params": {"pct": 5, "when_tags_contains": ["maintenance"]}},
    ]

    draft = build_draft_estimate("lead-1", jobs=jobs, parts=parts, pricing_rules=rules)
    assert draft["requires_approval"] is True

    items = draft["items"]
    j0 = items["jobs"][0]
    assert j0["unit_price"] == 1900.0  # 2000 - 5%
    p0 = items["parts"][0]
    assert p0["unit_price"] == 1100.0  # 1000 + 10%
    assert items["totals"]["total"] == 1900.0 + 1000.0 + 1100.0  # 1900 + 1000 + 1100

