"""Clerk flow with the AI writer on: messy notes in, text + flyer + voice preview out, ✏️ fix loop."""

import pytest
from aiogram.methods import SendMessage, SendPhoto, SendVoice
from aiogram.types import FSInputFile

from sangkat_bot.db import set_group
from sangkat_bot.news_ai import MadeNews, NewsAIError

from .test_handlers_admin import CLERK, GROUP, PHOTOS, admin_rows, app, feed  # noqa: F401
from .tg import callback_update, message_update

NOTES = "garbage truck from dec 1 village 1-8 6pm pls tell ppl"
CLEAN = "📅 ចាប់ពីថ្ងៃទី១ ខែធ្នូ រថយន្តប្រមូលសំរាមមកដល់ ម៉ោង ៦:០០ ល្ងាច។"


class FakeMaker:
    def __init__(self, tmp_path, fail=False):
        self.tmp_path, self.fail, self.calls = tmp_path, fail, []

    async def make(self, notes, corrections, want_flyer):
        self.calls.append((notes, list(corrections), want_flyer))
        if self.fail:
            raise NewsAIError("down")
        folder = self.tmp_path / f"made{len(self.calls)}"
        folder.mkdir()
        (folder / "flyer.png").write_bytes(b"png")
        (folder / "voice.ogg").write_bytes(b"ogg")
        text = CLEAN if not corrections else f"{CLEAN} ({corrections[-1]})"
        return MadeNews(text, folder / "flyer.png" if want_flyer else None, folder / "voice.ogg")


@pytest.fixture
def ai_app(app, tmp_path):
    dp, _, _ = app
    dp["news_maker"] = FakeMaker(tmp_path)
    return app


async def start(app_):
    await feed(app_, message_update(CLERK, text="/start 120101"))
    await feed(app_, message_update(CLERK, text="/announce"))


def prompt_buttons(session):
    return [b.callback_data for row in session.sent(SendMessage)[-1].reply_markup.inline_keyboard for b in row]


async def test_messy_notes_become_a_three_part_preview_then_publish_reuses_uploads(ai_app, copy_tb):
    dp, _, session = ai_app
    set_group(dp["conn"], "120101", GROUP)
    await start(ai_app)
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_content_ai")
    await feed(ai_app, message_update(CLERK, text=NOTES))

    assert dp["news_maker"].calls == [(NOTES, [], True)]
    assert copy_tb.t("admin.making") in session.texts()
    preview_photo, preview_voice = session.sent(SendPhoto)[-1], session.sent(SendVoice)[-1]
    assert isinstance(preview_photo.photo, FSInputFile) and isinstance(preview_voice.voice, FSInputFile)
    assert CLEAN in preview_photo.caption
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.preview_ai")
    buttons = prompt_buttons(session)
    assert "ann:fix" in buttons and "ann:publish:120101" in buttons and buttons[-1] == "ann:cancel"

    await feed(ai_app, callback_update(CLERK, "ann:publish:120101"))
    group_photo = [m for m in session.sent(SendPhoto) if m.chat_id == GROUP][-1]
    group_voice = [m for m in session.sent(SendVoice) if m.chat_id == GROUP][-1]
    assert isinstance(group_photo.photo, str) and group_photo.photo.startswith("photo-")
    assert isinstance(group_voice.voice, str) and group_voice.voice.startswith("voice-")
    (row,) = admin_rows(dp)
    assert row["text_kh"] == CLEAN and row["photo_file_id"].startswith("photo-") and row["voice_file_id"].startswith("voice-")


async def test_fix_sends_every_correction_and_shows_a_new_preview(ai_app, copy_tb):
    dp, _, session = ai_app
    await start(ai_app)
    await feed(ai_app, message_update(CLERK, text=NOTES))
    await feed(ai_app, callback_update(CLERK, "ann:fix"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_fix")
    await feed(ai_app, message_update(CLERK, text="the time is 7 PM"))
    await feed(ai_app, callback_update(CLERK, "ann:fix"))
    await feed(ai_app, message_update(CLERK, text="add: bring rubbish in bags"))

    assert [c[1] for c in dp["news_maker"].calls] == [[], ["the time is 7 PM"], ["the time is 7 PM", "add: bring rubbish in bags"]]
    assert all(c[0] == NOTES for c in dp["news_maker"].calls)
    assert "bring rubbish in bags" in session.sent(SendPhoto)[-1].caption
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.preview_ai")

    await feed(ai_app, callback_update(CLERK, "ann:publish:120101"))
    (row,) = admin_rows(dp)
    assert "bring rubbish in bags" in row["text_kh"]


async def test_own_photo_with_caption_is_kept_and_ai_writes_text_and_voice(ai_app):
    dp, _, session = ai_app
    await start(ai_app)
    await feed(ai_app, message_update(CLERK, photo=PHOTOS, caption=NOTES))
    assert dp["news_maker"].calls == [(NOTES, [], False)]
    assert session.sent(SendPhoto)[-1].photo == "big"
    assert isinstance(session.sent(SendVoice)[-1].voice, FSInputFile)


async def test_photo_without_caption_keeps_the_manual_flow(ai_app, copy_tb):
    dp, _, session = ai_app
    await start(ai_app)
    await feed(ai_app, message_update(CLERK, photo=PHOTOS))
    assert dp["news_maker"].calls == []
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_voice")


async def test_ai_failure_falls_back_to_manual_steps_keeping_the_notes(ai_app, copy_tb, tmp_path):
    dp, _, session = ai_app
    dp["news_maker"] = FakeMaker(tmp_path, fail=True)
    await start(ai_app)
    await feed(ai_app, message_update(CLERK, text=NOTES))
    texts = session.texts()
    assert copy_tb.t("admin.ai_failed") in texts
    assert texts[-1] == copy_tb.t("admin.ask_photo")
    await feed(ai_app, callback_update(CLERK, "ann:skip:photo"))
    await feed(ai_app, callback_update(CLERK, "ann:skip:voice"))
    await feed(ai_app, callback_update(CLERK, "ann:publish:120101"))
    (row,) = admin_rows(dp)
    assert row["text_kh"] == NOTES


async def test_menu_button_while_fixing_leaves_the_flow(ai_app, copy_tb):
    dp, _, session = ai_app
    await start(ai_app)
    await feed(ai_app, message_update(CLERK, text=NOTES))
    await feed(ai_app, callback_update(CLERK, "ann:fix"))
    await feed(ai_app, message_update(CLERK, text=copy_tb.button("emergency")))
    assert len(dp["news_maker"].calls) == 1
    assert "117" in session.texts()[-1] or "117" in "".join(session.texts()[-3:])


async def test_without_a_key_the_manual_flow_is_unchanged(app, copy_tb):
    dp, _, session = app
    assert dp["news_maker"] is None
    await start(app)
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_content")
    await feed(app, message_update(CLERK, text=NOTES))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_photo")
    assert "ann:fix" not in str(session.sent(SendMessage)[-1].reply_markup)
