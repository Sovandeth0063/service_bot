"""Wire settings, database, copy and routers into an aiogram dispatcher."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from sangkat_bot.config import Settings, load_settings
from sangkat_bot.copy import load_copy
from sangkat_bot.db import connect
from sangkat_bot.handlers import admin, group, resident
from sangkat_bot.keywords import load_keywords

log = logging.getLogger(__name__)


def build_dispatcher(settings: Settings) -> tuple[Bot, Dispatcher]:
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp["settings"] = settings
    dp["conn"] = connect(settings.db_path)
    dp["copy_data"] = load_copy(settings.seed_dir / "bot_copy_kh.json")
    dp["keywords"] = load_keywords(settings.seed_dir / "keywords_kh.csv")
    dp.include_router(group.make_router())
    dp.include_router(admin.make_router())
    dp.include_router(resident.make_router())  # resident last: it catches every remaining private message
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
