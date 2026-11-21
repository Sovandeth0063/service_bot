"""Super-admins manage clerks by @username: /addclerk, /removeclerk, /clerks (private chat only)."""

from __future__ import annotations

import logging
import sqlite3

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from sangkat_bot.clerks import clear_poster_menu, commune_name, normalize_username, role_of, set_poster_menu
from sangkat_bot.config import Settings
from sangkat_bot.copy import Copy
from sangkat_bot.db import audit, delete_clerk, get_clerk, get_commune, list_active_communes, list_clerks, upsert_clerk
from sangkat_bot.handlers.common import copy_for

log = logging.getLogger(__name__)


async def _from_super(message: Message, conn: sqlite3.Connection, settings: Settings) -> bool:
    """Async on purpose: sync filters run in a worker thread, and SQLite stays on its own thread."""
    role = role_of(conn, settings, message.from_user.id) if message.from_user else None
    return role is not None and role.is_super


def _copy(conn: sqlite3.Connection, settings: Settings, copy_data: dict) -> Copy:
    return copy_for(copy_data, get_commune(conn, settings.demo_commune_code))


def _usage(copy: Copy, conn: sqlite3.Connection) -> str:
    codes = "\n".join(f"{c['commune_code']} — {commune_name(c)}" for c in list_active_communes(conn))
    return copy.t("admin.clerk_usage").replace("{codes}", codes)


async def add_clerk(
    message: Message, command: CommandObject, conn: sqlite3.Connection, settings: Settings, copy_data: dict,
    bot: Bot, bot_username: str,
) -> None:
    copy = _copy(conn, settings, copy_data)
    parts = (command.args or "").split()
    username = normalize_username(parts[0]) if len(parts) == 2 else None
    commune = next((c for c in list_active_communes(conn) if len(parts) == 2 and c["commune_code"] == parts[1]), None)
    if username is None or commune is None:
        await message.answer(_usage(copy, conn))
        return
    existing = get_clerk(conn, username)
    if existing is not None and existing["role"] == "super":
        await message.answer(copy.t("admin.clerk_is_super").replace("{username}", username))
        return
    upsert_clerk(conn, username, commune["commune_code"], message.from_user.id)
    audit(conn, message.from_user.id, commune["commune_code"], "add_clerk", username, {})
    log.info("event=add_clerk commune=%s", commune["commune_code"])
    linked = get_clerk(conn, username)["telegram_user_id"]
    if linked is not None:
        await set_poster_menu(bot, copy_data, linked, is_super=False)
    text = copy.t("admin.clerk_added").replace("{username}", username)
    await message.answer(text.replace("{commune}", commune_name(commune)).replace("{bot}", bot_username))


async def remove_clerk(
    message: Message, command: CommandObject, conn: sqlite3.Connection, settings: Settings, copy_data: dict, bot: Bot
) -> None:
    copy = _copy(conn, settings, copy_data)
    username = normalize_username((command.args or "").strip())
    if username is None:
        await message.answer(copy.t("admin.removeclerk_usage"))
        return
    row = get_clerk(conn, username)
    if row is None:
        await message.answer(copy.t("admin.clerk_not_found").replace("{username}", username))
        return
    if row["role"] == "super":
        await message.answer(copy.t("admin.clerk_is_super").replace("{username}", username))
        return
    delete_clerk(conn, username)
    audit(conn, message.from_user.id, row["commune_code"], "remove_clerk", username, {})
    log.info("event=remove_clerk commune=%s", row["commune_code"])
    if row["telegram_user_id"] is not None:
        await clear_poster_menu(bot, row["telegram_user_id"])
    await message.answer(copy.t("admin.clerk_removed").replace("{username}", username))


async def show_clerks(message: Message, conn: sqlite3.Connection, settings: Settings, copy_data: dict) -> None:
    copy = _copy(conn, settings, copy_data)
    lines = [copy.t("admin.clerk_list_header")]
    for row in list_clerks(conn):
        commune = get_commune(conn, row["commune_code"]) if row["commune_code"] else None
        where = commune_name(commune) if commune else copy.t("admin.clerk_all_communes")
        status = copy.t("admin.clerk_linked" if row["telegram_user_id"] is not None else "admin.clerk_pending")
        lines.append(f"• @{row['username']} — {where} — {status}")
    await message.answer("\n".join(lines))


def make_router() -> Router:
    router = Router(name="manage")
    router.message.filter(F.chat.type == "private", _from_super)
    router.message.register(add_clerk, Command("addclerk"))
    router.message.register(remove_clerk, Command("removeclerk"))
    router.message.register(show_clerks, Command("clerks"))
    return router
