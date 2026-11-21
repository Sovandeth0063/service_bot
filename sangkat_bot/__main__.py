"""Run the bot: python -m sangkat_bot"""

import asyncio
import sys

from sangkat_bot.app import run

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except ValueError as error:  # missing settings, e.g. BOT_TOKEN
        sys.exit(f"Setup problem: {error}. Copy .env.example to .env and fill it in.")
    except KeyboardInterrupt:
        pass
