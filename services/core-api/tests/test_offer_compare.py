from app.offer_compare import rank_offers


def test_rank_offers_prefers_in_stock_then_price_then_delivery():
    offers = [
        {"price": 1000, "stock": 0, "delivery_days": 1, "name": "A"},
        {"price": 1200, "stock": 5, "delivery_days": 5, "name": "B"},
        {"price": 1100, "stock": 5, "delivery_days": 2, "name": "C"},
        {"price": 900, "stock": 0, "delivery_days": 2, "name": "D"},
    ]

    ranked = rank_offers(offers)
    assert [o["name"] for o in ranked] == ["C", "B", "D", "A"]

