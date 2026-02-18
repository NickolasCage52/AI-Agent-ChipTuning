from app.telegram import parse_update


def test_parse_update_message():
    upd = {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "text": "Привет",
            "from": {"id": 123, "first_name": "Ivan", "username": "ivan"},
            "chat": {"id": 456, "type": "private"},
        },
    }
    msg = parse_update(upd)
    assert msg is not None
    assert msg.tg_id == 123
    assert msg.chat_id == 456
    assert msg.text == "Привет"
    assert msg.name == "Ivan"


def test_parse_update_ignores_non_text():
    upd = {"update_id": 2, "message": {"message_id": 11, "from": {"id": 1}, "chat": {"id": 2}}}
    assert parse_update(upd) is None

