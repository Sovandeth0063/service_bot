r"""Send phone-number formats, then the real 🚨 card, to every admin: which lines can you tap?

Usage: .venv\Scripts\python -m sangkat_bot.seed   (once)
       .venv\Scripts\python scripts/phone_check.py
Each admin must have pressed Start on the bot first. If a format is not tappable,
change format_phone() in sangkat_bot/formatting.py; every card uses it.
"""

import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from sangkat_bot.config import load_settings
from sangkat_bot.copy import load_copy
from sangkat_bot.db import connect, emergency_numbers, get_commune, local_contacts
from sangkat_bot.formatting import emergency_card
from sangkat_bot.handlers.common import copy_for

FORMATS = ["117", "023 426 948", "023426948", "+855 23 426 948", "012 786 693"]


async def main() -> None:
    settings = load_settings()
    conn = connect(settings.db_path)
    commune = get_commune(conn, settings.demo_commune_code)
    copy = copy_for(load_copy(settings.seed_dir / "bot_copy_kh.json"), commune)
    card = emergency_card(
        emergency_numbers(conn, commune["province_code"]),
        local_contacts(conn, commune["commune_code"], ["police", "fire", "ambulance"])
        + local_contacts(conn, commune["commune_code"], ["hospital"], only_24h=True),  # same as the 🚨 button
        copy,
        settings.demo_mode,
    )
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    formats = "Phone link check — which lines can you tap?\n\n" + "\n".join(FORMATS)
    try:
        for user_id in settings.admin_user_ids:
            await bot.send_message(user_id, formats, parse_mode=None)
            await bot.send_message(user_id, "As shipped (the 🚨 card):\n\n" + card)
            print(f"sent to {user_id}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
