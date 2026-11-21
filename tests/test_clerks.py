"""Clerk roles: super-admins manage clerks by @username; a clerk posts only for their own sangkat."""

import pytest
from aiogram.methods import SendMessage, SetMyCommands

from sangkat_bot.app import build_dispatcher
from sangkat_bot.clerks import normalize_username, role_of
from sangkat_bot.config import load_settings
from sangkat_bot.db import get_commune, set_group
from sangkat_bot.seed import run_seed

from .conftest import DATAEF, SEED
from .tg import callback_update, make_bot, message_update

TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
BOSS, CLERK, STRANGER = 100, 200, 300  # BOSS is a super-admin by username (.env ADMIN_USERNAMES)
GROUP_TB, GROUP_OTHER = -100111, -100222


@pytest.fixture
def app(tmp_path):
    settings = load_settings({
        "BOT_TOKEN": TOKEN, "ADMIN_USERNAMES": "Sovandeth_Hour", "DB_PATH": str(tmp_path / "c.db"),
    })
    _, dp = build_dispatcher(settings)
    run_seed(dp["conn"], DATAEF, SEED)
    dp["bot_username"] = "SangkatBot"
    bot, session = make_bot()
    yield dp, bot, session
    dp["conn"].close()


async def feed(app, update):
    dp, bot, _ = app
    await dp.feed_update(bot, update)


async def boss(app, text):
    await feed(app, message_update(BOSS, username="sovandeth_hour", text=text))


def last_text(session):
    return session.sent(SendMessage)[-1].text


def keyboard_labels(message):
    return [b.text for row in (message.reply_markup.keyboard if message.reply_markup else []) for b in row]


def admin_rows(dp):
    return dp["conn"].execute("select * from announcements where source='admin'").fetchall()


@pytest.mark.parametrize("raw, expected", [
    ("@Sok_Dara", "sok_dara"), ("sok_dara", "sok_dara"), ("https://t.me/Sok_Dara", "sok_dara"),
    ("t.me/sok_dara", "sok_dara"), ("@abc", None), ("bad name", None), ("", None), (None, None),
])
def test_normalize_username(raw, expected):
    assert normalize_username(raw) == expected


async def test_super_admin_by_username_is_linked_on_first_message(app, copy_tb):
    dp, _, session = app
    assert role_of(dp["conn"], dp["settings"], BOSS) is None
    await boss(app, "/start 120101")
    role = role_of(dp["conn"], dp["settings"], BOSS)
    assert role is not None and role.is_super
    assert copy_tb.t("admin.announce_button") in keyboard_labels(session.sent(SendMessage)[-1])


async def test_add_clerk_then_clerk_links_on_start_and_gets_menu(app, copy_tb):
    dp, _, session = app
    await boss(app, "/addclerk @Sok_Dara 120111")
    assert "@sok_dara" in last_text(session)
    assert role_of(dp["conn"], dp["settings"], CLERK) is None  # not linked until they write to the bot

    await feed(app, message_update(CLERK, username="sok_dara", text="/start"))
    role = role_of(dp["conn"], dp["settings"], CLERK)
    assert role is not None and not role.is_super and role.commune_code == "120111"
    texts = session.texts()
    assert any("បឹងត្របែក" in t and "📝" in t for t in texts)  # the welcome names their sangkat
    menus = [m for m in session.requests if isinstance(m, SetMyCommands) and getattr(m.scope, "chat_id", None) == CLERK]
    assert menus and "announce" in [c.command for c in menus[-1].commands]
    assert "addclerk" not in [c.command for c in menus[-1].commands]


async def test_role_stays_with_the_account_not_the_username(app):
    dp, _, _ = app
    await boss(app, "/addclerk @sok_dara 120111")
    await feed(app, message_update(CLERK, username="sok_dara", text="/start 120111"))
    await feed(app, message_update(CLERK, username="sok_dara_new", text="/help"))  # they renamed themselves
    assert role_of(dp["conn"], dp["settings"], CLERK).commune_code == "120111"
    await feed(app, message_update(STRANGER, username="sok_dara", text="/start 120101"))  # someone took the old name
    assert role_of(dp["conn"], dp["settings"], STRANGER) is None


