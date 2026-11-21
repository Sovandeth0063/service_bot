"""SQLite access. Every query the bot runs lives here, so a move to PostgreSQL touches one file."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

Row = sqlite3.Row


def utc_iso(moment: datetime) -> str:
    """Store timestamps as UTC ISO-8601 so string comparison orders them correctly."""
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def connect(db_path: Path) -> sqlite3.Connection:
    """Open the database, enable foreign keys and create any missing tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(resources.files("sangkat_bot").joinpath("schema.sql").read_text(encoding="utf-8"))
    _add_missing_columns(conn)
    return conn


def _add_missing_columns(conn: sqlite3.Connection) -> None:
    """Bring a database made by an older version up to date (CREATE TABLE IF NOT EXISTS won't)."""
    have = {row["name"] for row in conn.execute("PRAGMA table_info(announcements)")}
    for column in ("photo_path", "voice_path", "publish_id", "location_url"):
        if column not in have:
            conn.execute(f"ALTER TABLE announcements ADD COLUMN {column} TEXT")
    conn.commit()


_COMMUNE_SELECT = """
    SELECT c.commune_code, c.commune_kh, c.commune_en, c.province_code, c.commune_type,
           d.district_kh, d.district_en, p.province_kh, p.province_en,
           cc.hall_name_kh, cc.hall_phone, cc.office_days_kh, cc.office_hours_kh, cc.address_kh,
           cc.lat, cc.lon, cc.google_maps_url, cc.telegram_group_id,
           COALESCE(cc.is_active, 0) AS is_active, cc.verification_status
    FROM communes c
    JOIN districts d ON d.district_code = c.district_code
    JOIN provinces p ON p.province_code = c.province_code
    LEFT JOIN commune_configs cc ON cc.commune_code = c.commune_code
"""


def get_commune(conn: sqlite3.Connection, code: str) -> Row | None:
    return conn.execute(_COMMUNE_SELECT + " WHERE c.commune_code = ?", (code,)).fetchone()


def list_active_communes(conn: sqlite3.Connection) -> list[Row]:
    return conn.execute(_COMMUNE_SELECT + " WHERE cc.is_active = 1 ORDER BY c.commune_code").fetchall()


def upsert_user(conn: sqlite3.Connection, user_id: int, commune_code: str) -> None:
    now = utc_iso(datetime.now(UTC))
    conn.execute(
        """INSERT INTO users (telegram_user_id, commune_code, first_seen_at, last_active_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT (telegram_user_id) DO UPDATE
           SET commune_code = excluded.commune_code, last_active_at = excluded.last_active_at""",
        (user_id, commune_code, now, now),
    )
    conn.commit()


def get_user_commune(conn: sqlite3.Connection, user_id: int) -> str | None:
    row = conn.execute("SELECT commune_code FROM users WHERE telegram_user_id = ?", (user_id,)).fetchone()
    return row["commune_code"] if row else None


def emergency_numbers(conn: sqlite3.Connection, province_code: str) -> list[Row]:
    return conn.execute(
        """SELECT * FROM emergency_numbers
           WHERE is_active = 1 AND (scope = 'national' OR scope = ?)
           ORDER BY sort_order""",
        (f"province:{province_code}",),
    ).fetchall()


def local_contacts(
    conn: sqlite3.Connection, commune_code: str, categories: Sequence[str], only_24h: bool = False
) -> list[Row]:
    """Active contacts in the given categories, grouped in the order the categories were passed."""
    if not categories:
        return []
    marks = ",".join("?" for _ in categories)
    rows = conn.execute(
        f"""SELECT * FROM local_contacts
            WHERE commune_code = ? AND is_active = 1 AND category IN ({marks})
            {"AND is_24h = 1" if only_24h else ""}
            ORDER BY sort_order, id""",
        (commune_code, *categories),
    ).fetchall()
    rank = {category: index for index, category in enumerate(categories)}
    return sorted(rows, key=lambda row: rank[row["category"]])


def public_services(conn: sqlite3.Connection, commune_code: str) -> list[Row]:
    return conn.execute(
        """SELECT * FROM public_services
           WHERE is_active = 1 AND (commune_code = ? OR commune_code IS NULL)
           ORDER BY sort_order, id""",
        (commune_code,),
    ).fetchall()


def get_service(conn: sqlite3.Connection, service_key: str) -> Row | None:
    return conn.execute(
        "SELECT * FROM public_services WHERE service_key = ? AND is_active = 1", (service_key,)
    ).fetchone()


