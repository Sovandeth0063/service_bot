from sangkat_bot.db import list_active_communes, public_services
from sangkat_bot.handlers.resident import resolve_commune, resolve_intent
from sangkat_bot.keyboards import commune_picker, open_bot_button, resident_keyboard, services_menu

A = {"120101"}


def test_payload_wins():
    assert resolve_commune("120101", None, A) == "120101"


def test_payload_with_spaces():
    assert resolve_commune(" 120101 ", None, A) == "120101"


def test_invalid_payload_falls_back_to_stored():
    assert resolve_commune("999999", "120101", A) == "120101"


def test_no_binding_needs_picker():
    assert resolve_commune(None, None, A) is None


def test_inactive_stored_needs_picker():
    assert resolve_commune(None, "010201", A) is None


def test_button_label_beats_keywords(copy_tb, keywords):
    assert resolve_intent(copy_tb.button("health"), copy_tb, keywords) == "health"


def test_typed_text_uses_keywords(copy_tb, keywords):
    assert resolve_intent("ភ្លើងឆេះ", copy_tb, keywords) == "emergency"


def test_unknown_text_is_none(copy_tb, keywords):
    assert resolve_intent("hello", copy_tb, keywords) is None


def test_keyboard_layout(copy_tb):
    kb = resident_keyboard(copy_tb, is_admin=False)
    assert [len(row) for row in kb.keyboard] == [1, 2, 2] and kb.is_persistent and kb.resize_keyboard
    assert kb.keyboard[0][0].text == "🚨 សង្គ្រោះបន្ទាន់"
    admin_kb = resident_keyboard(copy_tb, is_admin=True)
    assert len(admin_kb.keyboard) == 4 and admin_kb.keyboard[3][0].text == copy_tb.t("admin.announce_button")


def test_commune_picker(conn):
    picker = commune_picker(list_active_communes(conn))
    button = picker.inline_keyboard[0][0]
    assert button.callback_data == "pick:120101" and "ទន្លេបាសាក់" in button.text and "ចំការមន" in button.text


def test_services_menu(conn):
    menu = services_menu(public_services(conn, "120101"))
    assert [row[0].callback_data for row in menu.inline_keyboard] == [
        "svc:birth_certificate",
        "svc:residence_certificate",
        "svc:residence_book",
    ]


def test_open_bot_button(copy_tb):
    button = open_bot_button(copy_tb, "SangkatBot", "120101").inline_keyboard[0][0]
    assert button.url == "https://t.me/SangkatBot?start=120101" and button.text == copy_tb.t("open_bot_button")
