"""Reply and inline keyboards."""

from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from sangkat_bot.copy import Copy
from sangkat_bot.db import Row


def resident_keyboard(copy: Copy, is_admin: bool) -> ReplyKeyboardMarkup:
    """Big always-visible buttons: 🚨 alone on top, then 2 × 2; clerks get a posting row."""
    rows = [[KeyboardButton(text=copy.button(intent)) for intent in row] for row in copy.keyboard_layout]
    if is_admin:
        rows.append([KeyboardButton(text=copy.t("admin.announce_button"))])
    return ReplyKeyboardMarkup(keyboard=rows, is_persistent=True, resize_keyboard=True)


def commune_picker(communes: Sequence[Row]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{c['commune_kh']} ({c['district_kh']})", callback_data=f"pick:{c['commune_code']}")]
            for c in communes
        ]
    )


def services_menu(services: Sequence[Row]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=s["title_kh"], callback_data=f"svc:{s['service_key']}")] for s in services
        ]
    )


def open_bot_button(copy: Copy, bot_username: str, commune_code: str) -> InlineKeyboardMarkup:
    url = f"https://t.me/{bot_username}?start={commune_code}"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=copy.t("open_bot_button"), url=url)]])
