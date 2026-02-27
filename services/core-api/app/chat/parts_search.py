from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.intent_extractor import extract_sku_from_message
from app.repositories.parts import PartsRepository

# Термины для поиска: нормализованный тип -> ключевые слова (en + ru, паттерны SKU)
SEARCH_EXPAND: dict[str, list[str]] = {
    "тормозные колодки": ["brake", "pad", "тормоз", "колодк"],
    "колодки": ["brake", "pad", "тормоз", "колодк"],
    "масляный фильтр": ["oil", "filter", "фильтр", "масл"],
    "фильтр масл": ["oil", "filter", "фильтр", "масл"],
    "воздушный фильтр": ["air", "filter", "воздушн", "фильтр"],
    "комплект ГРМ": ["belt", "грм", "ремень"],
    "ремень ГРМ": ["belt", "грм", "ремень"],
    "свечи зажигания": ["spark", "свеч", "зажиган"],
    "диск": ["brake", "disc", "диск", "тормоз"],
    "масло": ["oil", "масло"],
}


def _search_terms(part_type: str) -> list[str]:
    """Возвращает список поисковых терминов для ILIKE (en + ru + паттерны SKU)."""
    pt_lower = part_type.lower().strip()
    for key, terms in SEARCH_EXPAND.items():
        if key in pt_lower or pt_lower in key:
            return terms
    return [part_type]


def _matches_car(offer_name: str | None, brand: str | None, model: str | None) -> bool:
    """Проверяет, подходит ли запчасть под марку/модель (по наименованию)."""
    if not offer_name:
        return False
    name_lower = offer_name.lower()
    if brand and brand.lower() in name_lower:
        return True
    if model and model.lower() in name_lower:
        return True
    return False


async def search_parts(
    part_type: str,
    car_context: dict[str, Any],
    db: AsyncSession,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Ищет запчасти по типу. Фильтрует по car_context (brand/model в наименовании).
    """
    repo = PartsRepository(db)
    terms = _search_terms(part_type)
    seen_ids: set[int] = set()
    all_offers: list[Any] = []
    for term in terms:
        offers = await repo.search(term, limit=limit)
        for o in offers:
            if o.id not in seen_ids:
                seen_ids.add(o.id)
                all_offers.append(o)

    brand = (car_context.get("brand") or "").strip()
    model = (car_context.get("model") or "").strip()

    # Фильтр по машине: приоритет запчастям, где в name есть марка/модель
    if brand or model:
        matching = [o for o in all_offers if _matches_car(o.name, brand, model)]
        if matching:
            all_offers = matching

    return [_offer_to_dict(o) for o in all_offers[:limit]]


async def search_by_sku_oem(
    sku_or_oem: str,
    db: AsyncSession,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Точный поиск по артикулу/OEM."""
    repo = PartsRepository(db)
    offers = await repo.compare(sku=None, oem=sku_or_oem)
    if not offers:
        offers = await repo.compare(sku=sku_or_oem, oem=None)
    return [_offer_to_dict(o) for o in offers[:limit]]


def _offer_to_dict(o: Any) -> dict[str, Any]:
    return {
        "id": str(o.id),
        "name": o.name or "Запчасть",
        "brand": o.brand,
        "sku": o.sku,
        "oem": o.oem,
        "price": float(o.price) if o.price is not None else None,
        "stock": o.stock,
        "delivery_days": o.delivery_days,
        "in_stock": (o.stock or 0) > 0,
        "supplier_id": str(o.supplier_id),
        "supplier_priority": 5,
        "is_oem": _is_oem_brand(o.brand),
    }


def _is_oem_brand(brand: str | None) -> bool:
    if not brand:
        return False
    return brand.lower() in ("toyota", "kia", "vw", "volkswagen", "honda", "bmw", "mercedes", "hyundai")


def rank_and_tier(
    parts: list[dict[str, Any]],
    car_brand: str | None = None,
    car_model: str | None = None,
    weights: dict[str, float] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Ранжирует и разбивает на 3 тира: economy, optimal, oem."""
    if not weights:
        weights = {"price": 0.4, "delivery": 0.3, "stock": 0.2, "supplier_priority": 0.1}

    if not parts:
        return {"economy": [], "optimal": [], "oem": []}

    max_price = max((p.get("price") or 0) for p in parts) or 1
    max_delivery = max((p.get("delivery_days") or 7) for p in parts) or 1

    def score(p: dict) -> float:
        price_score = 1 - ((p.get("price") or 0) / max_price)
        delivery_score = 1 - ((p.get("delivery_days") or 7) / max_delivery)
        stock_score = 1.0 if p.get("in_stock") else 0.0
        supplier_score = (p.get("supplier_priority", 5) or 5) / 10
        return (
            weights["price"] * price_score
            + weights["delivery"] * delivery_score
            + weights["stock"] * stock_score
            + weights["supplier_priority"] * supplier_score
        )

    ranked = sorted(parts, key=score, reverse=True)

    economy = sorted(parts, key=lambda p: p.get("price") or 99999)[:3]
    optimal = ranked[:3]
    brand_lower = (car_brand or "").lower()
    model_lower = (car_model or "").lower()

    def _is_oem_fit(p: dict) -> bool:
        if p.get("is_oem"):
            return True
        if brand_lower and str(p.get("brand", "")).lower() == brand_lower:
            return True
        name = (p.get("name") or "").lower()
        if model_lower and model_lower in name:
            return True
        if brand_lower and brand_lower in name:
            return True
        return False

    oem_candidates = [p for p in parts if _is_oem_fit(p)]
    oem = oem_candidates[:3] if oem_candidates else optimal[:1]

    return {"economy": economy, "optimal": optimal, "oem": oem}
