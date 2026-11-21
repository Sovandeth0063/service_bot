import html

from sangkat_bot.copy import commune_type_kh
from sangkat_bot.db import emergency_numbers, get_commune, get_service, local_contacts
from sangkat_bot.formatting import (
    contact_block,
    emergency_card,
    format_phone,
    hall_card,
    health_card,
    service_card,
)
from sangkat_bot.keywords import INTENTS


def test_copy_fills_sangkat(copy_tb):
    assert copy_tb.button("location") == "📍 សាលាសង្កាត់"
    assert copy_tb.t("welcome").startswith("សួស្តី! នេះជាជំនួយការរបស់សង្កាត់ទន្លេបាសាក់")


def test_copy_khum_default():
    assert commune_type_kh(None) == "ឃុំ" and commune_type_kh("sangkat") == "សង្កាត់"


def test_copy_dotted_key(copy_tb):
    assert copy_tb.t("admin.publish") == "✅ ផ្សាយ"


def test_button_intent_roundtrip(copy_tb):
    for intent in INTENTS:
        assert copy_tb.button_intent(copy_tb.button(intent)) == intent
    assert copy_tb.button_intent("random") is None


def test_format_phone_splits():
    assert format_phone("666 | 012 786 693") == ["666", "012 786 693"]


def test_format_phone_empty():
    assert format_phone(None) == [] and format_phone("") == [] and format_phone(" | ") == []


def test_missing_phone_says_verifying(conn, copy_tb):
    row = [r for r in local_contacts(conn, "120101", ["hospital"]) if r["name_en"] == "Preah Ang Duong Hospital"][0]
    block = contact_block(row, copy_tb)
    assert copy_tb.t("phone_missing") in block and copy_tb.t("map_link") in block


def test_phone_lines_each_on_own_line(conn, copy_tb):
    row = local_contacts(conn, "120101", ["fire"])[0]
    lines = contact_block(row, copy_tb).splitlines()
    assert "📞 666" in lines and "📞 012 786 693" in lines


def test_emergency_card_has_national_and_local(conn, copy_tb):
    local = local_contacts(conn, "120101", ["police", "fire", "ambulance"]) + local_contacts(
        conn, "120101", ["hospital"], only_24h=True
    )
    card = emergency_card(emergency_numbers(conn, "12"), local, copy_tb, demo_mode=True)
    assert "117" in card and "666" in card and "កាល់ម៉ែត" in card and "Calmette" not in card
    assert card.endswith(f"<i>{html.escape(copy_tb.t('demo_footer'))}</i>")


def test_health_card_lists_hospitals(conn, copy_tb):
    card = health_card(local_contacts(conn, "120101", ["health_center", "hospital"]), copy_tb, demo_mode=False)
    assert card.startswith(f"<b>{copy_tb.t('health_header')}</b>")
    assert card.index("កាល់ម៉ែត") < card.index("មិត្តភាព")  # sort_order kept
    assert copy_tb.t("hours_24h") in card


def test_no_demo_footer_when_off(conn, copy_tb):
    assert copy_tb.t("demo_footer") not in hall_card(get_commune(conn, "120101"), copy_tb, demo_mode=False)


def test_hall_card_contents(conn, copy_tb):
    card = hall_card(get_commune(conn, "120101"), copy_tb, demo_mode=True)
    assert "សាលាសង្កាត់ទន្លេបាសាក់" in card and "7:30" in card and copy_tb.t("phone_missing") in card
    assert "google.com/maps" in card


def test_html_is_escaped(copy_tb):
    row = {"name_kh": "<b>x</b>", "phone_numbers": "", "operating_hours_kh": None, "is_24h": 0, "google_maps_url": None}
    assert "&lt;b&gt;" in contact_block(row, copy_tb)


def test_service_card_checklist(conn, copy_tb):
    card = service_card(get_service(conn, "birth_certificate"), copy_tb)
    assert card.count("☐") == 4 and "សាលាសង្កាត់" in card and "សូមសួរសាលាសង្កាត់" in card
