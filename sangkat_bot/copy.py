"""User-facing Khmer text, loaded from data/seed/bot_copy_kh.json."""

from __future__ import annotations

import json
from pathlib import Path

_TYPE_KH = {"sangkat": "សង្កាត់", "khum": "ឃុំ"}


def load_copy(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def commune_type_kh(commune_type: str | None) -> str:
    """Khmer word for the commune level; unknown types read as rural "ឃុំ"."""
    return _TYPE_KH.get(commune_type or "", "ឃុំ")


class Copy:
    """Copy strings with {commune_type_kh} and {commune_kh} filled for one commune."""

    def __init__(self, data: dict, commune_type: str | None, commune_kh: str) -> None:
        self._data = data
        self._fill = {"commune_type_kh": commune_type_kh(commune_type), "commune_kh": commune_kh}

    def _render(self, template: str) -> str:
        for name, value in self._fill.items():
            template = template.replace("{" + name + "}", value)
        return template

    def _lookup(self, key: str) -> object:
        value: object = self._data
        for part in key.split("."):
            value = value[part]  # type: ignore[index]
        return value

    def t(self, key: str) -> str:
        """Look up a dotted key such as "admin.publish"."""
        return self._render(str(self._lookup(key)))

    def lines(self, key: str) -> list[str]:
        """Look up a list of strings, such as "guide.tips"."""
        return [self._render(str(line)) for line in self._lookup(key)]  # type: ignore[union-attr]

    def button(self, intent: str) -> str:
        return self._render(self._data["buttons"][intent])

    def button_intent(self, text: str) -> str | None:
        """Map an exact keyboard label back to its intent."""
        for intent in self._data["buttons"]:
            if self.button(intent) == text:
                return intent
        return None

    @property
    def keyboard_layout(self) -> list[list[str]]:
        return self._data["keyboard_layout"]
