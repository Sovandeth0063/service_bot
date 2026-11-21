import logging

from aiogram.methods import SendMessage

from .test_handlers_admin import RESIDENT, app, feed  # noqa: F401  (fixture reuse)
from .tg import message_update


async def test_handler_crash_replies_fallback_and_does_not_raise(app, copy_tb):
    dp, _, session = app
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    dp["conn"].close()  # every query now raises sqlite3.ProgrammingError
    await feed(app, message_update(RESIDENT, text=copy_tb.button("emergency")))
    assert session.sent(SendMessage)[-1].text == copy_tb.t("fallback")


async def test_logs_never_contain_user_text(app, caplog):
    caplog.set_level(logging.INFO)
    await feed(app, message_update(RESIDENT, text="/start 120101"))
    await feed(app, message_update(RESIDENT, text="ផ្ទះខ្ញុំឆេះ សូមជួយ"))
    assert "event=intent intent=emergency" in caplog.text
    assert "ផ្ទះខ្ញុំ" not in caplog.text and "សូមជួយ" not in caplog.text
