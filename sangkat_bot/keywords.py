"""Map typed Khmer text to a menu intent with a small keyword list."""

from __future__ import annotations

import csv
from pathlib import Path

from sangkat_bot.khmer import normalize

INTENTS = ("emergency", "health", "announcements", "services", "location")


def normalize_text(text: str) -> str:
    """Normalize Khmer (zero-width chars, deprecated letters, vowel order) and collapse whitespace."""
    return " ".join(normalize(text).text.split())


def load_keywords(path: Path) -> list[tuple[str, str]]:
    """Read (intent, keyword) pairs in file order; file order is match priority."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        pairs = [(row["intent"], normalize_text(row["keyword"])) for row in csv.DictReader(file)]
    return [(intent, keyword) for intent, keyword in pairs if keyword]


def match_intent(text: str, keywords: list[tuple[str, str]]) -> str | None:
    """Return the intent of the first keyword found in the text, or None."""
    normalized = normalize_text(text)
    if not normalized:
        return None
    for intent, keyword in keywords:
        if keyword in normalized:
            return intent
    return None
