"""Resident flow through the real dispatcher with an offline Telegram session."""

from datetime import UTC, datetime

import pytest
from aiogram.methods import SendLocation, SendMessage
from aiogram.types import PhotoSize, Sticker

from sangkat_bot.app import build_dispatcher
from sangkat_bot.config import load_settings
from sangkat_bot.db import get_user_commune, insert_announcement
from sangkat_bot.seed import run_seed

from .conftest import DATAEF, SEED
from .tg import callback_update, make_bot, message_update

RESIDENT, CLERK = 501, 777


@pytest.fixture
def app(tmp_path):
    settings = load_settings({"BOT_TOKEN": "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi", "ADMIN_USER_IDS": str(CLERK), "DB_PATH": str(tmp_path / "h.db")})
    _, dp = build_dispatcher(settings)
    run_seed(dp["conn"], DATAEF, SEED)
    dp["bot_username"] = "SangkatBot"
    bot, session = make_bot()
    yield dp, bot, session
    dp["conn"].close()


async def feed(app, update):
    dp, bot, _ = app
    await dp.feed_update(bot, update)


async def test_deep_link_binds_and_shows_keyboard(app):
    dp, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    reply = session.sent(SendMessage)[-1]
    assert "សង្កាត់ទន្លេបាសាក់" in reply.text
    assert [len(r) for r in reply.reply_markup.keyboard] == [1, 2, 2]
    assert get_user_commune(dp["conn"], RESIDENT) == "120101"


async def test_plain_start_from_new_user_shows_picker(app):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start"))
    reply = session.sent(SendMessage)[-1]
    assert [row[0].callback_data for row in reply.reply_markup.inline_keyboard] == [
        "pick:120101", "pick:120109", "pick:120110", "pick:120111", "pick:120112"
    ]


async def test_picking_another_sangkat_gives_its_own_police_post(app, copy_tb):
    dp, _, session = app
    await feed(app, callback_update(RESIDENT, "pick:120111"))
    assert get_user_commune(dp["conn"], RESIDENT) == "120111"
    assert "សង្កាត់បឹងត្របែក" in session.sent(SendMessage)[-1].text
    await feed(app, message_update(RESIDENT, text=copy_tb.button("emergency")))
    card = session.sent(SendMessage)[-1].text
    assert "078 803 525" in card and "012 496 065" not in card


async def test_picker_callback_binds(app):
    dp, _, session = app
    await feed(app, callback_update(RESIDENT, "pick:120101"))
    assert get_user_commune(dp["conn"], RESIDENT) == "120101"
    assert "សួស្តី" in session.sent(SendMessage)[-1].text


async def test_text_before_binding_shows_picker(app):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="ភ្លើង"))
    assert session.sent(SendMessage)[-1].reply_markup.inline_keyboard[0][0].callback_data == "pick:120101"


async def test_emergency_button(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text=copy_tb.button("emergency")))
    card = session.sent(SendMessage)[-1].text
    assert "117" in card and "666" in card and "កាល់ម៉ែត" in card and "ទិន្នន័យសាកល្បង" in card


async def test_typed_keyword_routes_to_health(app):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text="ខ្ញុំឈឺ"))
    assert "មន្ទីរពេទ្យ និងមណ្ឌលសុខភាព" in session.sent(SendMessage)[-1].text


async def test_location_sends_card_and_pin(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text=copy_tb.button("location")))
    pin = session.sent(SendLocation)[-1]
    assert (pin.latitude, pin.longitude) == (11.550436, 104.931359)


async def test_services_menu_then_card(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text=copy_tb.button("services")))
    assert session.sent(SendMessage)[-1].reply_markup.inline_keyboard[0][0].callback_data == "svc:birth_certificate"
    await feed(app, callback_update(RESIDENT, "svc:birth_certificate"))
    assert session.sent(SendMessage)[-1].text.count("☐") == 4


async def test_news_feed_replays_photo_and_voice(app, copy_tb):
    dp, _, session = app
    insert_announcement(
        dp["conn"], commune_code="120101", source="admin", posted_by=CLERK, text_kh="វ៉ាក់សាំង",
        photo_file_id="PHOTO", voice_file_id="VOICE", event_date=None, expires_at=None, created_at=datetime.now(UTC),
    )
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    before = len(session.sent())
    await feed(app, message_update(RESIDENT, text=copy_tb.button("announcements")))
    sent = session.sent()[before:]
    kinds = [type(m).__name__ for m in sent]
    assert kinds[-2:] == ["SendPhoto", "SendVoice"] and sent[-1].reply_to_message_id is not None
    assert "វ៉ាក់សាំង" in sent[-2].caption


async def test_unknown_text_fallback(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text="hello"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("fallback")


async def test_sticker_gets_non_text_fallback(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    sticker = Sticker(file_id="s", file_unique_id="s", type="regular", width=1, height=1, is_animated=False, is_video=False)
    await feed(app, message_update(RESIDENT, sticker=sticker))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("non_text_fallback")


async def test_clerk_sees_post_button(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(CLERK, text="/start 120101"))
    rows = session.sent(SendMessage)[-1].reply_markup.keyboard
    assert rows[-1][0].text == copy_tb.t("admin.announce_button")


async def test_group_messages_ignored(app):
    _, _, session = app
    await feed(app, message_update(RESIDENT, chat_id=-100200, text="ភ្លើង"))
    assert session.sent() == []
