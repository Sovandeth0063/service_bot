"""Clerk side: post news (text → photo → voice → preview → publish) and /delete_last."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramMigrateToChat
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from sangkat_bot.config import Settings
from sangkat_bot.copy import Copy
from sangkat_bot.db import (
    Row,
    audit,
    get_commune,
    insert_announcement,
    last_admin_announcement,
    mark_deleted,
    set_announcement_messages,
    set_group,
)
from sangkat_bot.handlers.common import copy_for
from sangkat_bot.handlers.resident import answer_intent
from sangkat_bot.keyboards import open_bot_button, resident_keyboard
from sangkat_bot.posts import PartialSendError, build_post, send_post

log = logging.getLogger(__name__)


class AnnounceForm(StatesGroup):
    text = State()
    photo = State()
    voice = State()
    preview = State()


def is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_user_ids


def publish_target(commune: Row | None) -> int | None:
    """The group to post to, or None when the commune is unknown, inactive or not bound yet."""
    if commune is None or not commune["is_active"] or commune["telegram_group_id"] is None:
        return None
    return int(commune["telegram_group_id"])


def _from_admin(event: Message | CallbackQuery, settings: Settings) -> bool:
    return event.from_user is not None and is_admin(event.from_user.id, settings)


def _skip_markup(copy: Copy, step: str) -> InlineKeyboardMarkup:
    """Skip button tagged with its step, so a double tap or an old button can't skip the next step."""
    button = InlineKeyboardButton(text=copy.t("admin.skip"), callback_data=f"ann:skip:{step}")
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def _confirm_markup(copy: Copy) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=copy.t("admin.publish"), callback_data="ann:publish"),
            InlineKeyboardButton(text=copy.t("admin.cancel"), callback_data="ann:cancel"),
        ]]
    )


def _context(conn: sqlite3.Connection, settings: Settings, copy_data: dict) -> tuple[Row | None, Copy]:
    commune = get_commune(conn, settings.demo_commune_code)
    return commune, copy_for(copy_data, commune)


async def _ask_photo(message: Message, state: FSMContext, copy: Copy) -> None:
    await state.set_state(AnnounceForm.photo)
    await message.answer(copy.t("admin.ask_photo"), reply_markup=_skip_markup(copy, "photo"))


async def _ask_voice(message: Message, state: FSMContext, copy: Copy) -> None:
    await state.set_state(AnnounceForm.voice)
    await message.answer(copy.t("admin.ask_voice"), reply_markup=_skip_markup(copy, "voice"))


async def _preview(
    message: Message, state: FSMContext, copy: Copy, commune: Row | None, bot: Bot, bot_username: str
) -> None:
    data = await state.get_data()
    if not (data.get("text_kh") or data.get("photo_file_id") or data.get("voice_file_id")):
        await state.set_state(AnnounceForm.text)
        await message.answer(copy.t("admin.need_something"), reply_markup=_skip_markup(copy, "text"))
        return
    await state.set_state(AnnounceForm.preview)
    sends = build_post(copy.t("announcement_header"), data.get("text_kh"), data.get("photo_file_id"), data.get("voice_file_id"))
    code = commune["commune_code"] if commune else ""
    await send_post(bot, message.chat.id, sends, open_bot_button(copy, bot_username, code))
    await message.answer(copy.t("admin.preview"), reply_markup=_confirm_markup(copy))


async def start_announce(message: Message, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict) -> None:
    _, copy = _context(conn, settings, copy_data)
    await state.clear()
    await state.set_state(AnnounceForm.text)
    await message.answer(copy.t("admin.ask_content"), reply_markup=_skip_markup(copy, "text"))


async def cancel(message: Message, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict) -> None:
    _, copy = _context(conn, settings, copy_data)
    await state.clear()
    await message.answer(copy.t("admin.cancelled"), reply_markup=resident_keyboard(copy, is_admin=True))