async def test_clerk_sees_only_their_sangkat_and_forged_targets_do_nothing(app, copy_tb):
    dp, _, session = app
    await boss(app, "/addclerk @sok_dara 120111")
    await feed(app, message_update(CLERK, username="sok_dara", text="/start 120111"))
    await feed(app, message_update(CLERK, username="sok_dara", text="/announce"))
    await feed(app, message_update(CLERK, username="sok_dara", text="ការចាក់វ៉ាក់សាំង"))
    await feed(app, callback_update(CLERK, "ann:skip:photo", username="sok_dara"))
    await feed(app, callback_update(CLERK, "ann:skip:voice", username="sok_dara"))
    buttons = [b.callback_data for row in session.sent(SendMessage)[-1].reply_markup.inline_keyboard for b in row]
    assert buttons == ["ann:publish:120111", "ann:cancel"]

    await feed(app, callback_update(CLERK, "ann:publish:all", username="sok_dara"))
    await feed(app, callback_update(CLERK, "ann:publish:120101", username="sok_dara"))
    assert admin_rows(dp) == []
    await feed(app, callback_update(CLERK, "ann:publish:120111", username="sok_dara"))
    assert [r["commune_code"] for r in admin_rows(dp)] == ["120111"]


async def test_remove_clerk_takes_effect_immediately(app, copy_tb):
    dp, _, session = app
    await boss(app, "/addclerk @sok_dara 120111")
    await feed(app, message_update(CLERK, username="sok_dara", text="/start 120111"))
    await boss(app, "/removeclerk sok_dara")
    assert "@sok_dara" in last_text(session)
    assert role_of(dp["conn"], dp["settings"], CLERK) is None
    await feed(app, message_update(CLERK, username="sok_dara", text="/announce"))
    assert copy_tb.t("admin.ask_content") not in session.texts()[-1]
    await feed(app, message_update(CLERK, username="sok_dara", text="/help"))
    assert copy_tb.t("admin.announce_button") not in keyboard_labels(session.sent(SendMessage)[-1])


async def test_clerks_list_shows_linked_and_waiting(app, copy_tb):
    _, _, session = app
    await boss(app, "/addclerk @sok_dara 120111")
    await boss(app, "/addclerk @chan_thy 120101")
    await feed(app, message_update(CLERK, username="sok_dara", text="/start"))
    await boss(app, "/clerks")
    listing = last_text(session)
    sok = next(line for line in listing.splitlines() if "@sok_dara" in line)
    chan = next(line for line in listing.splitlines() if "@chan_thy" in line)
    assert copy_tb.t("admin.clerk_linked") in sok and "បឹងត្របែក" in sok
    assert copy_tb.t("admin.clerk_pending") in chan
    assert "@sovandeth_hour" in listing


@pytest.mark.parametrize("command", ["/addclerk", "/addclerk @sok_dara", "/addclerk @x 120111", "/addclerk @sok_dara 999999"])
async def test_add_clerk_bad_input_explains_usage(app, copy_tb, command):
    dp, _, session = app
    await boss(app, command)
    assert "/addclerk" in last_text(session)
    assert dp["conn"].execute("select count(*) from clerks where role='clerk'").fetchone()[0] == 0


async def test_only_super_admins_manage_clerks(app):
    dp, _, _ = app
    await boss(app, "/addclerk @sok_dara 120111")
    await feed(app, message_update(CLERK, username="sok_dara", text="/start"))
    await feed(app, message_update(CLERK, username="sok_dara", text="/addclerk @friend_one 120111"))
    await feed(app, message_update(STRANGER, username="random_guy", text="/addclerk @random_guy 120101"))
    await feed(app, message_update(CLERK, username="sok_dara", text="/removeclerk @sovandeth_hour"))
    usernames = {r["username"] for r in dp["conn"].execute("select username from clerks")}
    assert usernames == {"sok_dara", "sovandeth_hour"}


