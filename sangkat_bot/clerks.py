"""Who may post: super-admins (from .env) and clerks (added by @username, one sangkat each).

A clerk is added by username, but the role is tied to their Telegram account the first time that
username writes to the bot (the outer middleware below). After that a renamed or recycled
username can neither lose nor steal the role.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, BotCommandScopeChat

from sangkat_bot.config import Settings
from sangkat_bot.copy import commune_type_kh
from sangkat_bot.db import Row, clerk_for_user, get_commune, link_clerk
from sangkat_bot.handlers.common import copy_for

log = logging.getLogger(__name__)

RESIDENT_COMMANDS = ("start", "help")
CLERK_COMMANDS = RESIDENT_COMMANDS + ("announce", "delete_last", "cancel")
SUPER_COMMANDS = CLERK_COMMANDS + ("clerks", "addclerk", "removeclerk")

_USERNAME = re.compile(r"[a-z][a-z0-9_]{4,31}")


@dataclass(frozen=True)
class Role:
    is_super: bool
    commune_code: str | None  # the clerk's sangkat; None for super-admins (every sangkat)


def normalize_username(raw: str | None) -> str | None:
    """'@Sok_Dara', 'sok_dara' or 't.me/sok_dara' → 'sok_dara'; None if it can't be a Telegram username."""
    if not raw:
        return None
    name = raw.strip()
    name = re.sub(r"^(https?://)?(www\.)?(t|telegram)\.me/", "", name, flags=re.IGNORECASE)
    name = name.removeprefix("@").lower()
    return name if _USERNAME.fullmatch(name) else None


def role_of(conn: sqlite3.Connection, settings: Settings, user_id: int) -> Role | None:
    if user_id in settings.admin_user_ids:
        return Role(is_super=True, commune_code=None)
    row = clerk_for_user(conn, user_id)
    if row is None:
        return None
    return Role(is_super=row["role"] == "super", commune_code=row["commune_code"])


def postable_communes(role: Role | None, active: list[Row]) -> list[Row]:
    """The sangkats this person may publish for."""
    if role is None:
        return []
    return active if role.is_super else [c for c in active if c["commune_code"] == role.commune_code]


def commune_name(commune: Row) -> str:
    return f"{commune_type_kh(commune['commune_type'])}{commune['commune_kh']}"


def menu(copy_data: dict, names: tuple[str, ...]) -> list[BotCommand]:
    labels = copy_data["commands"]
    return [BotCommand(command=name, description=labels[name]) for name in names]


async def set_poster_menu(bot: Bot, copy_data: dict, user_id: int, is_super: bool) -> None:
    try:
        commands = menu(copy_data, SUPER_COMMANDS if is_super else CLERK_COMMANDS)
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
    except TelegramAPIError:  # they haven't pressed Start yet
        log.warning("event=commands_skipped user=%s", user_id)


async def clear_poster_menu(bot: Bot, user_id: int) -> None:
    try:
        await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=user_id))
    except TelegramAPIError:
        pass


async def link_on_first_contact(handler, event, data):
    """Outer middleware: the first update from an added @username ties the role to that account."""
    user = data.get("event_from_user")
    if user is not None and user.username:
        conn: sqlite3.Connection = data["conn"]
        row = link_clerk(conn, user.id, user.username.lower())
        if row is not None:
            log.info("event=clerk_linked role=%s commune=%s", row["role"], row["commune_code"])
            chat = data.get("event_chat")
            if chat is not None and chat.type == "private":
                await _greet(data["bot"], data["copy_data"], conn, data["settings"], user.id, row)
    return await handler(event, data)


async def _greet(bot: Bot, copy_data: dict, conn: sqlite3.Connection, settings: Settings, user_id: int, row: Row) -> None:
    is_super = row["role"] == "super"
    commune = get_commune(conn, row["commune_code"] or settings.demo_commune_code)
    copy = copy_for(copy_data, commune)
    if is_super:
        text = copy.t("admin.super_welcome")
    else:
        text = copy.t("admin.clerk_welcome").replace("{commune}", commune_name(commune) if commune else "")
    try:
        await bot.send_message(user_id, text)
    except TelegramAPIError:
        log.warning("event=clerk_greet_failed")
    await set_poster_menu(bot, copy_data, user_id, is_super)
