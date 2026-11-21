"""Regression tests for the final-review findings (clerk flow robustness, phone format)."""

import asyncio

from aiogram.exceptions import TelegramMigrateToChat, TelegramNetworkError
from aiogram.methods import AnswerCallbackQuery, SendMessage, SendPhoto, SendVoice

from sangkat_bot.db import emergency_numbers, get_commune, set_group
from sangkat_bot.formatting import emergency_card

from .test_handlers_admin import CLERK, GROUP, PHOTOS, VOICE, admin_rows, app, compose_all_three, feed  # noqa: F401
from .tg import callback_update, message_update


# Important 1: step 1 accepts what its prompt asks for (text, picture or voice).
async def test_photo_with_caption_at_first_step(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, message_update(CLERK, photo=PHOTOS, caption="ដំណឹងរូបភាព"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.ask_voice")
    await feed(app, callback_update(CLERK, "ann:skip:voice"))
    await feed(app, callback_update(CLERK, "ann:publish:120101"))
    (row,) = admin_rows(dp)
    assert row["text_kh"] == "ដំណឹងរូបភាព" and row["photo_file_id"] == "big"


async def test_voice_at_first_step_goes_to_preview(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, message_update(CLERK, voice=VOICE))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.preview")


# Important 2: double taps and stale buttons.
async def test_double_tap_publish_posts_once_without_fallback(app, copy_tb):
    dp, bot, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    session.delay = 0.02
    await asyncio.gather(
        dp.feed_update(bot, callback_update(CLERK, "ann:publish:120101")),
        dp.feed_update(bot, callback_update(CLERK, "ann:publish:120101")),
    )
    assert len(admin_rows(dp)) == 1
    texts = [m.text for m in session.sent(SendMessage) if m.chat_id == CLERK]
    assert copy_tb.t("fallback") not in texts and texts.count(copy_tb.t("admin.published")) == 1


async def test_double_tap_skip_skips_one_step(app, copy_tb):
    dp, bot, session = app
    await feed(app, message_update(CLERK, text="/announce"))
    session.delay = 0.02
    await asyncio.gather(
        dp.feed_update(bot, callback_update(CLERK, "ann:skip:text")),
        dp.feed_update(bot, callback_update(CLERK, "ann:skip:text")),
    )
    prompts = [m.text for m in session.sent(SendMessage)]
    assert prompts.count(copy_tb.t("admin.ask_photo")) == 1 and copy_tb.t("admin.ask_voice") not in prompts


async def test_stale_skip_button_is_ignored(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(CLERK, text="/announce"))
    await feed(app, callback_update(CLERK, "ann:skip:text"))  # now on the photo step
    await feed(app, callback_update(CLERK, "ann:skip:text"))  # old button from step 1
    assert copy_tb.t("admin.ask_voice") not in [m.text for m in session.sent(SendMessage)]


async def test_late_publish_tap_is_answered(app):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    await feed(app, callback_update(CLERK, "ann:publish:120101"))
    answered = len([r for r in session.requests if isinstance(r, AnswerCallbackQuery)])
    await feed(app, callback_update(CLERK, "ann:publish:120101"))  # state already cleared
    assert len([r for r in session.requests if isinstance(r, AnswerCallbackQuery)]) == answered + 1
    assert len(admin_rows(dp)) == 1


# Important 3: national numbers go through format_phone and are not bold (tap-to-call).
def test_national_numbers_plain_and_formatted(conn, copy_tb):
    card = emergency_card(emergency_numbers(conn, "12"), [], copy_tb, demo_mode=False)
    assert "<b>117</b>" not in card and "<b>ប៉ូលីស</b>  117" in card


# Important 4: other Telegram errors during publish.
async def test_group_upgraded_to_supergroup_is_followed(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", -100)
    await compose_all_three(app)
    session.fail_on[SendPhoto] = lambda m: (
        TelegramMigrateToChat(method=m, message="group upgraded", migrate_to_chat_id=-100555) if m.chat_id == -100 else None
    )
    await feed(app, callback_update(CLERK, "ann:publish:120101"))
    assert get_commune(dp["conn"], "120101")["telegram_group_id"] == -100555
    assert [m.chat_id for m in session.sent(SendPhoto)][-1] == -100555
    assert len(admin_rows(dp)) == 1 and session.sent(SendMessage)[-1].text == copy_tb.t("admin.published")


async def test_network_error_tells_clerk(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    session.fail_on[SendPhoto] = lambda m: TelegramNetworkError(method=m, message="timeout") if m.chat_id == GROUP else None
    await feed(app, callback_update(CLERK, "ann:publish:120101"))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.error_not_admin_in_group")
    assert admin_rows(dp) == []


async def test_voice_failure_after_lead_still_saves_for_delete(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    session.fail_on[SendVoice] = lambda m: TelegramNetworkError(method=m, message="timeout") if m.chat_id == GROUP else None
    await feed(app, callback_update(CLERK, "ann:publish:120101"))
    (row,) = admin_rows(dp)
    assert row["group_message_id"] is not None and row["group_voice_message_id"] is None
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.voice_failed")