def set_group(conn: sqlite3.Connection, commune_code: str, group_id: int) -> None:
    conn.execute("UPDATE commune_configs SET telegram_group_id = NULL WHERE telegram_group_id = ?", (group_id,))
    conn.execute(
        "UPDATE commune_configs SET telegram_group_id = ? WHERE commune_code = ?", (group_id, commune_code)
    )
    conn.commit()


def commune_for_group(conn: sqlite3.Connection, group_id: int) -> str | None:
    row = conn.execute("SELECT commune_code FROM commune_configs WHERE telegram_group_id = ?", (group_id,)).fetchone()
    return row["commune_code"] if row else None


def unposted_admin_announcement(conn: sqlite3.Connection, commune_code: str, text_kh: str) -> Row | None:
    """A clerk's news item that is in the feed but was never posted to the group (no group was bound)."""
    return conn.execute(
        "SELECT * FROM announcements WHERE source = 'admin' AND commune_code = ? AND text_kh = ?"
        " AND group_message_id IS NULL AND is_deleted = 0 ORDER BY id DESC LIMIT 1",
        (commune_code, text_kh),
    ).fetchone()


def cache_announcement_media(
    conn: sqlite3.Connection, announcement_id: int, photo_file_id: str | None, voice_file_id: str | None
) -> None:
    """Remember Telegram's copy of an uploaded file, so later sends reuse it instead of uploading again."""
    conn.execute(
        "UPDATE announcements SET photo_file_id = COALESCE(photo_file_id, ?), voice_file_id = COALESCE(voice_file_id, ?)"
        " WHERE id = ?",
        (photo_file_id, voice_file_id, announcement_id),
    )
    conn.commit()


def hide_seed_duplicates(conn: sqlite3.Connection, commune_code: str, text_kh: str) -> int:
    """Hide seeded copies of a news text once a clerk publishes it for real; returns rows hidden."""
    cursor = conn.execute(
        "UPDATE announcements SET is_deleted = 1 WHERE source = 'seed' AND commune_code = ? AND text_kh = ?",
        (commune_code, text_kh),
    )
    conn.commit()
    return cursor.rowcount


