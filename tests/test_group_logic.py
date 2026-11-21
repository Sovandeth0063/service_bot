import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import PinChatMessage, SendMessage

from sangkat_bot.db import get_commune
from sangkat_bot.handlers.group import parse_bind_args

from .test_handlers_admin import CLERK, RESIDENT, app, feed  # noqa: F401  (fixture reuse)
from .tg import message_update

GROUP = -100700


def test_parse_bind_valid():
    assert parse_bind_args(" 120101 ", {"120101"}) == "120101"


@pytest.mark.parametrize("args", [None, "", "999999", "12010", "010201"])
def test_parse_bind_invalid(args):
    assert parse_bind_args(args, {"120101"}) is None


async def test_bind_saves_group_and_pins_onboarding(app, copy_tb):
    dp, _, session = app
    await feed(app, message_update(CLERK, chat_id=GROUP, text="/bind 120101"))
    assert get_commune(dp["conn"], "120101")["telegram_group_id"] == GROUP
    texts = [m.text for m in session.sent(SendMessage) if m.chat_id == GROUP]
    assert texts[0] == copy_tb.t("admin.bound") and texts[1] == copy_tb.t("welcome")
    onboarding = [m for m in session.sent(SendMessage) if m.chat_id == GROUP][1]
    assert onboarding.reply_markup.inline_keyboard[0][0].url == "https://t.me/SangkatBot?start=120101"
    assert any(isinstance(r, PinChatMessage) and r.chat_id == GROUP for r in session.requests)
    assert dp["conn"].execute("select action from audit_logs").fetchone()["action"] == "bind"


async def test_bind_pin_failure_is_reported(app, copy_tb):
    dp, _, session = app
    session.fail_on[PinChatMessage] = TelegramBadRequest(method=None, message="not enough rights")
    await feed(app, message_update(CLERK, chat_id=GROUP, text="/bind 120101"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.pin_failed")
    assert get_commune(dp["conn"], "120101")["telegram_group_id"] == GROUP


async def test_bind_by_non_admin_is_ignored(app):
    dp, _, session = app
    await feed(app, message_update(RESIDENT, chat_id=GROUP, text="/bind 120101"))
    assert session.sent() == [] and get_commune(dp["conn"], "120101")["telegram_group_id"] is None


async def test_bind_with_bad_code_is_ignored(app):
    dp, _, session = app
    await feed(app, message_update(CLERK, chat_id=GROUP, text="/bind 999999"))
    assert get_commune(dp["conn"], "120101")["telegram_group_id"] is None


async def test_bind_mentioning_bot_username(app):
    dp, _, _ = app
    await feed(app, message_update(CLERK, chat_id=GROUP, text="/bind@SangkatBot 120101"))
    assert get_commune(dp["conn"], "120101")["telegram_group_id"] == GROUP
