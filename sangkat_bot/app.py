"""Wire settings, database, copy and routers into an aiogram dispatcher."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import CallbackQuery, ErrorEvent

from sangkat_bot.config import Settings, load_settings
from sangkat_bot.copy import Copy, load_copy
from sangkat_bot.db import connect
from sangkat_bot.handlers import admin, group, resident
from sangkat_bot.keywords import load_keywords

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
    dp.errors.register(on_error)
    dp.include_router(group.make_router())
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
        await dp.start_polling(bot)
    finally:
        dp["conn"].close()
