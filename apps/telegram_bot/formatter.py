"""Форматирование ответов для Telegram."""
from __future__ import annotations


def format_clarification(summary: str, questions: list[dict]) -> str:
    lines = []
    if summary:
        lines.append(f"🔍 <b>Понял:</b> {summary}\n")
    lines.append("❓ <b>Уточните, пожалуйста:</b>")
    for i, q in enumerate(questions[:2], 1):
        text = q.get("text", "") if isinstance(q, dict) else str(q)
        lines.append(f"{i}. {text}")
    return "\n".join(lines)


def format_results(
    summary: str,
    part_type: str,
    car_context: dict,
    tiers: dict,
    safety_notes: list[str] | None = None,
) -> str:
    safety_notes = safety_notes or []
    car_str = _format_car(car_context)
    lines = []

    if summary:
        lines.append(f"🔍 <b>Понял запрос:</b> {summary}")
    if car_str:
        lines.append(f"🚗 <b>Авто:</b> {car_str}\n")

    lines.append(f"📦 <b>Варианты по запросу: {part_type}</b>\n")

    tier_configs = [
        ("economy", "🟢", "Эконом"),
        ("optimal", "🟡", "Оптимум"),
        ("oem", "🔵", "OEM / Оригинал"),
    ]

    for key, emoji, label in tier_configs:
        items = tiers.get(key, [])
        lines.append(f"{emoji} <b>{label}:</b>")
        if not items:
            lines.append("  — нет вариантов")
        else:
            for item in items[:3]:
                price = f"{item.get('price', '?')} ₽" if item.get('price') else "цена по запросу"
                delivery = f"{item.get('delivery_days', '?')} дн." if item.get('delivery_days') else ""
                stock = "✓ есть" if item.get('in_stock') else "под заказ"
                brand = item.get("brand", "")
                name = item.get("display_name") or item.get("name") or item.get("part_type", "")
                lines.append(
                    f"  • <b>{name}</b> {brand}\n"
                    f"    💰 {price} | 🚚 {delivery} | {stock}"
                )
        lines.append("")

    if safety_notes:
        for note in safety_notes:
            lines.append(f"⚠️ <i>{note}</i>")
        lines.append("")

    lines.append("👇 <b>Что дальше?</b> Выберите вариант или напишите новый запрос.")
    return "\n".join(lines)


def _format_car(ctx: dict) -> str:
    parts = [ctx.get("brand", ""), ctx.get("model", ""), str(ctx.get("year", "") or "")]
    engine = ctx.get("engine", "")
    result = " ".join(p for p in parts if p)
    if engine:
        result += f", {engine}"
    return result
