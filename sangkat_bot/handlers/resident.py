"""Resident side: deep-link start, commune picker, the five buttons, typed text and fallbacks."""

from __future__ import annotations

import logging
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from sangkat_bot.config import Settings
from sangkat_bot.copy import Copy
from sangkat_bot.db import (
    Row,
    emergency_numbers,
    get_service,
    get_user_commune,
    cache_announcement_media,
    latest_announcements,
    list_active_communes,
    local_contacts,
    public_services,
    upsert_user,
)
from sangkat_bot.formatting import emergency_card, hall_card, health_card, service_card
from sangkat_bot.guide import resident_guide
from sangkat_bot.handlers.common import active_codes, commune_or_none, copy_for
from sangkat_bot.keyboards import commune_picker, resident_keyboard, services_menu
from sangkat_bot.keywords import match_intent
from sangkat_bot.posts import build_post, send_post_detailed

log = logging.getLogger(__name__)

def resolve_commune(payload: str | None, stored: str | None, active: set[str]) -> str | None:
    """A valid deep-link code wins; otherwise the user's saved commune if still active; else None."""
    code = (payload or "").strip()
    if code in active:
        return code
    if stored in active:
        return stored
    return None


def resolve_intent(text: str, copy: Copy, keywords: list[tuple[str, str]]) -> str | None:
    return copy.button_intent(text) or match_intent(text, keywords)


def _local_file(path: str | None) -> FSInputFile | None:
    """A news picture/voice stored on disk (paths are relative to the project folder)."""
    return FSInputFile(path) if path and Path(path).is_file() else None


def _keyboard(copy: Copy, user_id: int, settings: Settings):
    return resident_keyboard(copy, is_admin=user_id in settings.admin_user_ids)


async def _send_picker(message: Message, conn: sqlite3.Connection, copy_data: dict) -> None:
    communes = list_active_communes(conn)
    copy = copy_for(copy_data, communes[0] if communes else None)
    await message.answer(copy.t("pick_commune"), reply_markup=commune_picker(communes))


async def _welcome(message: Message, commune: Row, copy_data: dict, settings: Settings, user_id: int) -> None:
    copy = copy_for(copy_data, commune)
    await message.answer(copy.t("welcome"), reply_markup=_keyboard(copy, user_id, settings))


async def on_start(
    message: Message, command: CommandObject, conn: sqlite3.Connection, copy_data: dict, settings: Settings
) -> None:
    user_id = message.from_user.id
    code = resolve_commune(command.args, get_user_commune(conn, user_id), active_codes(conn))
    if code is None:
        await _send_picker(message, conn, copy_data)
        return
    upsert_user(conn, user_id, code)
    await _welcome(message, commune_or_none(conn, code), copy_data, settings, user_id)


async def on_help(message: Message, conn: sqlite3.Connection, copy_data: dict, settings: Settings) -> None:
    """The step-by-step guide; residents who haven't chosen a commune get the picker after it."""
    code = resolve_commune(None, get_user_commune(conn, message.from_user.id), active_codes(conn))
    commune = commune_or_none(conn, code) if code else None
    copy = copy_for(copy_data, commune)
    if commune is None:
        await message.answer(resident_guide(copy))
        await _send_picker(message, conn, copy_data)
        return
    await message.answer(resident_guide(copy), reply_markup=_keyboard(copy, message.from_user.id, settings))


async def on_pick(callback: CallbackQuery, conn: sqlite3.Connection, copy_data: dict, settings: Settings) -> None:
    code = callback.data.removeprefix("pick:")
    await callback.answer()
    if code not in active_codes(conn):
        await _send_picker(callback.message, conn, copy_data)
        return
    upsert_user(conn, callback.from_user.id, code)
    await _welcome(callback.message, commune_or_none(conn, code), copy_data, settings, callback.from_user.id)


async def on_service(callback: CallbackQuery, conn: sqlite3.Connection, copy_data: dict) -> None:
    await callback.answer()
    service = get_service(conn, callback.data.removeprefix("svc:"))
    commune = commune_or_none(conn, get_user_commune(conn, callback.from_user.id))
    if service is not None:
        await callback.message.answer(service_card(service, copy_for(copy_data, commune)))


