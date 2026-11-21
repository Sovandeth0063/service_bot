"""Wire settings, database, copy and routers into an aiogram dispatcher."""

from __future__ import annotations

import logging
import sqlite3

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    CallbackQuery,
    ErrorEvent,
)

from sangkat_bot.config import Settings, load_settings
from sangkat_bot.copy import Copy, load_copy
from sangkat_bot.clerks import RESIDENT_COMMANDS, link_on_first_contact, menu, set_poster_menu
from sangkat_bot.db import connect, list_clerks, sync_super_usernames
from sangkat_bot.handlers import admin, group, manage, resident
from sangkat_bot.keywords import load_keywords
from sangkat_bot.news_ai import make_news_maker

log = logging.getLogger(__name__)


async def on_error(event: ErrorEvent, copy_data: dict, bot: Bot) -> bool:
    """Never let one bad update stop the bot: log it (no message text) and reply politely."""
    update = event.update
    log.error(
        "event=error update=%s error=%s",
        update.update_id, type(event.exception).__name__, exc_info=event.exception,
    )
    message = update.message or (update.callback_query.message if update.callback_query else None)
    if message is not None and message.chat.type == "private":
        try:
            await bot.send_message(message.chat.id, Copy(copy_data, None, "").t("fallback"))
        except Exception:  # the reply itself failed (e.g. network); nothing more to do
            log.exception("event=error_reply_failed update=%s", update.update_id)
    return True


GROUP_COMMANDS = ("help",)  # any member: shows the open-bot button
GROUP_ADMIN_COMMANDS = GROUP_COMMANDS + ("bind", "guide")


async def setup_commands(bot: Bot, copy_data: dict, settings: Settings, conn: sqlite3.Connection | None = None) -> None:
    """Fill Telegram's Menu button, so nobody has to remember or type a command."""
    await bot.set_my_commands(menu(copy_data, RESIDENT_COMMANDS), scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(menu(copy_data, GROUP_COMMANDS), scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(menu(copy_data, GROUP_ADMIN_COMMANDS), scope=BotCommandScopeAllChatAdministrators())
    for user_id in settings.admin_user_ids:
        await set_poster_menu(bot, copy_data, user_id, is_super=True)
    for row in list_clerks(conn) if conn is not None else []:
        if row["telegram_user_id"] is not None and row["telegram_user_id"] not in settings.admin_user_ids:
            await set_poster_menu(bot, copy_data, row["telegram_user_id"], is_super=row["role"] == "super")


async def answer_leftover_tap(callback: CallbackQuery) -> None:
    """An old or double-tapped inline button: stop its loading spinner and do nothing."""
    await callback.answer()


def build_dispatcher(settings: Settings) -> tuple[Bot, Dispatcher]:
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    # One update at a time per chat+user, so a double tap can't run a step twice.
    dp = Dispatcher(events_isolation=SimpleEventIsolation())
    dp["settings"] = settings
    dp["conn"] = connect(settings.db_path)
    dp["copy_data"] = load_copy(settings.seed_dir / "bot_copy_kh.json")
    dp["keywords"] = load_keywords(settings.seed_dir / "keywords_kh.csv")
    dp["news_maker"] = make_news_maker(settings)  # None: clerks post text/photo/voice by hand
    sync_super_usernames(dp["conn"], sorted(settings.admin_usernames))
    dp.update.outer_middleware(link_on_first_contact)  # ties an added @username to its account
    dp.errors.register(on_error)
    dp.include_router(group.make_router())
    dp.include_router(manage.make_router())  # super-admins: /addclerk /removeclerk /clerks
    dp.include_router(admin.make_router())
    dp.include_router(resident.make_router())  # resident last: it catches every remaining private message
    leftovers = Router(name="leftovers")
    leftovers.callback_query.register(answer_leftover_tap)
    dp.include_router(leftovers)
    return bot, dp


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = load_settings()
    bot, dp = build_dispatcher(settings)
    me = await bot.get_me()
    dp["bot_username"] = me.username
    log.info("event=start bot=@%s commune=%s demo_mode=%s", me.username, settings.demo_commune_code, settings.demo_mode)
    try:
        await setup_commands(bot, dp["copy_data"], settings, dp["conn"])
    except TelegramAPIError as error:  # a missing menu must never stop the bot
        log.warning("event=commands_failed error=%s", type(error).__name__)
    try:
        await dp.start_polling(bot)
    finally:
        dp["conn"].close()
