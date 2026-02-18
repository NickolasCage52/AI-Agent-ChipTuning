from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class PricingRule:
    rule_type: str
    params: dict[str, Any]


def _d(v: Any, default: Decimal = Decimal("0")) -> Decimal:
    try:
        if v is None:
            return default
        return Decimal(str(v))
    except Exception:
        return default


def apply_total_rules(total: Decimal, rules: list[PricingRule]) -> Decimal:
    """
    Deterministic rule application in the provided order.

    Supported total-level rules:
    - percent_add_total: params {percent: 15} -> total *= 1.15
    - percent_mult_total: params {mult: 1.2} or {percent: 20} -> total *= 1.2
    - fixed_add_total: params {amount: 500} -> total += 500
    """
    out = total
    for r in rules:
        rt = (r.rule_type or "").strip()
        p = r.params or {}
        if rt == "percent_add_total":
            pct = _d(p.get("percent"))
            out = (out * (Decimal("100") + pct) / Decimal("100")).quantize(Decimal("0.01"))
        elif rt == "percent_mult_total":
            mult = p.get("mult")
            if mult is None:
                pct = _d(p.get("percent"))
                mult_d = (Decimal("100") + pct) / Decimal("100")
            else:
                mult_d = _d(mult, Decimal("1"))
            out = (out * mult_d).quantize(Decimal("0.01"))
        elif rt == "fixed_add_total":
            amount = _d(p.get("amount"))
            out = (out + amount).quantize(Decimal("0.01"))
    return out


def parse_rules(raw_rules: list[dict[str, Any]] | None) -> list[PricingRule]:
    rules: list[PricingRule] = []
    for r in raw_rules or []:
        rules.append(PricingRule(rule_type=str(r.get("rule_type") or r.get("type") or ""), params=(r.get("params") or {})))
    return rules

