from __future__ import annotations

import re
from typing import Any

from app.schemas import NluResult


_BRANDS = ["kia", "hyundai", "toyota", "vw", "volkswagen", "bmw", "mercedes", "audi", "skoda", "renault", "nissan", "ford", "lada"]


def rule_based_nlu(message: str) -> NluResult:
    m = message.lower()
    intent = "unknown"
    if any(x in m for x in ["то", "техобслуж", "замена масла", "масло", "oil service"]):
        intent = "to_service"
    if any(x in m for x in ["стук", "скрип", "вибра", "шум", "тянет", "люфт"]):
        intent = "problem_symptom" if intent == "unknown" else intent
    if any(x in m for x in ["колодк", "запчаст", "нужн", "тормоз", "фильтр", "свеч", "ремень"]):
        intent = "parts_search" if intent == "unknown" else intent

    slots: dict[str, Any] = {}

    # VIN
    vin = re.search(r"\b([A-HJ-NPR-Z0-9]{17})\b", message.upper())
    if vin:
        slots["vin"] = vin.group(1)

    # year
    year = re.search(r"\b(19[8-9]\d|20[0-2]\d)\b", m)
    if year:
        slots["year"] = int(year.group(1))

    # mileage: "120к" / "120k" / "120000"
    mil = re.search(r"\b(\d{1,3})(\s?)(к|k)\b", m)
    if mil:
        slots["mileage"] = int(mil.group(1)) * 1000
    else:
        mil2 = re.search(r"\b(\d{5,6})\b", m)
        if mil2:
            slots["mileage"] = int(mil2.group(1))

    # brand/model heuristic
    for b in _BRANDS:
        if re.search(rf"\b{re.escape(b)}\b", m):
            slots["brand"] = b.title() if b != "vw" else "VW"
            break

    # model: word right after brand (simple)
    if slots.get("brand"):
        b = slots["brand"].lower()
        mo = re.search(rf"\b{re.escape(b)}\s+([a-z0-9\-]+)\b", m)
        if mo:
            slots["model"] = mo.group(1).title()

    # special: detect Camry 50 even without explicit "Toyota"
    mo2 = re.search(r"\b(camry)\s*(50)\b", m)
    if mo2:
        slots["brand"] = "Toyota"
        slots["model"] = "Camry 50"

    # part query: strip filler
    if intent == "parts_search":
        slots["part_query"] = message.strip()

    return NluResult(intent=intent, slots=slots)

