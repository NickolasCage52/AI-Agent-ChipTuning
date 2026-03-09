"""Поиск по таблицам прайса в SQLite. Единственный источник — два файла прайса."""
from __future__ import annotations

import math
import os
import re
import sqlite3
from dataclasses import dataclass, asdict
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DB_PATH", os.path.join(ROOT, "data", "parts.db"))

NOT_IN_PRICELIST = "не указано в прайсе"


@dataclass
class PriceItem:
    id: int
    nomenclature: str
    brand: str
    article: str
    description: str
    price: float | None
    in_stock: str
    delivery_days: int | None
    catalog_number: str
    oem_number: str
    article_raw: str = ""
    is_defect: bool = False
    applicability: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @property
    def display_price(self) -> str:
        if self.price is not None and self.price > 0:
            return f"{self.price:,.0f} ₽".replace(",", " ")
        return NOT_IN_PRICELIST

    @property
    def display_delivery(self) -> str:
        if self.delivery_days is None or self.delivery_days < 0:
            return NOT_IN_PRICELIST
        if self.delivery_days <= 1:
            return "1 день (склад)"
        if self.delivery_days <= 3:
            return f"{self.delivery_days} дня"
        return f"{self.delivery_days} дней"

    @property
    def display_stock(self) -> str:
        if not self.in_stock:
            return NOT_IN_PRICELIST
        s = str(self.in_stock).strip().lower()
        if s.isdigit() and int(s) > 0:
            return "✓ есть"
        if any(x in s for x in ["да", "есть", "в наличии", "true", "yes"]):
            return "✓ есть"
        if any(x in s for x in ["нет", "0", "false", "no", "отсутствует"]):
            return "под заказ"
        return self.in_stock


def normalize_article(raw: str) -> str:
    if not raw:
        return ""
    return re.sub(r"[\s\-_]", "", str(raw)).upper()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_item(row: sqlite3.Row, is_defect: bool = False) -> PriceItem:
    keys = row.keys()
    def _val(k: str, default: str = "") -> str:
        try:
            v = row[k]
            return str(v) if v is not None else default
        except (IndexError, KeyError):
            return default
    return PriceItem(
        id=row["id"],
        nomenclature=_val("nomenclature"),
        brand=_val("brand"),
        article=_val("article"),
        description=_val("description"),
        price=float(row["price"]) if row["price"] is not None else None,
        in_stock=_val("in_stock"),
        delivery_days=int(row["delivery_days"]) if row["delivery_days"] is not None else None,
        catalog_number=_val("catalog_number"),
        oem_number=_val("oem_number"),
        article_raw=_val("article_raw"),
        is_defect=is_defect,
        applicability=_val("applicability") or None if is_defect and "applicability" in keys else None,
    )


