r"""Publish one news item as text + picture + voice, from files on this laptop.

Usage:
  .venv\Scripts\python scripts/publish_news.py --text-file news.txt --photo flyer.png --voice voice.ogg

What it does, as the first clerk in ADMIN_USER_IDS:
  1. sends the clerk a preview (picture + caption + 📱 button, voice note as a reply),
  2. posts it to the commune group too, if the group is bound (/bind),
  3. saves it so it appears under 📢 in the bot, and /delete_last can remove it.
Run it again after /bind and the same item is posted to the group (no duplicate in 📢).
Safe to run while the bot is running.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile

from sangkat_bot.config import load_settings
from sangkat_bot.copy import load_copy
from sangkat_bot.db import (
    audit,
    connect,
    get_commune,
    hide_seed_duplicates,
    insert_announcement,
    set_announcement_messages,
    unposted_admin_announcement,
)
from sangkat_bot.handlers.admin import publish_target
from sangkat_bot.handlers.common import copy_for
from sangkat_bot.keyboards import open_bot_button
from sangkat_bot.posts import CAPTION_LIMIT, announcement_body, build_post, send_post


async def publish(text: str, photo: Path, voice: Path) -> None:
    settings = load_settings()
    if not settings.admin_user_ids:
        raise SystemExit("Set ADMIN_USER_IDS in .env first.")
    clerk = min(settings.admin_user_ids)
    conn = connect(settings.db_path)
    commune = get_commune(conn, settings.demo_commune_code)
    copy = copy_for(load_copy(settings.seed_dir / "bot_copy_kh.json"), commune)
    header = copy.t("announcement_header")
    body = announcement_body(header, text)
    if len(body) > CAPTION_LIMIT:
        raise SystemExit(f"Text is too long for a picture caption ({len(body)} > {CAPTION_LIMIT}); shorten it.")

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        me = await bot.get_me()
        markup = open_bot_button(copy, me.username, commune["commune_code"])
        existing = unposted_admin_announcement(conn, commune["commune_code"], text)
        if existing is not None and publish_target(commune) is not None:
            # Already in 📢 from an earlier run with no group bound: just post it to the group now.
            photo_id, voice_id = existing["photo_file_id"], existing["voice_file_id"]
            group_ids = await send_post(bot, publish_target(commune), build_post(header, text, photo_id, voice_id), markup)
            set_announcement_messages(conn, existing["id"], *group_ids)
            print(f"posted existing announcement {existing['id']} to group {publish_target(commune)}")
            return

        # 1. Preview to the clerk; uploading here gives reusable file_ids for the group and the feed.
        lead = await bot.send_photo(clerk, FSInputFile(photo), caption=body, reply_markup=markup)
        sent_voice = await bot.send_voice(clerk, FSInputFile(voice), reply_to_message_id=lead.message_id)
        photo_id, voice_id = lead.photo[-1].file_id, sent_voice.voice.file_id
        print(f"preview sent to clerk {clerk}")

        # 2. The commune group, when bound.
        group_ids: tuple[int | None, int | None] = (None, None)
        target = publish_target(commune)
        if target is not None:
            group_ids = await send_post(bot, target, build_post(header, text, photo_id, voice_id), markup)
            print(f"posted to group {target}")
        else:
            print(f"no group bound yet: send /bind {commune['commune_code']} in the group, then run this again")

        # 3. The 📢 feed.
        ann_id = insert_announcement(
            conn, commune_code=commune["commune_code"], source="admin", posted_by=clerk, text_kh=text,
            photo_file_id=photo_id, voice_file_id=voice_id, event_date=None, expires_at=None,
            created_at=datetime.now(UTC),
        )
        set_announcement_messages(conn, ann_id, *group_ids)
        audit(conn, clerk, commune["commune_code"], "publish", str(ann_id), {"photo": True, "voice": True, "via": "script"})
        hidden = hide_seed_duplicates(conn, commune["commune_code"], text)
        print(f"saved as announcement {ann_id}; hid {hidden} seeded copy(ies) of the same text")
    finally:
        await bot.session.close()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish text + picture + voice news.")
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--photo", type=Path, required=True)
    parser.add_argument("--voice", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(publish(args.text_file.read_text(encoding="utf-8").strip(), args.photo, args.voice))


if __name__ == "__main__":
    main()