async def on_text_step(
    message: Message, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict, bot: Bot, bot_username: str
) -> None:
    """Step 1 asks for "text, picture or voice": accept whichever arrives and jump ahead."""
    commune, copy = _context(conn, settings, copy_data)
    if message.text:
        await state.update_data(text_kh=message.text)
        await _ask_photo(message, state, copy)
    elif message.photo:
        await state.update_data(text_kh=message.caption, photo_file_id=message.photo[-1].file_id)
        await _ask_voice(message, state, copy)
    elif message.voice or message.audio:
        await state.update_data(voice_file_id=(message.voice or message.audio).file_id)
        await _preview(message, state, copy, commune, bot, bot_username)
    else:
        await message.answer(copy.t("admin.wrong_type"), reply_markup=_skip_markup(copy, "text"))


async def _is_menu_button(message: Message, conn: sqlite3.Connection, settings: Settings, copy_data: dict) -> bool:
    """True for a resident keyboard label, e.g. 🚨 tapped in the middle of posting.

    Async on purpose: aiogram runs sync filters in a worker thread, and the SQLite
    connection may only be used on the thread that opened it.
    """
    return bool(message.text) and _context(conn, settings, copy_data)[1].button_intent(message.text) is not None


async def leave_flow_for_menu(
    message: Message, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict, bot: Bot
) -> None:
    """A menu button mid-flow means "I'm done posting": answer it instead of saving it as news."""
    commune, copy = _context(conn, settings, copy_data)
    await state.clear()
    await answer_intent(message, copy.button_intent(message.text), commune, copy, conn, settings, bot)


async def on_photo_step(message: Message, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict) -> None:
    _, copy = _context(conn, settings, copy_data)
    if not message.photo:
        await message.answer(copy.t("admin.wrong_type"), reply_markup=_skip_markup(copy, "photo"))
        return
    await state.update_data(photo_file_id=message.photo[-1].file_id)  # last size is the largest
    await _ask_voice(message, state, copy)


async def on_voice_step(
    message: Message, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict, bot: Bot, bot_username: str
) -> None:
    commune, copy = _context(conn, settings, copy_data)
    media = message.voice or message.audio
    if media is None:
        await message.answer(copy.t("admin.wrong_type"), reply_markup=_skip_markup(copy, "voice"))
        return
    await state.update_data(voice_file_id=media.file_id)
    await _preview(message, state, copy, commune, bot, bot_username)


async def on_skip(
    callback: CallbackQuery, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict, bot: Bot, bot_username: str
) -> None:
    await callback.answer()
    commune, copy = _context(conn, settings, copy_data)
    current = await state.get_state()
    step = callback.data.removeprefix("ann:skip:")
    if current != f"{AnnounceForm.__name__}:{step}":
        return  # double tap, or an old button from an earlier step
    if current == AnnounceForm.text.state:
        await _ask_photo(callback.message, state, copy)
    elif current == AnnounceForm.photo.state:
        await _ask_voice(callback.message, state, copy)
    elif current == AnnounceForm.voice.state:
        await _preview(callback.message, state, copy, commune, bot, bot_username)


async def on_cancel_button(callback: CallbackQuery, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict) -> None:
    await callback.answer()
    _, copy = _context(conn, settings, copy_data)
    await state.clear()
    await callback.message.answer(copy.t("admin.cancelled"), reply_markup=resident_keyboard(copy, is_admin=True))


