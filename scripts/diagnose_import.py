#!/usr/bin/env python3
"""Диагностика импорта прайсов — статистика и качество данных."""
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "data/parts.db")

def main():
    if not os.path.exists(DB_PATH):
        print(f"БД не найдена: {DB_PATH}. Запустите scripts/import_prices.py")
        return

    conn = sqlite3.connect(DB_PATH)
    print("=== СТАТИСТИКА ПРАЙСА ===")
    for table in ["products", "products_defect"]:
        try:
            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            no_price = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE price IS NULL OR price = 0").fetchone()[0]
            no_days = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE delivery_days IS NULL").fetchone()[0]
            no_stock = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE in_stock IS NULL OR in_stock = ''").fetchone()[0]
            fake_99 = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE delivery_days = 99").fetchone()[0]
            pct = (no_price / total * 100) if total else 0
            print(f"\n{table}:")
            print(f"  Всего строк: {total}")
            print(f"  Без цены: {no_price} ({pct:.1f}%)")
            print(f"  Без срока: {no_days}")
            print(f"  Без наличия: {no_stock}")
            print(f"  С '99 дней': {fake_99} {'<- ПРОБЛЕМА' if fake_99 > 0 else ''}")
        except Exception as e:
            print(f"  {table}: {e}")

    print("\n=== ОБРАЗЦЫ ДАННЫХ ===")
    try:
        rows = conn.execute("SELECT brand, article_raw, price, delivery_days, in_stock FROM products LIMIT 5").fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print(f"Ошибка: {e}")
    conn.close()

if __name__ == "__main__":
    main()
