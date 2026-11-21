"""Commune group side: /bind links the group to a commune and pins the onboarding link."""

from __future__ import annotations

import logging
import sqlite3

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from sangkat_bot.config import Settings
from sangkat_bot.db import audit, commune_for_group, get_commune, set_group
from sangkat_bot.guide import group_guide
from sangkat_bot.handlers.admin import is_admin
from sangkat_bot.handlers.common import active_codes, copy_for
from sangkat_bot.keyboards import open_bot_button

log = logging.getLogger(__name__)


def parse_bind_args(args: str | None, active: set[str]) -> str | None:
    code = (args or "").strip()
    return code if code in active else None


async def bind(
    message: Message,
    command: CommandObject,
    conn: sqlite3.Connection,
    settings: Settings,
    copy_data: dict,
    bot: Bot,
    bot_username: str,
) -> None:
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        return  # only clerks may bind; stay silent for everyone else
    code = parse_bind_args(command.args, active_codes(conn))
    if code is None:
        return
    set_group(conn, code, message.chat.id)
    audit(conn, message.from_user.id, code, "bind", str(message.chat.id), {})
    log.info("event=bind commune=%s", code)
    copy = copy_for(copy_data, get_commune(conn, code))
    await message.answer(copy.t("admin.bound"))
    await _post_and_pin(message, copy.t("welcome"), copy, code, bot, bot_username)


async def post_guide(
    message: Message, conn: sqlite3.Connection, settings: Settings, copy_data: dict, bot: Bot, bot_username: str
) -> None:
    """/guide: post the "how to use" steps with the open-bot button, and pin them."""
    if message.from_user is None or not is_admin(message.from_user.id, settings):
        return
    code = commune_for_group(conn, message.chat.id)
    if code is None:
        copy = copy_for(copy_data, None)
        await message.answer(copy.t("admin.no_group").replace("{commune_code}", settings.demo_commune_code))
        return
    copy = copy_for(copy_data, get_commune(conn, code))
    await _post_and_pin(message, group_guide(copy), copy, code, bot, bot_username)


async def _post_and_pin(message: Message, text: str, copy, code: str, bot: Bot, bot_username: str) -> None:
    posted = await message.answer(text, reply_markup=open_bot_button(copy, bot_username, code))
    try:
        await bot.pin_chat_message(message.chat.id, posted.message_id, disable_notification=True)
    except (TelegramBadRequest, TelegramForbiddenError):
        await message.answer(copy.t("admin.pin_failed"))


def make_router() -> Router:
    router = Router(name="group")
    router.message.filter(F.chat.type.in_({"group", "supergroup"}))
    router.message.register(bind, Command("bind"))
    router.message.register(post_guide, Command("guide"))
    return router  # every other group message is ignored on purpose
