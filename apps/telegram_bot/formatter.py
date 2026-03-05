"""Форматирование ответов для Telegram (PriceItem из прайсов)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.price_search import PriceItem


def format_item(item: Any, num: int) -> str:
    """Форматирование одной позиции."""
    if hasattr(item, "display_price"):
        defect_mark = " 🔸<i>Некондиция</i>" if getattr(item, "is_defect", False) else ""
        brand = f"<b>{item.brand}</b>" if item.brand else ""
        article = f"арт. {item.article_raw or item.article}" if (item.article_raw or item.article) else ""
        desc = (item.description or item.nomenclature or "")[:60]
        return (
            f"  {num}. {brand} {article}{defect_mark}\n"
            f"     {desc}\n"
            f"     💰 {item.display_price} | 🚚 {item.display_delivery} | {item.display_stock}"
        )
    defect_mark = " 🔸<i>Некондиция</i>" if item.get("is_defect") else ""
    brand = f"<b>{item.get('brand', '')}</b>" if item.get("brand") else ""
    art = item.get("article_raw") or item.get("article", "")
    article = f"арт. {art}" if art else ""
    desc = (item.get("description") or item.get("nomenclature") or "")[:60]
    price = f"{item.get('price', 0):,.0f} ₽".replace(",", " ") if item.get("price") else "цена по запросу"
    delivery = (
        f"{item.get('delivery_days', 0)} дн." if item.get("delivery_days") else "уточнить"
    )
    instock = str(item.get("in_stock", "")).lower()
    stock = (
        "✓ есть"
        if instock in ("да", "есть", "в наличии") or (instock.isdigit() and int(instock) > 0)
        else "под заказ"
    )
    return (
        f"  {num}. {brand} {article}{defect_mark}\n"
        f"     {desc}\n"
        f"     💰 {price} | 🚚 {delivery} | {stock}"
    )


def format_tier(emoji: str, label: str, items: list[Any]) -> str:
    """Форматирование тира."""
    if not items:
        return f"{emoji} <b>{label}:</b>\n  — нет подходящих позиций\n"
    lines = [f"{emoji} <b>{label}:</b>"]
    for i, item in enumerate(items[:3], 1):
        lines.append(format_item(item, i))
    return "\n".join(lines) + "\n"


def format_results(
    summary: str,
    part_type: str,
    tiers: dict[str, list[Any]],
    safety_note: str = "",
) -> str:
    """Сборка ответа с 3 тирами."""
    economy = tiers.get("economy", [])
    optimal = tiers.get("optimal", [])
    oem = tiers.get("oem", [])

    parts = [f"🔍 <b>Понял:</b> {summary}"]
    if part_type:
        parts.append(f"📦 Ищу: <i>{part_type}</i>\n")
    parts.append("─" * 30)
    parts.append(format_tier("🟢", "Economy (дешевле)", economy))
    parts.append(format_tier("🟡", "Optimal (баланс)", optimal))
    if oem:
        parts.append(format_tier("🔵", "OEM / Оригинал", oem))
    else:
        parts.append("🔵 <b>OEM / Оригинал:</b>\n  — OEM-позиции не выделены в прайсе\n")
    if safety_note:
        parts.append(f"\n⚠️ <i>{safety_note}</i>")
    parts.append("\n👇 <b>Выберите вариант или напишите новый запрос:</b>")
    return "\n".join(parts)


def format_clarification(summary: str, questions: list[Any]) -> str:
    """Форматирование уточняющих вопросов."""
    lines = []
    if summary:
        lines.append(f"🔍 <b>Понял:</b> {summary}\n")
    lines.append("📋 <b>Для лучшего подбора нужна информация:</b>")
    for i, q in enumerate(questions[:2], 1):
        text = q.get("text", "") if isinstance(q, dict) else str(q)
        lines.append(f"{i}. {text}")
    lines.append("\n<i>Отвечайте по пунктам — это поможет найти точные позиции в прайсе.</i>")
    return "\n".join(lines)


def format_no_results(part_type: str) -> str:
    """Сообщение при отсутствии результатов."""
    return (
        f"😔 По запросу <i>{part_type}</i> ничего не найдено в прайсах.\n\n"
        "Попробуйте:\n"
        "• Указать точный артикул или OEM-номер\n"
        "• Написать название другими словами\n"
        "• Уточнить бренд\n\n"
        "Или напишите /reset для нового поиска."
    )
