"""The AI news writer: one Claude call turns a clerk's messy notes into text, a speech script and flyer fields."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sangkat_bot.config import load_settings
from sangkat_bot.media import render_html
from sangkat_bot.news_ai import (
    MODEL,
    NewsAIError,
    NewsDraft,
    NewsMaker,
    flyer_spec,
    make_news_maker,
    parse_draft,
    write_news,
)

TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"
DRAFT = {
    "text_kh": "📅 ចាប់ពីថ្ងៃទី១ ខែធ្នូ រថយន្តប្រមូលសំរាមមកដល់ភូមិ ១ ដល់ ៨ ម៉ោង ៦:០០ ល្ងាច។",
    "speech_kh": "ដំណឹងពីសង្កាត់។ ចាប់ពីថ្ងៃទីមួយ ខែធ្នូ រថយន្តប្រមូលសំរាម នឹងមកដល់ នៅម៉ោងប្រាំមួយល្ងាច។",
    "flyer": {
        "icon": "🚛",
        "title": "រថយន្តប្រមូលសំរាម",
        "subtitle": "",
        "facts": [
            {"icon": "📅", "label": "ចាប់ពី", "value": "១ ធ្នូ"},
            {"icon": "🏘️", "label": "ភូមិ", "value": "១ – ៨"},
            {"icon": "🕕", "label": "ម៉ោង", "value": "៦:០០ ល្ងាច"},
            {"icon": "❓", "label": "extra", "value": "dropped"},
        ],
        "note": "",
    },
    "at_sangkat_hall": False,
    "place_link": "",
    "place_search": "",
    "ask_kh": "",
}


class FakeMessages:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def fake_client(payload=DRAFT, stop_reason="end_turn"):
    response = SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=json.dumps(payload, ensure_ascii=False))],
    )
    return SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages(response)))


def test_parse_draft_keeps_at_most_three_facts_and_blanks_become_none():
    draft = parse_draft(json.dumps(DRAFT))
    assert draft.text_kh.startswith("📅 ចាប់ពី")
    assert [f["value"] for f in draft.flyer["facts"]] == ["១ ធ្នូ", "១ – ៨", "៦:០០ ល្ងាច"]
    assert draft.flyer["subtitle"] is None and draft.flyer["note"] is None


@pytest.mark.parametrize("bad", ["not json", json.dumps({**DRAFT, "text_kh": "  "}), json.dumps({"text_kh": "x"})])
def test_parse_draft_rejects_broken_or_empty_output(bad):
    with pytest.raises(NewsAIError):
        parse_draft(bad)


async def test_write_news_sends_notes_and_corrections_with_schema_and_fallback():
    client = fake_client()
    draft = await write_news(client, "garbage truck dec 1, 6pm, village 1-8", ["the time is 7 PM"])
    assert isinstance(draft, NewsDraft) and draft.flyer["icon"] == "🚛"
    (call,) = client.beta.messages.calls
    assert call["model"] == MODEL == "claude-opus-5-5"
    assert call["fallbacks"] == "default" and call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert call["output_config"]["effort"] == "medium"
    user = call["messages"][0]["content"]
    assert "garbage truck dec 1" in user and "the time is 7 PM" in user
    assert "invent" in call["system"].lower()


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
async def test_write_news_treats_refusal_and_cutoff_as_failure(stop):
    with pytest.raises(NewsAIError):
        await write_news(fake_client(stop_reason=stop), "notes", [])


def test_flyer_spec_adds_generic_label_and_demo_tag_from_code():
    spec = flyer_spec(parse_draft(json.dumps(DRAFT)), demo_mode=True)
    assert spec["who"] == "📢 ដំណឹងសង្កាត់" and spec["tag"] == "សាកល្បង" and spec["footer"]
    live = flyer_spec(parse_draft(json.dumps(DRAFT)), demo_mode=False)
    assert live["tag"] == "ដំណឹង" and live["footer"] == ""


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_flyer_html_lays_out_any_number_of_facts(count):
    spec = {"who": "w", "tag": "t", "icon": "🚛", "title": "T", "footer": "", "facts": [
        {"icon": "📅", "label": f"l{i}", "value": f"v{i}"} for i in range(count)
    ]}
    html = render_html(spec)
    assert html.count('class="fact"') == count
    assert ("repeat(%d, 1fr)" % count in html) if count else 'class="facts"' not in html


def test_maker_is_off_without_a_key():
    assert make_news_maker(load_settings({"BOT_TOKEN": TOKEN})) is None


async def test_maker_writes_flyer_and_voice_files(tmp_path):
    made_flyers, spoken = [], []

    def render(spec, out: Path):
        made_flyers.append(spec)
        out.write_bytes(b"png")

    async def speak(text, out: Path):
        spoken.append(text)
        out.write_bytes(b"ogg")

    maker = NewsMaker(fake_client(), tmp_path, demo_mode=True, render=render, speak=speak)
    made = await maker.make("notes", [], want_flyer=True)
    assert made.text_kh == DRAFT["text_kh"]
    assert made.photo_path.read_bytes() == b"png" and made.voice_path.read_bytes() == b"ogg"
    assert made.photo_path.parent.parent == tmp_path
    assert spoken == [DRAFT["speech_kh"]] and made_flyers[0]["title"] == "រថយន្តប្រមូលសំរាម"

    kept_photo = await maker.make("notes", [], want_flyer=False)
    assert kept_photo.photo_path is None and len(made_flyers) == 1


def made_location(tmp_path, **fields):
    async def speak(text, out):
        out.write_bytes(b"ogg")

    maker = NewsMaker(fake_client({**DRAFT, **fields}), tmp_path, demo_mode=True, render=lambda s, o: o.write_bytes(b"p"), speak=speak)
    return maker


@pytest.mark.parametrize("fields, expected", [
    ({}, None),
    ({"at_sangkat_hall": True}, "hall"),
    ({"place_search": "Wat Tonle Bassac, Phnom Penh"}, "https://www.google.com/maps/search/?api=1&query=Wat+Tonle+Bassac%2C+Phnom+Penh"),
    ({"at_sangkat_hall": True, "place_link": "https://maps.app.goo.gl/AbC123"}, "https://maps.app.goo.gl/AbC123"),
    ({"place_link": "not a link", "place_search": ""}, None),
])
async def test_maker_picks_the_map_location(tmp_path, fields, expected):
    made = await made_location(tmp_path, **fields).make("notes", [], want_flyer=False)
    assert made.location == expected


async def test_maker_passes_the_question_about_a_missing_end_time(tmp_path):
    made = await made_location(tmp_path, ask_kh="  ម៉ោងប៉ុន្មានចប់?  ").make("notes", [], want_flyer=False)
    assert made.ask_kh == "ម៉ោងប៉ុន្មានចប់?"
    none = await made_location(tmp_path).make("notes", [], want_flyer=False)
    assert none.ask_kh is None


def test_prompt_asks_for_time_ranges_and_never_invents_an_end_time():
    from sangkat_bot.news_ai import SCHEMA, SYSTEM_PROMPT

    assert "end time" in SYSTEM_PROMPT and "ask_kh" in SYSTEM_PROMPT and "– " in SYSTEM_PROMPT
    assert {"at_sangkat_hall", "place_link", "place_search", "ask_kh"} <= set(SCHEMA["required"])
