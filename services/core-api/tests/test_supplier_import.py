from app.supplier_import import parse_supplier_price


def test_parse_supplier_price_csv_aliases():
    csv_bytes = (
        "Артикул;OEM;Наименование;Бренд;Цена;Наличие;Срок\n"
        "ABC123;12345;Тормозные колодки;ATE;3500;5;2\n"
    ).encode("utf-8")

    offers = parse_supplier_price("price.csv", csv_bytes)
    assert len(offers) == 1
    o = offers[0]
    assert o.sku == "ABC123"
    assert o.oem == "12345"
    assert o.name == "Тормозные колодки"
    assert o.brand == "ATE"
    assert str(o.price) == "3500"
    assert o.stock == 5
    assert o.delivery_days == 2

