from datetime import UTC, datetime

from sangkat_bot.db import (
    audit,
    emergency_numbers,
    get_commune,
    get_service,
    get_user_commune,
    insert_announcement,
    last_admin_announcement,
    latest_announcements,
    list_active_communes,
    local_contacts,
    mark_deleted,
    public_services,
    set_announcement_messages,
    set_group,
    upsert_user,
)
from sangkat_bot.seed import run_seed

from .conftest import DATAEF, SEED

NOW = datetime(2026, 11, 21, 12, tzinfo=UTC)


def test_counts(conn):
    c = run_seed(conn, DATAEF, SEED)
    assert c["provinces"] == 25 and c["districts"] == 210 and c["communes"] == 1661
    assert c["villages"] == 16 and c["emergency_numbers"] == 5 and c["local_contacts"] == 10
    assert c["public_services"] == 3 and c["seed_announcements"] == 4


def test_codes_are_zero_padded_and_type_set(conn):
    assert get_commune(conn, "010201")["commune_en"] == "Banteay Neang"
    tb = get_commune(conn, "120101")
    assert tb["commune_kh"] == "ទន្លេបាសាក់" and tb["commune_type"] == "sangkat" and tb["is_active"] == 1
    assert tb["district_kh"] == "ចំការមន" and tb["province_code"] == "12"


def test_unknown_commune_is_none(conn):
    assert get_commune(conn, "999999") is None


def test_active_communes_is_demo_only(conn):
    assert [r["commune_code"] for r in list_active_communes(conn)] == ["120101"]


def test_666_only_in_phnom_penh(conn):
    assert "666" in [r["number"] for r in emergency_numbers(conn, "12")]
    assert "666" not in [r["number"] for r in emergency_numbers(conn, "01")]
    assert "115" not in [r["number"] for r in emergency_numbers(conn, "12")]  # inactive


def test_emergency_numbers_sorted(conn):
    assert [r["number"] for r in emergency_numbers(conn, "12")] == ["117", "118", "119", "666"]


def test_inactive_contacts_hidden(conn):
    names = [r["name_en"] for r in local_contacts(conn, "120101", ["health_center", "police"])]
    assert "Health Center (TBD)" not in names
    assert "Tonle Basak Administrative Police Post" not in names


def test_contacts_ordered_by_category_then_sort(conn):
    rows = local_contacts(conn, "120101", ["fire", "police"])
    assert [r["category"] for r in rows] == ["fire", "fire", "police"]
    assert rows[0]["name_en"] == "Phnom Penh Fire Brigade"


def test_only_24h_filter(conn):
    names = [r["name_en"] for r in local_contacts(conn, "120101", ["hospital"], only_24h=True)]
    assert "Calmette Hospital" in names and "Preah Ang Duong Hospital" not in names


def test_services_include_national_defaults(conn):
    assert [r["service_key"] for r in public_services(conn, "120101")] == [
        "birth_certificate",
        "residence_certificate",
        "residence_book",
    ]
    assert get_service(conn, "birth_certificate")["title_kh"] == "សំបុត្រកំណើត"
    assert get_service(conn, "nope") is None


def test_user_binding(conn):
    assert get_user_commune(conn, 42) is None
    upsert_user(conn, 42, "120101")
    upsert_user(conn, 42, "120101")
    assert get_user_commune(conn, 42) == "120101"


def test_reseed_preserves_group_users_and_admin_posts(conn):
    set_group(conn, "120101", -100123)
    upsert_user(conn, 5, "120101")
    insert_announcement(
        conn, commune_code="120101", source="admin", posted_by=5, text_kh="x",
        photo_file_id=None, voice_file_id=None, event_date=None, expires_at=None, created_at=NOW,
    )
    c = run_seed(conn, DATAEF, SEED)
    assert get_commune(conn, "120101")["telegram_group_id"] == -100123
    assert get_user_commune(conn, 5) == "120101" and c["seed_announcements"] == 4
    assert conn.execute("select count(*) from announcements where source='admin'").fetchone()[0] == 1


