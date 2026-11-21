"""AI news writer: a clerk's messy notes → clean Khmer text, a flyer and a voice note.

One Claude call returns JSON (announcement text, a script to read aloud, flyer fields);
the flyer and the voice are then made locally by sangkat_bot.media. Off unless
ANTHROPIC_API_KEY is set. The notes are never logged.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from urllib.parse import quote_plus
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from sangkat_bot.config import Settings
from sangkat_bot.media import make_voice_note, render_flyer

log = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
MAX_FACTS = 3

SYSTEM_PROMPT = """\
You prepare news for a Cambodian sangkat (commune) office. It is posted on Telegram to residents, \
many of whom are older people who read little or not at all, so every post goes out as short text, \
a picture flyer and a voice note.

The clerk gives you rough notes: maybe messy, out of order, mixed Khmer and English, with typos. \
Turn them into one clear announcement, written in Khmer.

Facts:
- Use only facts that are in the notes or the corrections. Never invent or guess a date, time, \
place, fee, phone number, name or requirement. If something is not given, leave it out.
- Corrections come after the notes and override them.
- Times: when the notes give a start and an end time, always write both as a range, \
"start – end" (for example "៨:០០ – ១១:០០ ព្រឹក"), in the text, the speech and the flyer. If an event \
or service has a start time but no end time, never invent the end time: leave it out and ask for it in ask_kh.
- Do not name a specific sangkat or commune as the sender. The post header adds that, and one post \
may go to several sangkats. Places that are part of the news (for example "at the sangkat hall") are fine.

text_kh: the written post. Plain, polite, short sentences, most important facts first (what, when, \
where, what to bring). At most 600 characters. Khmer digits are fine. No markdown or HTML. You may \
start key lines with one emoji such as 📅 🕗 📍. Never put links in the text: the bot adds a map \
button itself.

speech_kh: what an announcer would read aloud, in Khmer, about 20 to 45 seconds long. Write every \
number, date and time as Khmer words (for example "ម៉ោងប្រាំមួយល្ងាច", not "៦:០០"). Begin with \
"ដំណឹងពីសង្កាត់។" and repeat the single most important fact once at the end.

flyer: a big, simple picture.
- icon: one emoji that shows the topic.
- title: at most 22 characters.
- subtitle: at most 30 characters, or "".
- facts: 1 to 3 key facts, each with an emoji icon, a label of at most 10 characters and a value \
of at most 14 characters.
- note: one short line (at most 60 characters) such as what to bring, or "".

Place (the bot turns this into a 📍 map button under the post):
- at_sangkat_hall: true if it happens at the sangkat hall or sangkat office.
- place_link: a map link (Google Maps, goo.gl) copied exactly from the notes, or "".
- place_search: if it happens at another specific, named place (a pagoda, school, market, health \
centre), a Google Maps search for it that includes "Phnom Penh", for example \
"Wat Lanka, Phnom Penh"; otherwise "". Never guess a place that is not named.

