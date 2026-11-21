"""The clerk chooses which sangkat a post is for: one of them, or all of them."""

from aiogram.methods import DeleteMessage, SendMessage, SendPhoto

from sangkat_bot.db import set_group

from .test_handlers_admin import CLERK, GROUP, RESIDENT, admin_rows, app, compose_all_three, feed  # noqa: F401
from .tg import callback_update, message_update

ALL = ["120101", "120109", "120110", "120111", "120112"]


async def test_preview_offers_each_sangkat_then_all_then_cancel(app, copy_tb):
    _, _, session = app
    await compose_all_three(app)
    prompt = session.sent(SendMessage)[-1]
    assert prompt.text == copy_tb.t("admin.preview")
    callbacks = [row[0].callback_data for row in prompt.reply_markup.inline_keyboard]
    assert callbacks == [f"ann:publish:{code}" for code in ALL] + ["ann:publish:all", "ann:cancel"]
    assert prompt.reply_markup.inline_keyboard[1][0].text == "✅ ទួលទំពូងទី ២"


async def test_publish_to_all_reaches_every_feed_and_bound_group(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    await feed(app, callback_update(CLERK, "ann:publish:all"))

    rows = admin_rows(dp)
    assert sorted(r["commune_code"] for r in rows) == ALL
    assert len({r["publish_id"] for r in rows}) == 1 and rows[0]["publish_id"]
    assert [m.chat_id for m in session.sent(SendPhoto) if m.chat_id < 0] == [GROUP]
    reply = session.sent(SendMessage)[-1].text
    assert reply.startswith(copy_tb.t("admin.published"))
    assert "/bind 120109" in reply and "/bind 120112" in reply and "/bind 120101" not in reply

    await feed(app, callback_update(RESIDENT, "pick:120111"))
    await feed(app, message_update(RESIDENT, text=copy_tb.button("announcements")))
    newest = session.sent(SendPhoto)[-1]
    assert newest.chat_id == RESIDENT and "សង្កាត់បឹងត្របែក" in newest.caption and "ការចាក់វ៉ាក់សាំងកុមារ" in newest.caption


async def test_publish_to_one_other_sangkat_only(app, copy_tb):
    dp, _, session = app
    await compose_all_three(app)
    await feed(app, callback_update(CLERK, "ann:publish:120111"))
    assert [r["commune_code"] for r in admin_rows(dp)] == ["120111"]
    assert "/bind 120111" in session.sent(SendMessage)[-1].text


async def test_unknown_or_inactive_target_is_ignored(app):
    dp, _, _ = app
    await compose_all_three(app)
    await feed(app, callback_update(CLERK, "ann:publish:010201"))
    assert admin_rows(dp) == []


async def test_delete_last_removes_every_copy_of_one_post(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await compose_all_three(app)
    await feed(app, callback_update(CLERK, "ann:publish:all"))
    bound = next(r for r in admin_rows(dp) if r["commune_code"] == "120101")
    await feed(app, message_update(CLERK, text="/delete_last"))
    assert all(r["is_deleted"] == 1 for r in admin_rows(dp))
    deleted = {m.message_id for m in session.requests if isinstance(m, DeleteMessage)}
    assert deleted == {bound["group_message_id"], bound["group_voice_message_id"]}
    assert session.sent(SendMessage)[-1].text == copy_tb.t("admin.deleted")
