"""Clerk news flow through the real dispatcher with an offline Telegram session."""

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import DeleteMessage, SendMessage, SendPhoto, SendVoice
from aiogram.types import PhotoSize, Sticker, Voice

from sangkat_bot.app import build_dispatcher
from sangkat_bot.config import load_settings
from sangkat_bot.db import set_group
from sangkat_bot.seed import run_seed

from .conftest import DATAEF, SEED
from .tg import callback_update, make_bot, message_update

CLERK, RESIDENT, GROUP = 777, 501, -100900
TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
PHOTOS = [
    PhotoSize(file_id="small", file_unique_id="a", width=90, height=90),
    PhotoSize(file_id="big", file_unique_id="b", width=1280, height=1280),
]
VOICE = Voice(file_id="V1", file_unique_id="v", duration=12)


@pytest.fixture
def app(tmp_path):
    settings = load_settings({"BOT_TOKEN": TOKEN, "ADMIN_USER_IDS": str(CLERK), "DB_PATH": str(tmp_path / "a.db")})
    _, dp = build_dispatcher(settings)
    run_seed(dp["conn"], DATAEF, SEED)
    dp["bot_username"] = "SangkatBot"
    bot, session = make_bot()
    yield dp, bot, session
    dp["conn"].close()


async def feed(app, update):
    dp, bot, _ = app
    await dp.feed_update(bot, update)


def admin_rows(dp):
    return dp["conn"].execute("select * from announcements where source='admin'").fetchall()


async def compose_all_three(app):
    await feed(app, message_update(CLERK, text="/start 120101"))
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, message_update(CLERK, text="ការចាក់វ៉ាក់សាំងកុមារ"))
    await feed(app, message_update(CLERK, photo=PHOTOS))
    await feed(app, message_update(CLERK, voice=VOICE))


async def test_full_flow_publishes_photo_caption_button_and_voice_reply(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    preview_prompt = session.sent(SendMessage)[-1]
    assert preview_prompt.text == copy_tb.t("admin.preview")
    assert [b.callback_data for b in preview_prompt.reply_markup.inline_keyboard[0]] == ["ann:publish", "ann:cancel"]
    preview_photo = session.sent(SendPhoto)[-1]
    assert preview_photo.chat_id == CLERK and preview_photo.photo == "big"

    await feed(app, callback_update(CLERK, "ann:publish"))
    group_photo = [m for m in session.sent(SendPhoto) if m.chat_id == GROUP][-1]
    group_voice = [m for m in session.sent(SendVoice) if m.chat_id == GROUP][-1]
    assert "ការចាក់វ៉ាក់សាំងកុមារ" in group_photo.caption and "សង្កាត់ទន្លេបាសាក់" in group_photo.caption
    assert group_photo.reply_markup.inline_keyboard[0][0].url == "https://t.me/SangkatBot?start=120101"
    assert group_voice.voice == "V1" and group_voice.reply_to_message_id is not None
    (row,) = admin_rows(dp)
    assert row["photo_file_id"] == "big" and row["voice_file_id"] == "V1" and row["posted_by"] == CLERK
    assert row["group_message_id"] and row["group_voice_message_id"]
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.published")
    assert dp["conn"].execute("select action from audit_logs").fetchone()["action"] == "publish"


async def test_publish_before_bind_saves_nothing(app):
    dp, _, session = app
    await compose_all_three(app)
    await feed(app, callback_update(CLERK, "ann:publish"))
    assert "/bind 120101" in session.sent(SendMessage)[-1].text
    assert admin_rows(dp) == []


async def test_telegram_refusal_saves_nothing(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    session.fail_on[SendPhoto] = TelegramForbiddenError(method=None, message="bot was kicked")
    await feed(app, callback_update(CLERK, "ann:publish"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.error_not_admin_in_group")
    assert admin_rows(dp) == []


async def test_skip_everything_asks_again(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(CLERK, text="/announce"))
    for step in ("text", "photo", "voice"):
        await feed(app, callback_update(CLERK, f"ann:skip:{step}"))
    texts = [m.text for m in session.sent(SendMessage)]
    assert copy_tb.t("admin.need_something") in texts
    await feed(app, message_update(CLERK, text="ថ្មី"))  # back on the text step
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_photo")


async def test_sticker_at_photo_step_reprompts(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, callback_update(CLERK, "ann:skip:text"))
    sticker = Sticker(file_id="s", file_unique_id="s", type="regular", width=1, height=1, is_animated=False, is_video=False)
    await feed(app, message_update(CLERK, sticker=sticker))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.wrong_type")
    await feed(app, message_update(CLERK, photo=PHOTOS))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_voice")


async def test_text_only_preview_and_publish(app):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, message_update(CLERK, text="សួស្តី"))
    await feed(app, callback_update(CLERK, "ann:skip:photo"))
    await feed(app, callback_update(CLERK, "ann:skip:voice"))
    await feed(app, callback_update(CLERK, "ann:publish"))
    group_msgs = [m for m in session.sent(SendMessage) if m.chat_id == GROUP]
    assert len(group_msgs) == 1 and "សួស្តី" in group_msgs[0].text
    assert admin_rows(dp)[0]["group_voice_message_id"] is None


async def test_cancel_clears(app, copy_tb):
    dp, _, session = app
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, message_update(CLERK, text="/cancel"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.cancelled")
    await feed(app, message_update(CLERK, text="/start 120101"))
    await feed(app, message_update(CLERK, text="hello"))  # no longer captured as announcement text
    assert session.sent(SendMessage)[-1].text == copy_tb.t("fallback")


async def test_announce_button_label_starts_flow(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(CLERK, text=copy_tb.t("admin.announce_button")))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_content")


async def test_non_admin_cannot_announce(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text="/announce"))
    assert session.sent(SendMessage)[-1].text != copy_tb.t("admin.ask_content")


async def test_delete_last_removes_both_messages(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    await feed(app, callback_update(CLERK, "ann:publish"))
    row = admin_rows(dp)[0]
    await feed(app, message_update(CLERK, text="/delete_last"))
    deleted = {m.message_id for m in session.requests if isinstance(m, DeleteMessage)}
    assert deleted == {row["group_message_id"], row["group_voice_message_id"]}
    assert admin_rows(dp)[0]["is_deleted"] == 1
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.deleted")
    await feed(app, message_update(CLERK, text="/delete_last"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.nothing_to_delete")


async def test_menu_button_during_text_step_leaves_flow(app, copy_tb):
    dp, _, session = app
    await feed(app, message_update(CLERK, text="/start 120101"))
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, message_update(CLERK, text=copy_tb.button("emergency")))
    assert "117" in session.sent(SendMessage)[-1].text
    await feed(app, message_update(CLERK, text="hello"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("fallback")


async def test_menu_button_during_photo_step_leaves_flow(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(CLERK, text="/start 120101"))
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, callback_update(CLERK, "ann:skip:text"))
    await feed(app, message_update(CLERK, text=copy_tb.button("health")))
    assert "មន្ទីរពេទ្យ និងមណ្ឌលសុខភាព" in session.sent(SendMessage)[-1].text
