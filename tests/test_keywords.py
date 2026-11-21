import pytest

from sangkat_bot.keywords import INTENTS, match_intent, normalize_text


@pytest.mark.parametrize(
    "text,intent",
    [
        ("ផ្ទះ​ខ្ញុំ​ឆេះ", "emergency"),
        ("ខ្ញុំឈឺ ចង់ទៅពេទ្យ", "health"),
        ("សំបុត្រ​កំណើត", "services"),
        ("ឣត្តសញ្ញាណប័ណ្ណ", "services"),  # deprecated ឣ normalizes to អ
        ("119", "emergency"),
        ("ពេទ្យ ភ្លើង", "emergency"),  # emergency wins: CSV order is priority
        ("សាលាសង្កាត់បើកម៉ោងប៉ុន្មាន", "location"),
    ],
)
def test_match_intent(text, intent, keywords):
    assert match_intent(text, keywords) == intent


@pytest.mark.parametrize("text", ["hello", "", "   ", "👍", "​"])
def test_blank_and_emoji_do_not_match(text, keywords):
    assert match_intent(text, keywords) is None


def test_every_keyword_intent_is_known(keywords):
    assert {intent for intent, _ in keywords} <= set(INTENTS)


def test_normalize_text_collapses_whitespace():
    assert normalize_text("  ពេទ្យ \n  ឈឺ ") == "ពេទ្យ ឈឺ"
