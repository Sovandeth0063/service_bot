r"""Wipe a private chat with the bot (both sides), e.g. before filming a take.

Usage: .venv\Scripts\python scripts/clear_chat.py [telegram_user_id ...]
With no ids, clears the chat of every admin in ADMIN_USER_IDS.

Telegram lets a bot delete messages in a private chat only when they are under 48 hours old;
older ones stay. Message ids in a private chat count up from 1, so the script finds the
newest id (by sending a short marker) and deletes 1..newest in batches of 100.
"""

from __future__ import annotations

import asyncio
import sys

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from sangkat_bot.config import load_settings

BATCH = 100  # deleteMessages limit


async def clear(bot: Bot, chat_id: int) -> int:
    marker = await bot.send_message(chat_id, "🧹")
    newest = marker.message_id
    for start in range(1, newest + 1, BATCH):
        ids = list(range(start, min(start + BATCH, newest + 1)))
        try:
            await bot.delete_messages(chat_id, ids)  # missing or too-old ids are skipped
        except TelegramAPIError as error:
            print(f"  ids {ids[0]}-{ids[-1]}: {type(error).__name__}")
    return newest


async def main() -> None:
    settings = load_settings()
    chat_ids = [int(arg) for arg in sys.argv[1:]] or sorted(settings.admin_user_ids)
    bot = Bot(settings.bot_token)
    try:
        for chat_id in chat_ids:
            newest = await clear(bot, chat_id)
            print(f"cleared chat {chat_id} (message ids 1-{newest})")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
