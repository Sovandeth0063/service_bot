"""Offline Telegram for handler tests: a session that records API calls and fakes replies."""

from __future__ import annotations

import asyncio
import itertools
from datetime import datetime

from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import GetMe, SendLocation, SendMessage, SendPhoto, SendVoice, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, PhotoSize, Update, User, Voice

BOT_USER = User(id=999, is_bot=True, first_name="Sangkat", username="SangkatBot")
_ids = itertools.count(1)


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod] = []
        # method type -> Exception, or callable(method) -> Exception | None (fail selectively)
        self.fail_on: dict[type, object] = {}
        self.delay = 0.0  # simulated network latency, lets concurrent updates interleave
        self._message_ids = itertools.count(1000)

    async def make_request(self, bot, method, timeout=None):
        self.requests.append(method)
        if self.delay:
            await asyncio.sleep(self.delay)
        failure = self.fail_on.get(type(method))
        if callable(failure):
            failure = failure(method)
        if failure is not None:
            raise failure
        if isinstance(method, GetMe):
            return BOT_USER
        if isinstance(method, (SendMessage, SendPhoto, SendVoice, SendLocation)):
            chat_type = "private" if int(method.chat_id) > 0 else "supergroup"
            message_id = next(self._message_ids)
            media = {}
            if isinstance(method, SendPhoto):
                media["photo"] = [PhotoSize(file_id=f"photo-{message_id}", file_unique_id=f"p{message_id}", width=1, height=1)]
            if isinstance(method, SendVoice):
                media["voice"] = Voice(file_id=f"voice-{message_id}", file_unique_id=f"v{message_id}", duration=1)
            return Message(
                message_id=message_id, date=datetime.now(), chat=Chat(id=method.chat_id, type=chat_type), **media
            )
        return True

    async def stream_content(self, *args, **kwargs):  # pragma: no cover - not used
        raise NotImplementedError

    async def close(self) -> None:
        pass

    def sent(self, kind: type | None = None) -> list[TelegramMethod]:
        kinds = (SendMessage, SendPhoto, SendVoice, SendLocation) if kind is None else (kind,)
        return [r for r in self.requests if isinstance(r, kinds)]

    def texts(self) -> list[str]:
        return [r.text if isinstance(r, SendMessage) else (getattr(r, "caption", None) or "") for r in self.sent()]


def make_bot() -> tuple[Bot, RecordingSession]:
    session = RecordingSession()
    return Bot("123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi", session=session), session


def user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name=f"u{user_id}")


def message_update(user_id: int, chat_id: int | None = None, **fields) -> Update:
    chat_id = user_id if chat_id is None else chat_id
    chat = Chat(id=chat_id, type="private" if chat_id > 0 else "supergroup")
    msg = Message(message_id=next(_ids), date=datetime.now(), chat=chat, from_user=user(user_id), **fields)
    return Update(update_id=next(_ids), message=msg)


def callback_update(user_id: int, data: str) -> Update:
    msg = Message(message_id=next(_ids), date=datetime.now(), chat=Chat(id=user_id, type="private"))
    cb = CallbackQuery(id=str(next(_ids)), from_user=user(user_id), chat_instance="c", data=data, message=msg)
    return Update(update_id=next(_ids), callback_query=cb)