def test_latest_hides_expired_across_timezones(conn):
    # seed row "ID card" expires 2026-11-28T12:00+07:00 == 05:00 UTC
    before = datetime(2026, 11, 28, 4, 59, tzinfo=UTC)
    after = datetime(2026, 11, 28, 5, 1, tzinfo=UTC)
    assert any("អត្តសញ្ញាណប័ណ្ណ" in r["text_kh"] for r in latest_announcements(conn, "120101", before))
    assert not any("អត្តសញ្ញាណប័ណ្ណ" in r["text_kh"] for r in latest_announcements(conn, "120101", after))


def test_latest_is_three_oldest_first(conn):
    rows = latest_announcements(conn, "120101", NOW)
    assert len(rows) == 3
    assert [r["created_at"] for r in rows] == sorted(r["created_at"] for r in rows)
    assert not any("អុំទូក" in r["text_kh"] for r in rows)  # expired water-festival item


def test_latest_keeps_newest_three(conn):
    newer = datetime(2026, 11, 21, 11, tzinfo=UTC)
    ann = insert_announcement(
        conn, commune_code="120101", source="admin", posted_by=5, text_kh="ថ្មីបំផុត",
        photo_file_id="P", voice_file_id="V", event_date=None, expires_at=None, created_at=newer,
    )
    rows = latest_announcements(conn, "120101", NOW)
    assert len(rows) == 3 and rows[-1]["id"] == ann and rows[-1]["voice_file_id"] == "V"


def test_deleted_hidden(conn):
    rid = latest_announcements(conn, "120101", NOW)[-1]["id"]
    mark_deleted(conn, rid)
    assert rid not in [r["id"] for r in latest_announcements(conn, "120101", NOW)]


def test_last_admin_announcement_and_messages(conn):
    assert last_admin_announcement(conn, "120101", 5) is None
    ann = insert_announcement(
        conn, commune_code="120101", source="admin", posted_by=5, text_kh="a",
        photo_file_id=None, voice_file_id=None, event_date=None, expires_at=None, created_at=NOW,
    )
    set_announcement_messages(conn, ann, 10, 11)
    row = last_admin_announcement(conn, "120101", 5)
    assert row["id"] == ann and row["group_message_id"] == 10 and row["group_voice_message_id"] == 11
    mark_deleted(conn, ann)
    assert last_admin_announcement(conn, "120101", 5) is None


def test_audit_keeps_khmer(conn):
    audit(conn, 5, "120101", "publish", "1", {"note": "ដំណឹង"})
    stored = conn.execute("select metadata_json from audit_logs").fetchone()[0]
    assert "ដំណឹង" in stored


def test_hide_seed_duplicates_only_hides_matching_seed_rows(conn):
    from sangkat_bot.db import hide_seed_duplicates

    text = conn.execute("select text_kh from announcements where source='seed' and text_kh like '%សំរាម%'").fetchone()[0]
    assert hide_seed_duplicates(conn, "120101", text) == 1
    assert conn.execute("select is_deleted from announcements where text_kh = ?", (text,)).fetchone()[0] == 1
    assert conn.execute("select count(*) from announcements where source='seed' and is_deleted=0").fetchone()[0] == 3


def test_unposted_admin_announcement_finds_feed_only_item(conn):
    from datetime import UTC, datetime

    from sangkat_bot.db import insert_announcement, set_announcement_messages, unposted_admin_announcement

    assert unposted_admin_announcement(conn, "120101", "news") is None
    ann = insert_announcement(conn, commune_code="120101", source="admin", posted_by=1, text_kh="news",
                              photo_file_id="P", voice_file_id="V", event_date=None, expires_at=None,
                              created_at=datetime.now(UTC))
    assert unposted_admin_announcement(conn, "120101", "news")["id"] == ann
    set_announcement_messages(conn, ann, 10, 11)
    assert unposted_admin_announcement(conn, "120101", "news") is None
