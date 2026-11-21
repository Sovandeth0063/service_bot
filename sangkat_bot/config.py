"""Settings read from the environment (and `.env` when running the bot)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_FALSE_VALUES = {"false", "0", "no"}


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_user_ids: frozenset[int]
    demo_commune_code: str
    db_path: Path
    seed_dir: Path
    dataef_dir: Path
    demo_mode: bool


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build settings from `env`, or from `os.environ` after loading `.env`."""
    if env is None:
        load_dotenv()
        env = os.environ
    token = env.get("BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("BOT_TOKEN is not set")
    admins = frozenset(
        int(part) for part in env.get("ADMIN_USER_IDS", "").split(",") if part.strip()
    )
    return Settings(
        bot_token=token,
        admin_user_ids=admins,
        demo_commune_code=env.get("DEMO_COMMUNE_CODE", "120101").strip() or "120101",
        db_path=Path(env.get("DB_PATH", "data/sangkat.db")),
        seed_dir=Path("data/seed"),
        dataef_dir=Path("data/raw/dataef"),
        demo_mode=env.get("DEMO_MODE", "true").strip().lower() not in _FALSE_VALUES,
    )
