"""Every demo news item reaches residents as text + picture + voice, on any machine."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from aiogram.methods import SendPhoto, SendVoice
from aiogram.types import FSInputFile

from sangkat_bot.db import connect, latest_announcements

from .test_handlers_admin import RESIDENT, app, feed  # noqa: F401  (fixture reuse)
from .tg import message_update


def test_every_live_seed_news_has_picture_and_voice_files(conn):
    rows = latest_announcements(conn, "120101", datetime.now(UTC))
    assert len(rows) == 3
    for row in rows:
        assert row["photo_path"] and Path(row["photo_path"]).is_file(), row["text_kh"]
        assert row["voice_path"] and Path(row["voice_path"]).is_file(), row["text_kh"]


async def test_feed_uploads_files_once_then_reuses_telegram_copy(app, copy_tb):
    dp, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text=copy_tb.button("announcements")))
    photos, voices = session.sent(SendPhoto), session.sent(SendVoice)
    assert len(photos) == 3 and len(voices) == 3
    assert all(isinstance(p.photo, FSInputFile) for p in photos)
    assert all(isinstance(v.voice, FSInputFile) for v in voices)
    assert all(row["photo_file_id"] and row["voice_file_id"] for row in latest_announcements(dp["conn"], "120101", datetime.now(UTC)))

    await feed(app, message_update(RESIDENT, text=copy_tb.button("announcements")))
    again_photos, again_voices = session.sent(SendPhoto)[3:], session.sent(SendVoice)[3:]
    assert len(again_photos) == 3 and all(isinstance(p.photo, str) for p in again_photos)
    assert len(again_voices) == 3 and all(isinstance(v.voice, str) for v in again_voices)


def test_connect_adds_media_columns_to_an_older_database(tmp_path):
    old = tmp_path / "old.db"
    raw = sqlite3.connect(old)
    raw.execute("CREATE TABLE announcements (id INTEGER PRIMARY KEY, commune_code TEXT NOT NULL, source TEXT NOT NULL,"
                " posted_by INTEGER, text_kh TEXT, photo_file_id TEXT, voice_file_id TEXT, group_message_id INTEGER,"
                " group_voice_message_id INTEGER, event_date TEXT, expires_at TEXT,"
                " is_deleted INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)")
    raw.commit()
    raw.close()
    conn = connect(old)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(announcements)")}
    assert {"photo_path", "voice_path"} <= columns