async def answer_intent(
    message: Message, intent: str | None, commune: Row, copy: Copy, conn: sqlite3.Connection, settings: Settings, bot: Bot
) -> None:
    """Send the card for one intent. Shared by buttons, typed keywords and (later) other routes."""
    code = commune["commune_code"]
    keyboard = _keyboard(copy, message.from_user.id, settings)
    if intent == "emergency":
        local = local_contacts(conn, code, ["police", "fire", "ambulance"]) + local_contacts(
            conn, code, ["hospital"], only_24h=True
        )
        card = emergency_card(emergency_numbers(conn, commune["province_code"]), local, copy, settings.demo_mode)
        await message.answer(card, reply_markup=keyboard, disable_web_page_preview=True)
    elif intent == "health":
        card = health_card(local_contacts(conn, code, ["health_center", "hospital"]), copy, settings.demo_mode)
        await message.answer(card, reply_markup=keyboard, disable_web_page_preview=True)
    elif intent == "announcements":
        rows = latest_announcements(conn, code, datetime.now(UTC))
        if not rows:
            await message.answer(copy.t("no_announcements"), reply_markup=keyboard)
        for row in rows:
            photo = row["photo_file_id"] or _local_file(row["photo_path"])
            voice = row["voice_file_id"] or _local_file(row["voice_path"])
            sends = build_post(copy.t("announcement_header"), row["text_kh"], photo, voice)
            posted = await send_post_detailed(bot, message.chat.id, sends, None)
            if not row["photo_file_id"] or not row["voice_file_id"]:
                cache_announcement_media(conn, row["id"], posted.photo_file_id, posted.voice_file_id)
    elif intent == "services":
        await message.answer(copy.t("services_header"), reply_markup=services_menu(public_services(conn, code)))
    elif intent == "location":
        await message.answer(hall_card(commune, copy, settings.demo_mode), reply_markup=keyboard, disable_web_page_preview=True)
        if commune["lat"] is not None and commune["lon"] is not None:
            await bot.send_location(message.chat.id, commune["lat"], commune["lon"])
    else:
        await message.answer(copy.t("fallback"), reply_markup=keyboard)


async def on_text(
    message: Message,
    conn: sqlite3.Connection,
    copy_data: dict,
    keywords: list[tuple[str, str]],
    settings: Settings,
    bot: Bot,
) -> None:
    started = time.perf_counter()
    code = resolve_commune(None, get_user_commune(conn, message.from_user.id), active_codes(conn))
    if code is None:
        await _send_picker(message, conn, copy_data)
        return
    commune = commune_or_none(conn, code)
    copy = copy_for(copy_data, commune)
    intent = resolve_intent(message.text, copy, keywords)
    await answer_intent(message, intent, commune, copy, conn, settings, bot)
    log.info(
        "event=intent intent=%s commune=%s latency_ms=%d",
        intent or "none", code, (time.perf_counter() - started) * 1000,
    )


async def on_other(message: Message, conn: sqlite3.Connection, copy_data: dict, settings: Settings) -> None:
    """Voice notes, stickers, photos… from residents: point back to the buttons."""
    code = resolve_commune(None, get_user_commune(conn, message.from_user.id), active_codes(conn))
    if code is None:
        await _send_picker(message, conn, copy_data)
        return
    copy = copy_for(copy_data, commune_or_none(conn, code))
    await message.answer(copy.t("non_text_fallback"), reply_markup=_keyboard(copy, message.from_user.id, settings))


def make_router() -> Router:
    """A fresh router per dispatcher (aiogram routers attach to one dispatcher only)."""
    router = Router(name="resident")
    router.message.filter(F.chat.type == "private")
    router.message.register(on_start, CommandStart())
    router.message.register(on_help, Command("help"))
    router.callback_query.register(on_pick, F.data.startswith("pick:"))
    router.callback_query.register(on_service, F.data.startswith("svc:"))
    router.message.register(on_text, F.text)
    router.message.register(on_other)  # resident last: catches every remaining private message
    return router