def insert_announcement(
    conn: sqlite3.Connection,
    *,
    commune_code: str,
    source: str,
    posted_by: int | None,
    text_kh: str | None,
    photo_file_id: str | None,
    voice_file_id: str | None,
    event_date: str | None,
    expires_at: datetime | None,
    created_at: datetime,
    photo_path: str | None = None,
    voice_path: str | None = None,
    publish_id: str | None = None,
    location_url: str | None = None,
) -> int:
    cursor = conn.execute(
        """INSERT INTO announcements
           (commune_code, source, posted_by, text_kh, photo_file_id, voice_file_id, photo_path, voice_path,
            publish_id, location_url, event_date, expires_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            commune_code,
            source,
            posted_by,
            text_kh,
            photo_file_id,
            voice_file_id,
            photo_path,
            voice_path,
            publish_id,
            location_url,
            event_date,
            utc_iso(expires_at) if expires_at else None,
            utc_iso(created_at),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def set_announcement_messages(
    conn: sqlite3.Connection, ann_id: int, group_message_id: int | None, group_voice_message_id: int | None
) -> None:
    conn.execute(
        "UPDATE announcements SET group_message_id = ?, group_voice_message_id = ? WHERE id = ?",
        (group_message_id, group_voice_message_id, ann_id),
    )
    conn.commit()


def latest_announcements(conn: sqlite3.Connection, commune_code: str, now: datetime, limit: int = 3) -> list[Row]:
    """The newest `limit` live announcements, returned oldest first (newest ends up above the keyboard)."""
    rows = conn.execute(
        """SELECT * FROM announcements
           WHERE commune_code = ? AND is_deleted = 0 AND (expires_at IS NULL OR expires_at > ?)
           ORDER BY created_at DESC, id DESC
           LIMIT ?""",
        (commune_code, utc_iso(now), limit),
    ).fetchall()
    return list(reversed(rows))


def last_admin_announcement(conn: sqlite3.Connection, commune_code: str, posted_by: int) -> Row | None:
    return conn.execute(
        """SELECT * FROM announcements
           WHERE commune_code = ? AND posted_by = ? AND source = 'admin' AND is_deleted = 0
           ORDER BY created_at DESC, id DESC LIMIT 1""",
        (commune_code, posted_by),
    ).fetchone()


def last_admin_publish(conn: sqlite3.Connection, posted_by: int) -> list[Row]:
    """Every live copy of this clerk's latest post (one row per sangkat it was published for)."""
    latest = conn.execute(
        """SELECT * FROM announcements WHERE posted_by = ? AND source = 'admin' AND is_deleted = 0
           ORDER BY created_at DESC, id DESC LIMIT 1""",
        (posted_by,),
    ).fetchone()
    if latest is None:
        return []
    if latest["publish_id"] is None:
        return [latest]
    return conn.execute(
        "SELECT * FROM announcements WHERE publish_id = ? AND is_deleted = 0 ORDER BY id", (latest["publish_id"],)
    ).fetchall()


def clerk_for_user(conn: sqlite3.Connection, user_id: int) -> Row | None:
    return conn.execute("SELECT * FROM clerks WHERE telegram_user_id = ?", (user_id,)).fetchone()


def link_clerk(conn: sqlite3.Connection, user_id: int, username: str) -> Row | None:
    """First contact: tie a waiting @username row to this account. Returns the row if newly linked.

    An account that is already linked just has its stored username refreshed (they may have renamed).
    """
    linked = clerk_for_user(conn, user_id)
    if linked is not None:
        if linked["username"] != username and conn.execute(
            "SELECT 1 FROM clerks WHERE username = ?", (username,)
        ).fetchone() is None:
            conn.execute("UPDATE clerks SET username = ? WHERE id = ?", (username, linked["id"]))
            conn.commit()
        return None
    cursor = conn.execute(
        "UPDATE clerks SET telegram_user_id = ? WHERE username = ? AND telegram_user_id IS NULL", (user_id, username)
    )
    conn.commit()
    return clerk_for_user(conn, user_id) if cursor.rowcount else None


def upsert_clerk(conn: sqlite3.Connection, username: str, commune_code: str, added_by: int) -> None:
    """Add a clerk, or move an existing clerk to another sangkat (super rows are left alone)."""
    conn.execute(
        """INSERT INTO clerks (username, role, commune_code, added_by, added_at) VALUES (?, 'clerk', ?, ?, ?)
           ON CONFLICT (username) DO UPDATE SET commune_code = excluded.commune_code WHERE role = 'clerk'""",
        (username, commune_code, added_by, utc_iso(datetime.now(UTC))),
    )
    conn.commit()


def get_clerk(conn: sqlite3.Connection, username: str) -> Row | None:
    return conn.execute("SELECT * FROM clerks WHERE username = ?", (username,)).fetchone()


def delete_clerk(conn: sqlite3.Connection, username: str) -> None:
    conn.execute("DELETE FROM clerks WHERE username = ? AND role = 'clerk'", (username,))
    conn.commit()


def list_clerks(conn: sqlite3.Connection) -> list[Row]:
    return conn.execute("SELECT * FROM clerks ORDER BY role DESC, commune_code, username").fetchall()


def sync_super_usernames(conn: sqlite3.Connection, usernames: Sequence[str]) -> None:
    """Make the 'super' rows match ADMIN_USERNAMES in .env (a clerk listed there is promoted)."""
    wanted = set(usernames)
    for row in conn.execute("SELECT username FROM clerks WHERE role = 'super'").fetchall():
        if row["username"] not in wanted:
            conn.execute("DELETE FROM clerks WHERE username = ?", (row["username"],))
    for username in wanted:
        conn.execute(
            """INSERT INTO clerks (username, role, commune_code, added_at) VALUES (?, 'super', NULL, ?)
               ON CONFLICT (username) DO UPDATE SET role = 'super', commune_code = NULL""",
            (username, utc_iso(datetime.now(UTC))),
        )
    conn.commit()


def mark_deleted(conn: sqlite3.Connection, ann_id: int) -> None:
    conn.execute("UPDATE announcements SET is_deleted = 1 WHERE id = ?", (ann_id,))
    conn.commit()


def audit(
    conn: sqlite3.Connection,
    actor_user_id: int,
    commune_code: str | None,
    action: str,
    target_id: str | None,
    metadata: dict,
) -> None:
    conn.execute(
        """INSERT INTO audit_logs (actor_user_id, commune_code, action, target_id, metadata_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (actor_user_id, commune_code, action, target_id, json.dumps(metadata, ensure_ascii=False), utc_iso(datetime.now(UTC))),
    )
    conn.commit()
