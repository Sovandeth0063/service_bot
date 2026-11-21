"""Helpers shared by the handler modules."""

from __future__ import annotations

import sqlite3

from sangkat_bot.copy import Copy
from sangkat_bot.db import Row, get_commune, list_active_communes


def copy_for(copy_data: dict, commune: Row | None) -> Copy:
    """Copy filled for a commune; before a commune is known, use the first active one's type."""
    if commune is None:
        return Copy(copy_data, None, "")
    return Copy(copy_data, commune["commune_type"], commune["commune_kh"])


def active_codes(conn: sqlite3.Connection) -> set[str]:
    return {row["commune_code"] for row in list_active_communes(conn)}


def commune_or_none(conn: sqlite3.Connection, code: str | None) -> Row | None:
    return get_commune(conn, code) if code else None
