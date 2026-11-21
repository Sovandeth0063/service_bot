# AI news writer for clerks (short design)

Approved in chat on 2026-11-21.

## Why
Posting news today means the clerk sends text, then a picture, then a voice note. Making a flyer
and recording a voice note is too much work for a sangkat clerk, so most posts would end up
text-only, and text-only fails the residents this bot is for (older people, low literacy).

## What
The clerk taps 📝 and sends the news however it comes: messy, in any order, mixed Khmer and English.
The bot answers "⏳ preparing…", then shows the finished post in all three forms:

- **text:** clean, short Khmer announcement;
- **picture:** a 1080×1080 flyer (the existing template from `scripts/make_flyer.py`);
- **voice:** a Khmer voice note (edge-tts, same as `scripts/make_voice.py`), with numbers said in words.

Below the preview are the existing sangkat buttons plus **✏️ កែ** (fix). Fix asks "what should change?",
and the clerk types, for example, "the time is 7 PM, not 6". All three forms are then made again from
the notes plus every correction so far. ❌ cancels.

- A photo with a caption: the caption is the notes. The bot writes the text and voice and keeps the
  clerk's own photo.
- A photo with no caption, or a voice note: today's manual flow, unchanged (Khmer speech-to-text is
  out of scope).
- If anything fails (no internet, Claude down, Chrome missing), the clerk is told, and the flow drops
  to today's manual steps with the notes kept as the text.
- No `ANTHROPIC_API_KEY` in `.env` means the AI writer is off and the bot behaves exactly as before.

## Rules
- **Never invent facts.** Claude may use only facts in the notes and corrections, with no guessed
  dates, times, fees or phone numbers. The preview tells the clerk to check date, time and place.
  The clerk's ✅ is the safety gate.
- **The AI output never names a sangkat.** Each copy's header already does, and one post can go to
  all five sangkats. The flyer's top label is the generic "📢 ដំណឹងសង្កាត់".
- **The demo label is set by code, not by Claude:** the flyer tag and footer come from `DEMO_MODE`.
- **Logs never contain the notes.** Only the event and the error type are logged. The notes go to
  Anthropic (writing) and Microsoft (voice), which is fine for public announcement text. This is
  stated in the clerk guide.

## Approaches considered
1. **Claude structured output → existing flyer template + edge-tts (chosen).** One API call returns
   JSON (text, speech script, flyer fields). The flyer layout stays fixed and readable, and the cost
   is about a cent per post.
2. Claude writes the whole flyer HTML. More varied looks, but layouts break with long Khmer words and
   are harder to keep large and legible for older eyes.
3. An image-generation model for the flyer. Khmer text in generated images is unreliable, and it is
   a second vendor.

## How (builder notes)
- `sangkat_bot/media.py`: flyer HTML and rendering, plus voice synthesis, moved out of the scripts.
  The scripts become thin wrappers.
- `sangkat_bot/news_ai.py`:
  - `write_news(client, notes, corrections) -> NewsDraft`;
  - `NewsMaker.make(...) -> MadeNews` (paths of the generated files);
  - `make_news_maker(settings)`, which returns `None` when there is no key or the SDK is missing.
- The model call:
  - model `claude-opus-5-5` through `client.beta.messages.create`;
  - `output_config` with effort `medium` and a JSON schema;
  - server-side refusal fallback: `fallbacks="default"`, beta `server-side-fallback-2026-07-01`;
  - a refusal or a `max_tokens` stop is treated as a failure.
- Generated files go to `data/generated/<id>/` (git-ignored). Each is uploaded once, in the preview.
  Telegram's file ids are then reused for publishing.
- `jiter` is pinned below 0.19, because Windows App Control blocks that build's DLL on the demo laptop.

## Tasks
- [x] Design approved
- [x] `media.py` (flyer for 1–3 facts, voice) and scripts rewired
- [x] `news_ai.py` (prompt, schema, parse, maker) with offline tests
- [x] Clerk flow: AI path, ✏️ fix loop, fallback to manual, own photo kept
- [x] Copy, `.env.example`, README and clerk guide
- [x] Live check with a real key (2026-11-21: vaccination notes → correct text, flyer, voice in ~28 s)
