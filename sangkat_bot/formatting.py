"""Build the HTML text of every resident card. Pure functions: rows in, strings out."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from typing import Any

from sangkat_bot.copy import Copy

Record = Mapping[str, Any]


def format_phone(raw: str | None) -> list[str]:
    """Split a ' | '-separated phone field into display numbers.

    Numbers stay exactly as written in the seed data. If the phone check (Task 1) shows a
    format is not tappable on real phones, convert it here and nowhere else.
    """
    if not raw:
        return []
    return [part.strip() for part in raw.split("|") if part.strip()]


def _map_link(url: str | None, copy: Copy) -> str | None:
    return f'<a href="{escape(url, quote=True)}">{escape(copy.t("map_link"))}</a>' if url else None


def _demo(text: str, copy: Copy, demo_mode: bool) -> str:
    return f"{text}\n\n<i>{escape(copy.t('demo_footer'))}</i>" if demo_mode else text


def contact_block(row: Record, copy: Copy) -> str:
    """Name, hours, one phone per line (or "being verified"), and a map link."""
    lines = [f"<b>{escape(row['name_kh'])}</b>"]
    if row["is_24h"]:
        lines.append(f"🕒 {escape(copy.t('hours_24h'))}")
    elif row["operating_hours_kh"]:
        lines.append(f"🕒 {escape(row['operating_hours_kh'])}")
    phones = format_phone(row["phone_numbers"])
    lines += [f"📞 {escape(phone)}" for phone in phones] or [f"📞 {escape(copy.t('phone_missing'))}"]
    link = _map_link(row["google_maps_url"], copy)
    if link:
        lines.append(link)
    return "\n".join(lines)


def emergency_card(national: list[Record], local: list[Record], copy: Copy, demo_mode: bool) -> str:
    parts = [f"<b>{escape(copy.t('emergency_header_national'))}</b>"]
    parts.append("\n".join(
        f"<b>{escape(row['name_kh'])}</b>  {escape(' / '.join(format_phone(row['number'])))}" for row in national
    ))
    if local:
        parts.append(f"<b>{escape(copy.t('emergency_header_local'))}</b>")
        parts += [contact_block(row, copy) for row in local]
    return _demo("\n\n".join(parts), copy, demo_mode)


def health_card(contacts: list[Record], copy: Copy, demo_mode: bool) -> str:
    parts = [f"<b>{escape(copy.t('health_header'))}</b>"] + [contact_block(row, copy) for row in contacts]
    return _demo("\n\n".join(parts), copy, demo_mode)


def hall_card(commune: Record, copy: Copy, demo_mode: bool) -> str:
    lines = [f"<b>{escape(copy.t('hall_header'))}</b>"]
    hours = " ".join(part for part in (commune["office_days_kh"], commune["office_hours_kh"]) if part)
    if hours:
        lines.append(f"🕒 {escape(copy.t('hall_hours'))} {escape(hours)}")
    phones = format_phone(commune["hall_phone"])
    lines += [f"📞 {escape(phone)}" for phone in phones] or [f"📞 {escape(copy.t('phone_missing'))}"]
    if commune["address_kh"]:
        lines.append(f"🏠 {escape(commune['address_kh'])}")
    link = _map_link(commune["google_maps_url"], copy)
    if link:
        lines.append(link)
    return _demo("\n".join(lines), copy, demo_mode)


def service_card(service: Record, copy: Copy) -> str:
    lines = [f"<b>📄 {escape(service['title_kh'])}</b>", "", f"<b>{escape(copy.t('docs_needed'))}</b>"]
    lines += [f"☐ {escape(doc.strip())}" for doc in service["required_docs_kh"].split("|") if doc.strip()]
    lines.append("")
    fee = service["fee_khr"] or service["fee_conditions_kh"]
    if fee:
        lines.append(f"💵 {escape(copy.t('fee'))} {escape(fee)}")
    if service["processing_time_kh"]:
        lines.append(f"⏱️ {escape(copy.t('processing_time'))} {escape(service['processing_time_kh'])}")
    if service["where_kh"]:
        lines.append(f"🏛️ {escape(copy.t('where'))} {escape(service['where_kh'])}")
    if service["who_must_come_kh"]:
        lines.append(f"👤 {escape(copy.t('who'))} {escape(service['who_must_come_kh'])}")
    return "\n".join(lines).rstrip()
