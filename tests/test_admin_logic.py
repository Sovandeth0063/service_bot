from sangkat_bot.db import get_commune, set_group
from sangkat_bot.handlers.admin import publish_target


def test_publish_target_unbound(conn):
    assert publish_target(get_commune(conn, "120101")) is None


def test_publish_target_bound(conn):
    set_group(conn, "120101", -100500)
    assert publish_target(get_commune(conn, "120101")) == -100500


def test_publish_target_inactive_commune(conn):
    assert publish_target(get_commune(conn, "010201")) is None


def test_publish_target_missing():
    assert publish_target(None) is None
