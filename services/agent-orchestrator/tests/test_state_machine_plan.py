from app.state_machine import build_plan


def test_to_service_missing_slots_asks_questions():
    plan = build_plan("to_service", {"brand": "Kia", "model": "Rio"}, require_approval=True)
    assert plan.next_action == "ask_questions"
    assert "year" in plan.missing_slots
    assert "mileage" in plan.missing_slots
    assert plan.requires_human_approval is True


def test_parts_search_calls_tools_when_ready():
    plan = build_plan(
        "parts_search",
        {"part_query": "колодки", "brand": "Toyota", "model": "Camry 50", "year": 2014},
        require_approval=True,
    )
    assert plan.next_action == "call_tools"
    assert "search_parts" in plan.tools_to_call


def test_problem_symptom_requires_basic_car_context():
    plan = build_plan("problem_symptom", {"brand": "Toyota", "model": "Camry 50"}, require_approval=True)
    assert plan.next_action == "ask_questions"
    assert plan.missing_slots == ["year"]
