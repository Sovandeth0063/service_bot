"""How an announcement becomes Telegram messages. One rule, used for the group post,
the clerk's preview and the resident 📢 feed (spec §5.4)."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Literal

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

# Telegram's caption limit. We measure the HTML string, which is never shorter than the
# visible text Telegram counts, so this errs on the safe side.
CAPTION_LIMIT = 1024


class PartialSendError(Exception):
    """The lead message went out but a later part (e.g. the voice reply) failed."""

    def __init__(self, lead_id: int, cause: Exception) -> None:
        super().__init__(f"sent lead {lead_id}, then failed: {type(cause).__name__}")
        self.lead_id = lead_id
        self.cause = cause


@dataclass(frozen=True)
class Send:
    kind: Literal["text", "photo", "voice"]
    text: str | None
    file_id: str | None
    is_lead: bool
    reply_to_lead: bool


def announcement_body(header: str, text_kh: str | None) -> str:
    body = f"<b>{escape(header)}</b>"
    return f"{body}\n\n{escape(text_kh)}" if text_kh and text_kh.strip() else body


def build_post(
    header: str, text_kh: str | None, photo_file_id: str | None, voice_file_id: str | None
) -> list[Send]:
    """Lead message (photo+caption, or text) carrying the button, then voice as a reply."""
    text = text_kh if text_kh and text_kh.strip() else None
    if not (text or photo_file_id or voice_file_id):
        raise ValueError("an announcement needs text, a photo or a voice note")
    body = announcement_body(header, text)
    sends: list[Send] = []
    if photo_file_id and len(body) <= CAPTION_LIMIT:
        sends.append(Send("photo", body, photo_file_id, True, False))
    elif photo_file_id:
        sends.append(Send("text", body, None, True, False))
        sends.append(Send("photo", announcement_body(header, None), photo_file_id, False, False))
    else:
        sends.append(Send("text", body, None, True, False))
    if voice_file_id:
        sends.append(Send("voice", None, voice_file_id, False, True))
    return sends


async def send_post(
    bot: Bot, chat_id: int, sends: list[Send], lead_markup: InlineKeyboardMarkup | None
) -> tuple[int, int | None]:
    """Send the messages in order; return (lead message id, voice message id or None).

    A failure before the lead is sent propagates as-is; a failure after it raises PartialSendError
    so the caller can still record the lead message (and delete it later).
    """
    lead_id: int | None = None
    voice_id: int | None = None
    for send in sends:
        try:
            message = await _send_one(bot, chat_id, send, lead_markup if send.is_lead else None, lead_id)
        except Exception as error:
            if lead_id is None:
                raise
            raise PartialSendError(lead_id, error) from error
        if send.kind == "voice":
            voice_id = message.message_id
        if send.is_lead:
            lead_id = message.message_id
    assert lead_id is not None  # build_post always produces a lead message
    return lead_id, voice_id


async def _send_one(bot: Bot, chat_id: int, send: Send, markup: InlineKeyboardMarkup | None, lead_id: int | None):
    if send.kind == "text":
        return await bot.send_message(chat_id, send.text or "", reply_markup=markup, parse_mode="HTML")
    if send.kind == "photo":
        return await bot.send_photo(chat_id, send.file_id, caption=send.text, reply_markup=markup, parse_mode="HTML")
    return await bot.send_voice(chat_id, send.file_id, reply_to_message_id=lead_id)
