"""Send test phone-number formats to every admin to see which become tap-to-call links.

Usage: .venv\\Scripts\\python scripts/phone_check.py
Each admin must have pressed Start on the bot first.
"""

import asyncio

from aiogram import Bot

from sangkat_bot.config import load_settings

FORMATS = ["117", "023 426 948", "023426948", "+855 23 426 948", "012 786 693"]


async def main() -> None:
    settings = load_settings()
    bot = Bot(settings.bot_token)
    text = "Phone link check — which lines can you tap?\n\n" + "\n".join(FORMATS)
    try:
        for user_id in settings.admin_user_ids:
            await bot.send_message(user_id, text)
            print(f"sent to {user_id}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
