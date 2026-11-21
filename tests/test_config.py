from pathlib import Path

import pytest

from sangkat_bot.config import load_settings


def test_load_settings_parses_values():
    s = load_settings({"BOT_TOKEN": "t", "ADMIN_USER_IDS": "1, 22", "DEMO_MODE": "false"})
    assert s.bot_token == "t" and s.admin_user_ids == frozenset({1, 22})
    assert s.demo_commune_code == "120101" and s.demo_mode is False
    assert s.db_path == Path("data/sangkat.db")


def test_missing_token_raises():
    with pytest.raises(ValueError, match="BOT_TOKEN is not set"):
        load_settings({})


def test_empty_admin_list_is_allowed():
    assert load_settings({"BOT_TOKEN": "t"}).admin_user_ids == frozenset()


def test_demo_mode_defaults_true():
    assert load_settings({"BOT_TOKEN": "t"}).demo_mode is True
