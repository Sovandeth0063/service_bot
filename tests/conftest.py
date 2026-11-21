from pathlib import Path

import pytest

SEED = Path("data/seed")
DATAEF = Path("data/raw/dataef")


@pytest.fixture(scope="session")
def keywords():
    from sangkat_bot.keywords import load_keywords

    return load_keywords(SEED / "keywords_kh.csv")


@pytest.fixture
def conn(tmp_path):
    from sangkat_bot.db import connect
    from sangkat_bot.seed import run_seed

    connection = connect(tmp_path / "t.db")
    run_seed(connection, DATAEF, SEED)
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def copy_tb():
    from sangkat_bot.copy import Copy, load_copy

    return Copy(load_copy(SEED / "bot_copy_kh.json"), "sangkat", "ទន្លេបាសាក់")