async def test_super_admin_from_env_cannot_be_removed_by_command(app, copy_tb):
    dp, _, session = app
    await boss(app, "/removeclerk @sovandeth_hour")
    assert last_text(session) == copy_tb.t("admin.clerk_is_super").replace("{username}", "sovandeth_hour")
    assert role_of(dp["conn"], dp["settings"], BOSS).is_super


async def test_clerk_binds_and_guides_only_their_own_group(app):
    dp, _, session = app
    await boss(app, "/addclerk @sok_dara 120111")
    await feed(app, message_update(CLERK, username="sok_dara", text="/start"))
    await feed(app, message_update(CLERK, chat_id=GROUP_OTHER, username="sok_dara", text="/bind 120101"))
    assert get_commune(dp["conn"], "120101")["telegram_group_id"] is None
    await feed(app, message_update(CLERK, chat_id=GROUP_TB, username="sok_dara", text="/bind 120111"))
    assert get_commune(dp["conn"], "120111")["telegram_group_id"] == GROUP_TB

    set_group(dp["conn"], "120101", GROUP_OTHER)
    before = len(session.sent(SendMessage))
    await feed(app, message_update(CLERK, chat_id=GROUP_OTHER, username="sok_dara", text="/guide"))
    assert len(session.sent(SendMessage)) == before


async def test_removing_a_username_from_env_drops_its_super_role(tmp_path):
    db = str(tmp_path / "r.db")
    _, dp = build_dispatcher(load_settings({"BOT_TOKEN": TOKEN, "ADMIN_USERNAMES": "sovandeth_hour", "DB_PATH": db}))
    run_seed(dp["conn"], DATAEF, SEED)
    bot, _ = make_bot()
    await dp.feed_update(bot, message_update(BOSS, username="sovandeth_hour", text="/start 120101"))
    assert role_of(dp["conn"], dp["settings"], BOSS).is_super
    dp["conn"].close()
    _, dp2 = build_dispatcher(load_settings({"BOT_TOKEN": TOKEN, "ADMIN_USERNAMES": "", "DB_PATH": db}))
    assert role_of(dp2["conn"], dp2["settings"], BOSS) is None
    dp2["conn"].close()


async def test_any_resident_gets_every_public_button(app, copy_tb):
    """Public information is for everyone: a resident with a username and no role gets every card."""
    _, _, session = app
    await feed(app, message_update(STRANGER, username="random_guy", text="/start 120101"))
    assert keyboard_labels(session.sent(SendMessage)[-1]) == [
        copy_tb.button(i) for i in ("emergency", "health", "announcements", "services", "location")
    ]
    for intent in ("emergency", "health", "announcements", "services", "location"):
        before = len(session.requests)
        await feed(app, message_update(STRANGER, username="random_guy", text=copy_tb.button(intent)))
        replies = session.requests[before:]
        assert replies, intent
        assert all(getattr(r, "text", None) != copy_tb.t("fallback") for r in replies), intent


async def test_resident_cannot_post_or_delete(app, copy_tb):
    dp, _, session = app
    await feed(app, message_update(STRANGER, username="random_guy", text="/start 120101"))
    assert copy_tb.t("admin.announce_button") not in keyboard_labels(session.sent(SendMessage)[-1])
    for text in ("/announce", copy_tb.t("admin.announce_button"), "/delete_last", "/addclerk @random_guy 120101"):
        await feed(app, message_update(STRANGER, username="random_guy", text=text))
        assert copy_tb.t("admin.ask_content") not in last_text(session)
        assert copy_tb.t("admin.ask_content_ai") not in last_text(session)
    for data in ("ann:publish:120101", "ann:publish:all", "ann:fix", "ann:skip:photo"):
        await feed(app, callback_update(STRANGER, data, username="random_guy"))
    assert admin_rows(dp) == []
    assert role_of(dp["conn"], dp["settings"], STRANGER) is None
