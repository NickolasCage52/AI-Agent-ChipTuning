from app.nlu import rule_based_nlu


def test_rule_nlu_detects_maintenance():
    r = rule_based_nlu("Нужно ТО на Kia Rio 2017, пробег 120к")
    assert r.intent == "to_service"
    assert r.slots.get("brand") == "Kia"
    assert r.slots.get("model") == "Rio"
    assert r.slots.get("year") == 2017
    assert r.slots.get("mileage") == 120000


def test_rule_nlu_detects_symptom():
    r = rule_based_nlu("Стук справа при повороте")
    assert r.intent in ("problem_symptom", "unknown")


def test_rule_nlu_detects_parts():
    r = rule_based_nlu("Нужны колодки на Camry 50")
    assert r.intent == "parts_search"
    assert "Camry" in (r.slots.get("model") or "")