async def on_publish(
    callback: CallbackQuery, state: FSMContext, conn: sqlite3.Connection, settings: Settings, copy_data: dict, bot: Bot, bot_username: str
) -> None:
    await callback.answer()
    commune, copy = _context(conn, settings, copy_data)
    data = await state.get_data()
    await state.clear()
    if not (data.get("text_kh") or data.get("photo_file_id") or data.get("voice_file_id")):
        return  # a second tap on the publish button after the post already went out
    keyboard = resident_keyboard(copy, is_admin=True)
    target = publish_target(commune)
    if target is None:
        await callback.message.answer(
            copy.t("admin.no_group").replace("{commune_code}", settings.demo_commune_code), reply_markup=keyboard
        )
        return
    code = commune["commune_code"]
    sends = build_post(copy.t("announcement_header"), data.get("text_kh"), data.get("photo_file_id"), data.get("voice_file_id"))
    markup = open_bot_button(copy, bot_username, code)
    reply = "admin.published"
    try:
        try:
            lead_id, voice_id = await send_post(bot, target, sends, markup)
        except TelegramMigrateToChat as moved:  # the group became a supergroup: follow it once
            set_group(conn, code, moved.migrate_to_chat_id)
            lead_id, voice_id = await send_post(bot, moved.migrate_to_chat_id, sends, markup)
    except PartialSendError as partial:  # the post is in the group but the voice reply failed
        log.warning("event=publish_partial commune=%s error=%s", code, type(partial.cause).__name__)
        lead_id, voice_id, reply = partial.lead_id, None, "admin.voice_failed"
    except TelegramAPIError as error:
        log.warning("event=publish_failed commune=%s error=%s", code, type(error).__name__)
        await callback.message.answer(copy.t("admin.error_not_admin_in_group"), reply_markup=keyboard)
        return
    ann_id = insert_announcement(
        conn, commune_code=code, source="admin", posted_by=callback.from_user.id, text_kh=data.get("text_kh"),
        photo_file_id=data.get("photo_file_id"), voice_file_id=data.get("voice_file_id"),
        event_date=None, expires_at=None, created_at=datetime.now(UTC),
    )
    set_announcement_messages(conn, ann_id, lead_id, voice_id)
    audit(conn, callback.from_user.id, code, "publish", str(ann_id), {
        "photo": bool(data.get("photo_file_id")), "voice": bool(data.get("voice_file_id")),
    })
    log.info("event=publish commune=%s announcement=%s", code, ann_id)
    await callback.message.answer(copy.t(reply), reply_markup=keyboard)


async def delete_last(message: Message, conn: sqlite3.Connection, settings: Settings, copy_data: dict, bot: Bot) -> None:
    commune, copy = _context(conn, settings, copy_data)
    keyboard = resident_keyboard(copy, is_admin=True)
    row = last_admin_announcement(conn, settings.demo_commune_code, message.from_user.id)
    if row is None:
        await message.answer(copy.t("admin.nothing_to_delete"), reply_markup=keyboard)
        return
    group_id = publish_target(commune)
    if group_id is not None:
        for message_id in (row["group_message_id"], row["group_voice_message_id"]):
            if message_id:
                try:
                    await bot.delete_message(group_id, message_id)
                except TelegramAPIError:
                    pass  # already deleted by hand, too old, or the bot lost its rights
    mark_deleted(conn, row["id"])
    audit(conn, message.from_user.id, settings.demo_commune_code, "delete", str(row["id"]), {})
    await message.answer(copy.t("admin.deleted"), reply_markup=keyboard)


def make_router() -> Router:
    router = Router(name="admin")
    router.message.filter(F.chat.type == "private", _from_admin)
    router.callback_query.filter(_from_admin)
    router.message.register(cancel, Command("cancel"), StateFilter("*"))
    router.message.register(delete_last, Command("delete_last"))
    router.message.register(start_announce, Command("announce"))
    router.message.register(start_announce, lambda m, copy_data: m.text == copy_data["admin"]["announce_button"])
    router.message.register(
        leave_flow_for_menu, StateFilter(AnnounceForm.text, AnnounceForm.photo, AnnounceForm.voice), _is_menu_button
    )
    router.message.register(on_text_step, AnnounceForm.text)
    router.message.register(on_photo_step, AnnounceForm.photo)
    router.message.register(on_voice_step, AnnounceForm.voice)
    router.callback_query.register(on_skip, F.data.startswith("ann:skip:"))
    router.callback_query.register(on_cancel_button, F.data == "ann:cancel")
    router.callback_query.register(on_publish, F.data == "ann:publish", AnnounceForm.preview)
    return router