ask_kh: one short, polite Khmer question to the clerk about the most important missing fact, above \
all a missing end time (for example "ម៉ោងប៉ុន្មានចប់?"), or "" when nothing important is missing.
"""

_FACT = {
    "type": "object",
    "properties": {"icon": {"type": "string"}, "label": {"type": "string"}, "value": {"type": "string"}},
    "required": ["icon", "label", "value"],
    "additionalProperties": False,
}
SCHEMA = {
    "type": "object",
    "properties": {
        "text_kh": {"type": "string"},
        "speech_kh": {"type": "string"},
        "flyer": {
            "type": "object",
            "properties": {
                "icon": {"type": "string"},
                "title": {"type": "string"},
                "subtitle": {"type": "string"},
                "facts": {"type": "array", "items": _FACT},
                "note": {"type": "string"},
            },
            "required": ["icon", "title", "subtitle", "facts", "note"],
            "additionalProperties": False,
        },
        "at_sangkat_hall": {"type": "boolean"},
        "place_link": {"type": "string"},
        "place_search": {"type": "string"},
        "ask_kh": {"type": "string"},
    },
    "required": ["text_kh", "speech_kh", "flyer", "at_sangkat_hall", "place_link", "place_search", "ask_kh"],
    "additionalProperties": False,
}


class NewsAIError(Exception):
    """Claude declined, was cut off, or returned something unusable."""


@dataclass(frozen=True)
class NewsDraft:
    text_kh: str
    speech_kh: str
    flyer: dict  # icon, title, subtitle | None, facts (≤3), note | None
    at_hall: bool = False
    place_link: str | None = None
    place_search: str | None = None
    ask_kh: str | None = None


@dataclass(frozen=True)
class MadeNews:
    text_kh: str
    photo_path: Path | None  # None when the clerk sent their own photo
    voice_path: Path
    location: str | None = None  # "hall" (each sangkat's own hall pin) or a map URL
    ask_kh: str | None = None  # a question for the clerk, e.g. the missing end time


def map_location(draft: NewsDraft) -> str | None:
    """A pasted map link wins; then the sangkat hall; then a search for a named place."""
    link = draft.place_link or ""
    if link.startswith("https://") and any(host in link for host in ("google.", "goo.gl")):
        return link
    if draft.at_hall:
        return "hall"
    if draft.place_search:
        return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(draft.place_search)
    return None


def parse_draft(raw: str) -> NewsDraft:
    try:
        data = json.loads(raw)
        text, speech, flyer = data["text_kh"].strip(), data["speech_kh"].strip(), data["flyer"]
        facts = [
            {key: str(fact[key]).strip() for key in ("icon", "label", "value")}
            for fact in flyer["facts"][:MAX_FACTS]
        ]
        clean = {
            "icon": flyer["icon"].strip() or "📢",
            "title": flyer["title"].strip(),
            "subtitle": flyer["subtitle"].strip() or None,
            "facts": facts,
            "note": flyer["note"].strip() or None,
        }
        extras = {
            "at_hall": bool(data.get("at_sangkat_hall")),
            "place_link": (data.get("place_link") or "").strip() or None,
            "place_search": (data.get("place_search") or "").strip() or None,
            "ask_kh": (data.get("ask_kh") or "").strip() or None,
        }
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise NewsAIError(f"unusable output: {type(error).__name__}") from error
    if not (text and speech and clean["title"]):
        raise NewsAIError("empty text, speech or title")
    return NewsDraft(text, speech, clean, **extras)


def _user_message(notes: str, corrections: list[str]) -> str:
    parts = [f"<notes>\n{notes}\n</notes>"]
    parts += [f"<correction>\n{c}\n</correction>" for c in corrections]
    return "\n".join(parts)


async def write_news(client, notes: str, corrections: list[str]) -> NewsDraft:
    """Ask Claude for the announcement. `client` is an anthropic.AsyncAnthropic."""
    response = await client.beta.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_message(notes, corrections)}],
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # a safety decline is retried on Anthropic's recommended model
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        raise NewsAIError(f"stopped: {response.stop_reason}")
    text = next((block.text for block in response.content if block.type == "text"), None)
    if text is None:
        raise NewsAIError("no text in the response")
    return parse_draft(text)


def flyer_spec(draft: NewsDraft, demo_mode: bool) -> dict:
    """The flyer's fixed parts come from code: a generic label (one post can go to every sangkat) and the demo tag."""
    return {
        **draft.flyer,
        "who": "📢 ដំណឹងសង្កាត់",
        "tag": "សាកល្បង" if demo_mode else "ដំណឹង",
        "footer": "ទិន្នន័យសាកល្បងសម្រាប់ការបង្ហាញ" if demo_mode else "",
    }


class NewsMaker:
    def __init__(
        self,
        client,
        out_dir: Path,
        demo_mode: bool,
        render: Callable[[dict, Path], object] = render_flyer,
        speak: Callable[[str, Path], Awaitable[object]] = make_voice_note,
    ) -> None:
        self.client, self.out_dir, self.demo_mode = client, out_dir, demo_mode
        self.render, self.speak = render, speak

    async def make(self, notes: str, corrections: list[str], want_flyer: bool) -> MadeNews:
        draft = await write_news(self.client, notes, corrections)
        folder = self.out_dir / uuid.uuid4().hex
        folder.mkdir(parents=True)
        photo, voice = folder / "flyer.png", folder / "voice.ogg"
        jobs = [self.speak(draft.speech_kh, voice)]
        if want_flyer:
            jobs.append(asyncio.to_thread(self.render, flyer_spec(draft, self.demo_mode), photo))
        await asyncio.gather(*jobs)
        return MadeNews(draft.text_kh, photo if want_flyer else None, voice, map_location(draft), draft.ask_kh)


def make_news_maker(settings: Settings) -> NewsMaker | None:
    """The AI writer, or None (manual posting only) when there is no key or the SDK is missing."""
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import AsyncAnthropic
    except ImportError as error:
        log.warning("event=news_ai_off error=%s", type(error).__name__)
        return None
    client = AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=120.0, max_retries=1)
    return NewsMaker(client, settings.db_path.parent / "generated", settings.demo_mode)
