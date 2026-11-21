from aiogram.methods import PinChatMessage, SendMessage, SetMyCommands
from aiogram.types import (
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    ReplyKeyboardMarkup,
)

from sangkat_bot.app import setup_commands
from sangkat_bot.db import commune_for_group, set_group
from sangkat_bot.guide import group_guide, resident_guide

from .test_handlers_admin import CLERK, RESIDENT, app, feed  # noqa: F401  (fixture reuse)
from .tg import make_bot, message_update, user

GROUP = -100800


def test_resident_guide_lists_every_button_in_keyboard_order(copy_tb):
    text = resident_guide(copy_tb)
    labels = [copy_tb.button(intent) for row in copy_tb.keyboard_layout for intent in row]
    positions = [text.index(label) for label in labels]
    assert positions == sorted(positions)
    for row in copy_tb.keyboard_layout:
        for intent in row:
            assert copy_tb.t(f"guide.items.{intent}") in text
    assert "សង្កាត់ទន្លេបាសាក់" in text and "/help" in text


def test_group_guide_names_the_open_bot_button(copy_tb):
    text = group_guide(copy_tb)
    assert copy_tb.t("open_bot_button") in text and "{open_bot_button}" not in text


def test_commune_for_group(conn):
    assert commune_for_group(conn, GROUP) is None
    set_group(conn, "120101", GROUP)
    assert commune_for_group(conn, GROUP) == "120101"


async def test_help_shows_guide_with_keyboard(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text="/help"))
    last = session.sent(SendMessage)[-1]
    assert last.text == resident_guide(copy_tb) and isinstance(last.reply_markup, ReplyKeyboardMarkup)


async def test_help_before_choosing_commune_shows_guide_then_picker(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(RESIDENT, text="/help"))
    first, second = session.sent(SendMessage)[-2:]
    assert copy_tb.t("guide.items.emergency") in first.text
    assert second.text == copy_tb.t("pick_commune")


async def test_guide_in_bound_group_posts_and_pins(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await feed(app, message_update(CLERK, chat_id=GROUP, text="/guide"))
    (post,) = [m for m in session.sent(SendMessage) if m.chat_id == GROUP]
    assert post.text == group_guide(copy_tb)
    assert post.reply_markup.inline_keyboard[0][0].url == "https://t.me/SangkatBot?start=120101"
    assert any(isinstance(r, PinChatMessage) and r.chat_id == GROUP for r in session.requests)


async def test_guide_in_unbound_group_says_bind_first(app, copy_tb):
    _, _, session = app
    await feed(app, message_update(CLERK, chat_id=GROUP, text="/guide"))
    assert "/bind 120101" in session.sent(SendMessage)[-1].text


async def test_guide_by_non_admin_is_ignored(app):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    await feed(app, message_update(RESIDENT, chat_id=GROUP, text="/guide"))
    assert session.sent() == []


async def test_setup_commands_menus(app):
    dp, _, _ = app
    bot, session = make_bot()
    await setup_commands(bot, dp["copy_data"], dp["settings"])
    menus = {type(r.scope): r for r in session.requests if isinstance(r, SetMyCommands)}
    names = lambda scope: [c.command for c in menus[scope].commands]  # noqa: E731
    assert names(BotCommandScopeAllPrivateChats) == ["start", "help"]
    assert names(BotCommandScopeChat) == ["start", "help", "announce", "delete_last", "cancel", "clerks", "addclerk", "removeclerk"]
    assert menus[BotCommandScopeChat].scope.chat_id == CLERK
    assert names(BotCommandScopeAllGroupChats) == ["help"]
    assert names(BotCommandScopeAllChatAdministrators) == ["help", "bind", "guide"]


def group_sends(session):
    return [m for m in session.sent(SendMessage) if m.chat_id == GROUP]


async def test_new_member_is_welcomed_with_the_open_bot_button(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    friend = user(888).model_copy(update={"first_name": "Dara <3"})
    await feed(app, message_update(888, chat_id=GROUP, new_chat_members=[friend]))
    (post,) = group_sends(session)
    assert "Dara &lt;3" in post.text and "សង្កាត់ទន្លេបាសាក់" in post.text
    assert copy_tb.t("open_bot_button") in post.text
    assert post.reply_markup.inline_keyboard[0][0].url == "https://t.me/SangkatBot?start=120101"
    assert not any(isinstance(r, PinChatMessage) for r in session.requests)  # the pinned guide stays pinned


async def test_bots_joining_and_unbound_groups_get_no_welcome(app):
    dp, _, session = app
    robot = user(889).model_copy(update={"is_bot": True})
    await feed(app, message_update(889, chat_id=GROUP, new_chat_members=[user(888)]))  # group not bound
    set_group(dp["conn"], "120101", GROUP)
    await feed(app, message_update(889, chat_id=GROUP, new_chat_members=[robot]))
    assert group_sends(session) == []


async def test_any_member_asking_for_help_in_the_group_gets_the_button(app, copy_tb):
    dp, _, session = app
    set_group(dp["conn"], "120101", GROUP)
    for text in ("/help", "/help@SangkatBot", "/start"):
        await feed(app, message_update(RESIDENT, chat_id=GROUP, text=text))
    posts = group_sends(session)
    assert len(posts) == 3
    assert all(p.text == group_guide(copy_tb) for p in posts)
    assert all(p.reply_markup.inline_keyboard[0][0].url == "https://t.me/SangkatBot?start=120101" for p in posts)
    assert not any(isinstance(r, PinChatMessage) for r in session.requests)


async def test_help_in_unbound_group_and_plain_chat_stay_silent(app):
    dp, _, session = app
    await feed(app, message_update(RESIDENT, chat_id=GROUP, text="/help"))
    set_group(dp["conn"], "120101", GROUP)
    await feed(app, message_update(RESIDENT, chat_id=GROUP, text="hello everyone"))
    assert group_sends(session) == []
