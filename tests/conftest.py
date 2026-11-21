from pathlib import Path

import pytest

SEED = Path("data/seed")
DATAEF = Path("data/raw/dataef")


@pytest.fixture(scope="session")
def keywords():
    from sangkat_bot.keywords import load_keywords

    return load_keywords(SEED / "keywords_kh.csv")
