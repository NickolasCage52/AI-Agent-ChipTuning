from decimal import Decimal

from app.domain.pricing.engine import PricingRule, apply_total_rules


def test_apply_total_rules_order_is_stable():
    total = Decimal("1000.00")
    rules = [
        PricingRule("fixed_add_total", {"amount": 500}),
        PricingRule("percent_add_total", {"percent": 10}),
    ]
    # (1000 + 500) * 1.10 = 1650
    out = apply_total_rules(total, rules)
    assert out == Decimal("1650.00")


def test_apply_total_rules_multiplier():
    total = Decimal("1000.00")
    rules = [PricingRule("percent_mult_total", {"mult": 1.2})]
    out = apply_total_rules(total, rules)
    assert out == Decimal("1200.00")


def test_apply_total_rules_percent_multiplier_via_percent_param():
    total = Decimal("1000.00")
    rules = [PricingRule("percent_mult_total", {"percent": 20})]
    out = apply_total_rules(total, rules)
    assert out == Decimal("1200.00")

