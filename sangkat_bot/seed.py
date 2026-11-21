"""Rebuild reference data from DataEF + data/seed. Run: python -m sangkat_bot.seed"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime
from pathlib import Path

from sangkat_bot.db import connect, insert_announcement

_BOOL = {"true": 1, "false": 0}


def _rows(path: Path) -> list[dict[str, str | None]]:
    """Read a CSV (BOM-safe); empty cells become None, true/false stay as text for _flag()."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        return [{key: (value if value != "" else None) for key, value in row.items()} for row in csv.DictReader(file)]


def _flag(value: str | None) -> int:
    return _BOOL.get((value or "false").strip().lower(), 0)


def _num(value: str | None) -> float | None:
    return float(value) if value else None


def _moment(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _load_hierarchy(conn: sqlite3.Connection, dataef_dir: Path) -> None:
    conn.executemany(
        "INSERT INTO provinces VALUES (:province_code, :province_kh, :province_en)",
        _rows(dataef_dir / "provinces_2025.csv"),
    )
    conn.executemany(
        "INSERT INTO districts VALUES (:district_code, :province_code, :district_kh, :district_en)",
        _rows(dataef_dir / "districts_2025.csv"),
    )
    communes = _rows(dataef_dir / "communes_2025.csv")
    for row in communes:
        # DataEF has no Khum/Sangkat column; all of Phnom Penh is Sangkat. Elsewhere unknown (NULL → "ឃុំ").
        row["commune_type"] = "sangkat" if row["province_code"] == "12" else None
    conn.executemany(
        """INSERT INTO communes VALUES
           (:commune_code, :district_code, :province_code, :commune_kh, :commune_en, :commune_type)""",
        communes,
    )


def _load_configs(conn: sqlite3.Connection, seed_dir: Path) -> None:
    for row in _rows(seed_dir / "commune_configs.csv"):
        conn.execute(
            """INSERT INTO commune_configs
               (commune_code, chat_type, hall_name_kh, hall_phone, office_days_kh, office_hours_kh, address_kh,
                lat, lon, google_maps_url, is_active, verification_status, source, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (commune_code) DO UPDATE SET
                 chat_type = excluded.chat_type, hall_name_kh = excluded.hall_name_kh,
                 hall_phone = excluded.hall_phone, office_days_kh = excluded.office_days_kh,
                 office_hours_kh = excluded.office_hours_kh, address_kh = excluded.address_kh,
                 lat = excluded.lat, lon = excluded.lon, google_maps_url = excluded.google_maps_url,
                 is_active = excluded.is_active, verification_status = excluded.verification_status,
                 source = excluded.source, notes = excluded.notes""",
            (
                row["commune_code"], row["chat_type"] or "group", row["hall_name_kh"], row["hall_phone"],
                row["office_days_kh"], row["office_hours_kh"], row["address_kh"], _num(row["lat"]),
                _num(row["lon"]), row["google_maps_url"], _flag(row["is_active"]),
                row["verification_status"], row["source"], row["notes"],
            ),
        )
        # A seeded group id only fills an empty slot; one set by /bind always wins.
        if row["telegram_group_id"]:
            conn.execute(
                "UPDATE commune_configs SET telegram_group_id = ? WHERE commune_code = ? AND telegram_group_id IS NULL",
                (int(row["telegram_group_id"]), row["commune_code"]),
            )


def _load_directories(conn: sqlite3.Connection, seed_dir: Path) -> None:
    conn.executemany(
        "INSERT INTO villages VALUES (:village_code, :commune_code, :village_kh, :village_en)",
        _rows(seed_dir / "demo_villages.csv"),
    )
    for row in _rows(seed_dir / "national_emergency_numbers.csv"):
        conn.execute(
            "INSERT INTO emergency_numbers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["number"], row["category"], row["name_kh"], row["name_en"], row["scope"],
                _flag(row["is_active"]), int(row["sort_order"]), row["verification_status"],
                row["source"], row["notes"],
            ),
        )
    for row in _rows(seed_dir / "local_contacts.csv"):
        conn.execute(
            """INSERT INTO local_contacts
               (commune_code, category, name_kh, name_en, phone_numbers, operating_hours_kh, is_24h, lat, lon,
                google_maps_url, distance_km, sort_order, is_active, verification_status, source, source_ref, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["commune_code"], row["category"], row["name_kh"], row["name_en"], row["phone_numbers"],
                row["operating_hours_kh"], _flag(row["is_24h"]), _num(row["lat"]), _num(row["lon"]),
                row["google_maps_url"], _num(row["distance_km"]), int(row["sort_order"] or 10),
                _flag(row["is_active"]), row["verification_status"], row["source"], row["source_ref"], row["notes"],
            ),
        )
    for row in _rows(seed_dir / "public_services.csv"):
        conn.execute(
            """INSERT INTO public_services
               (commune_code, service_key, title_kh, required_docs_kh, fee_khr, fee_conditions_kh,
                processing_time_kh, office_level, where_kh, who_must_come_kh, sort_order, is_active,
                verification_status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["commune_code"], row["service_key"], row["title_kh"], row["required_docs_kh"], row["fee_khr"],
                row["fee_conditions_kh"], row["processing_time_kh"], row["office_level"], row["where_kh"],
                row["who_must_come_kh"], int(row["sort_order"] or 10), _flag(row["is_active"]),
                row["verification_status"], row["notes"],
            ),
        )


def run_seed(conn: sqlite3.Connection, dataef_dir: Path, seed_dir: Path) -> dict[str, int]:
    """Reload reference tables; keep users, audit logs, bound group ids and admin-published news."""
    with conn:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in ("villages", "local_contacts", "public_services", "emergency_numbers", "districts", "provinces"):
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM communes")
        conn.execute("DELETE FROM announcements WHERE source = 'seed'")
        _load_hierarchy(conn, dataef_dir)
        _load_configs(conn, seed_dir)
        _load_directories(conn, seed_dir)
    conn.execute("PRAGMA foreign_keys = ON")
    for row in _rows(seed_dir / "demo_announcements.csv"):
        insert_announcement(
            conn, commune_code=row["commune_code"], source="seed", posted_by=None, text_kh=row["text_kh"],
            photo_file_id=None, voice_file_id=None, photo_path=row["photo_path"] or None,
            voice_path=row["voice_path"] or None, event_date=row["event_date"],
            expires_at=_moment(row["expires_at"]), created_at=_moment(row["created_at"]),
        )
    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("provinces", "districts", "communes", "villages", "emergency_numbers", "local_contacts",
                      "public_services", "commune_configs", "users")
    }
    counts["seed_announcements"] = conn.execute(
        "SELECT COUNT(*) FROM announcements WHERE source = 'seed'"
    ).fetchone()[0]
    return counts


def main() -> None:
    from sangkat_bot.config import load_settings

    settings = load_settings()
    conn = connect(settings.db_path)
    for table, count in run_seed(conn, settings.dataef_dir, settings.seed_dir).items():
        print(f"{table:20} {count}")
    conn.close()


if __name__ == "__main__":
    main()