def search(
    query: str = "",
    article: str = "",
    oem: str = "",
    brand: str = "",
    max_results: int = 50,
) -> list[PriceItem]:
    """
    Агрегированный поиск по обоим прайсам.
    Приоритет: точный артикул > OEM/каталожный > нечёткий по названию/описанию.
    При точном поиске по артикулу возвращает ВСЕ найденные позиции из обоих прайсов.
    """
    conn = get_connection()
    results: list[PriceItem] = []

    # Точный артикул — без лимита, чтобы вернуть все позиции из обоих прайсов
    article_limit = 500 if article and not query else max_results
    if article:
        norm = normalize_article(article)
        for table, is_def in [("products", False), ("products_defect", True)]:
            try:
                rows = conn.execute(
                    f"SELECT * FROM {table} WHERE article = ? OR article_raw = ? LIMIT ?",
                    (norm, article.strip(), article_limit),
                ).fetchall()
                results.extend(_row_to_item(r, is_def) for r in rows)
            except sqlite3.OperationalError:
                pass

    if oem:
        norm_oem = normalize_article(oem)
        for table, is_def in [("products", False), ("products_defect", True)]:
            try:
                rows = conn.execute(
                    f"""SELECT * FROM {table}
                        WHERE REPLACE(REPLACE(REPLACE(oem_number,' ',''),'-',''),'_','') = ?
                           OR REPLACE(REPLACE(REPLACE(catalog_number,' ',''),'-',''),'_','') = ?
                        LIMIT ?""",
                    (norm_oem, norm_oem, max_results),
                ).fetchall()
                results.extend(_row_to_item(r, is_def) for r in rows)
            except sqlite3.OperationalError:
                pass

    if query and len(results) < 5:
        stopwords = {"на", "для", "и", "в", "с", "по", "из", "к", "от", "у", "о", "об", "что", "какой"}
        terms = [t for t in query.lower().split() if t not in stopwords and len(t) > 1]
        if not terms:
            terms = [query.lower()[:30].strip()]
        for table, is_def in [("products", False), ("products_defect", True)]:
            try:
                conditions = " AND ".join(
                    "(LOWER(nomenclature) LIKE ? OR LOWER(description) LIKE ? OR LOWER(brand) LIKE ?)"
                    for _ in terms
                )
                params: list[Any] = []
                for t in terms:
                    params.extend([f"%{t}%", f"%{t}%", f"%{t}%"])
                params.append(max_results)
                rows = conn.execute(
                    f"SELECT * FROM {table} WHERE {conditions} LIMIT ?", params
                ).fetchall()
                results.extend(_row_to_item(r, is_def) for r in rows)
            except sqlite3.OperationalError:
                pass

    if brand and results:
        brand_lower = brand.lower()
        brand_filtered = [r for r in results if brand_lower in r.brand.lower()]
        if brand_filtered:
            results = brand_filtered

    seen: set[tuple[int, bool]] = set()
    unique: list[PriceItem] = []
    for item in results:
        key = (item.id, item.is_defect)
        if key not in seen:
            seen.add(key)
            unique.append(item)

    conn.close()
    return unique


def build_tiers(items: list[PriceItem]) -> dict[str, list[PriceItem]]:
    """
    Собирает 3 тира из списка найденных позиций.
    Возвращает dict с ключами: economy, optimal, oem.
    Если найдена только одна позиция — она в Optimal, остальные тиры пустые.
    """
    if not items:
        return {"economy": [], "optimal": [], "oem": []}

    # Одна позиция — показываем только в Optimal
    if len(items) == 1:
        return {"economy": [], "optimal": items.copy(), "oem": []}

    normal = [i for i in items if not i.is_defect]
    OEM_BRANDS = {
        "toyota", "honda", "kia", "hyundai", "volkswagen", "bmw", "mercedes",
        "ford", "nissan", "mazda", "subaru", "mitsubishi", "suzuki", "original",
        "oem", "оригинал", "denso", "bosch", "trw", "akebono", "brembo",
    }

    oem_items = [
        i for i in normal
        if i.oem_number or i.catalog_number
        or any(b in i.brand.lower() for b in OEM_BRANDS)
    ]

    economy_pool = sorted(
        [i for i in items if i.price is not None and i.price > 0],
        key=lambda x: (x.price, x.delivery_days if x.delivery_days is not None else math.inf),
    )

    def optimal_score(item: PriceItem) -> float:
        price_score = (item.price / 1000) if item.price and item.price > 0 else 999.0
        delivery_score = (item.delivery_days * 0.5) if item.delivery_days is not None and item.delivery_days >= 0 else 30.0
        stock_bonus = -2 if "✓" in item.display_stock else 0
        defect_penalty = 1 if item.is_defect else 0
        return price_score + delivery_score + stock_bonus + defect_penalty

    optimal_pool = sorted(items, key=optimal_score)

    return {
        "economy": economy_pool[:3],
        "optimal": optimal_pool[:3],
        "oem": oem_items[:3] if oem_items else [],
    }
