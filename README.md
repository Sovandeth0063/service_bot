# SangkatConnect (ជំនួយការឃុំ-សង្កាត់) — demo bot

A Telegram bot for one commune group. Older residents get emergency numbers, hospitals, the commune hall, document guides and the latest news in **one or two taps**, in Khmer, with no typing. Clerks post news as **text + picture + voice** from their phone (or type rough notes and let the AI helper make all three); it goes to the commune group and into the bot's news button.

Demo commune: **Sangkat Tonle Basak (`120101`), Khan Chamkar Mon, Phnom Penh.**

- Product & design: [`docs/superpowers/specs/2026-11-21-sangkatconnect-demo-design.md`](docs/superpowers/specs/2026-11-21-sangkatconnect-demo-design.md)
- Build plan (tick-box tasks): [`docs/superpowers/plans/2026-11-21-sangkatconnect-demo.md`](docs/superpowers/plans/2026-11-21-sangkatconnect-demo.md)
- **Pending manual checks:** [`docs/superpowers/plans/NOTES.md`](docs/superpowers/plans/NOTES.md)
- Filming the demo video: [`docs/demo-runsheet.md`](docs/demo-runsheet.md)
- Running the bot and managing clerks: [`docs/superadmin-guide.md`](docs/superadmin-guide.md)
- How clerks post news: [`docs/clerk-guide.md`](docs/clerk-guide.md)
- How residents use the bot: [`docs/resident-guide.md`](docs/resident-guide.md)
- Data sources & what is verified: [`data/README.md`](data/README.md)

> **Setting it up for a demo?** Follow the step-by-step [super-admin guide](docs/superadmin-guide.md): install, settings, first run, adding clerks, and a 10-minute demo walkthrough. No coding needed.

## You need

- Windows with **Python 3.12+** (`py -3 --version`), and Edge or Chrome (for AI-made flyers)
- The project in a **short path** such as `C:\service_bot` (a long path breaks installing the Anthropic SDK on Windows without long-path support)
- A bot token from **@BotFather** (`/newbot`)
- A Telegram **group** standing in for the commune group, with the bot added as **admin** (post + pin rights)
- Telegram accounts with **usernames** (Settings → Username): a **super-admin** (you), a **clerk**, and a **resident** (you can play the resident yourself)
- Optional: a Claude API key for the AI helper

## Set up (≈ 10 minutes)

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev,ai]"
copy .env.example .env        # then edit .env: BOT_TOKEN, ADMIN_USERNAMES (your username, no @), optional ANTHROPIC_API_KEY
.venv\Scripts\python -m sangkat_bot.seed   # builds data\sangkat.db from data\seed + DataEF
.venv\Scripts\python -m sangkat_bot        # starts the bot (Ctrl+C to stop)
```

The bot uses long polling, so it runs on a laptop with no public URL. **Only one computer may run a given bot token at a time** (a second one gets "Conflict: terminated by other getUpdates"). Each computer has its own `data\sangkat.db`, so linked groups and clerks are set up again on a new machine. Re-running `seed` is safe: it reloads the reference data and **keeps** users, the bound group, and news posted by clerks.

## First run

1. Add the bot to the commune group and **make it an admin first** (post + pin rights). Doing this can turn a small group into a "supergroup" with a new id, so bind afterwards. Then the clerk (as a normal admin, not "remain anonymous") sends **`/bind 120101`** (or `/bind@kh_svc_desk_x7_bot 120101`). The bot confirms, posts the welcome message with a **📱 សួរជំនួយការ** button, and pins it.
2. The resident taps that button → the bot opens already set to Tonle Basak, with five big buttons. Residents need no username and no setup. New members are greeted in the group with the same button, and any member can tap **Menu → /help** in the group to get it. The five buttons themselves only exist in the private chat, because Telegram doesn't show reply keyboards to group members.
3. The clerk opens the bot privately and taps **📝 ផ្សាយដំណឹង** (or `/announce`). **With the AI helper on**, they just type the news, messy is fine; the bot makes clean text + a flyer + a Khmer voice note (+ a 📍 map button when there's a place), and **✏️ កែ** under the preview remakes them with a correction (see below). Without it: send text → a picture → a voice note (each can be skipped). Then → preview → tap **✅ the sangkat** it's for (a clerk sees only their own), or **✅ all sangkats** (super-admins). Each sangkat gets its own copy (heading names that sangkat) in its 📢 feed and, if its group is linked with `/bind <code>`, in that group; the bot lists any groups not linked yet. `/cancel` stops at any step; `/delete_last` removes every copy of the clerk's latest post from the groups and the feeds.
4. **Guides:** residents tap **Menu → /help** in the bot for a step-by-step Khmer guide to every button. In the group, the clerk sends **`/guide`** to post and pin a short "how to start" message with the 📱 button. Guide wording lives under `guide` in `data/seed/bot_copy_kh.json`.

## Who can post: super-admins and clerks

- **Super-admins** are the usernames in `ADMIN_USERNAMES` in `.env`. They post to any sangkat or to all of them, and manage clerks. (`ADMIN_USER_IDS` still works too.)
- **Clerks** post only for their own sangkat. A super-admin manages them in the private chat with the bot (full guide: [`docs/superadmin-guide.md`](docs/superadmin-guide.md)):

| Command | What it does |
| :--- | :--- |
| `/addclerk @sok_dara 120101` | Makes @sok_dara the clerk for that sangkat (or moves them to it) |
| `/removeclerk @sok_dara` | Takes the clerk role away, effective immediately |
| `/clerks` | Lists everyone who can post: ✅ linked, ⏳ hasn't opened the bot yet |

The new clerk opens the bot and presses **Start**. The bot then **locks the role to their Telegram account**: if they later change their username, they keep the role, and someone who takes the old username gets nothing. A clerk sees one ✅ button (their sangkat), and can `/bind` / `/guide` only their own sangkat's group. Every change is in `audit_logs`. Design: `docs/superpowers/specs/2026-11-21-clerk-roles-design.md`.

## AI helper for clerks (optional)

Put a Claude API key in `.env` as `ANTHROPIC_API_KEY=...`, install the extra once, and restart the bot:

```powershell
.venv\Scripts\python -m pip install -e ".[ai]"
```

The clerk's notes go to Claude (`claude-opus-5-5`), which returns JSON: the post text, a script to read aloud (numbers in words), and flyer fields. The bot then draws the flyer with Chrome (`sangkat_bot/media.py`, same template as below) and makes the voice with edge-tts. It costs about a cent per post and takes about half a minute.

- Claude is told to use only facts in the notes and never guess. The preview asks the clerk to check date, time and place.
- **Times are written as a range** ("៨:០០ – ១១:០០ ព្រឹក") when the notes give both ends. If only a start time is given, Claude doesn't invent the end; the preview shows its question ("❓ … ចប់ម៉ោងប៉ុន្មាន?") and the clerk answers with ✏️ កែ.
- **📍 Map button** under the post (group, preview and 📢 feed): a map link pasted in the notes wins; "at the sangkat hall" opens *each* sangkat's own hall pin (`commune_configs.google_maps_url`); another named place gets a Google Maps search. Stored per copy in `announcements.location_url`.
- If anything fails (no internet, no Chrome, Claude down), the clerk is told and continues by hand with their notes kept.
- No key: the bot posts by hand exactly as before.
- Design: `docs/superpowers/specs/2026-11-21-ai-news-writer-design.md`.

## Demo news: text + picture + voice

Every demo news item has a flyer and a Khmer voice note in `data/demo_media/<news>/`, listed in `data/seed/demo_announcements.csv` (`photo_path`, `voice_path`). The bot uploads each file the first time someone taps 📢 and reuses Telegram's copy after that.

To make a new one (needs `pip install -e ".[media]"`, Chrome, internet):

```powershell
.venv\Scripts\python scripts/make_flyer.py data/demo_media/<news>/flyer.json        # flyer.png from a small JSON spec
.venv\Scripts\python scripts/make_voice.py data/demo_media/<news>/speech_kh.txt data/demo_media/<news>/voice.ogg
.venv\Scripts\python scripts/publish_news.py --text-file news.txt --photo flyer.png --voice voice.ogg   # post as the clerk
```

Write `speech_kh.txt` the way it should be *said* (numbers and times in words). The voice is Microsoft's free Khmer neural voice via edge-tts; the text is sent to Microsoft to make the audio.

## Tests

```powershell
.venv\Scripts\python -m pytest -q
```

Tests run fully offline: `tests/tg.py` is a fake Telegram that records what the bot would send, so the resident and clerk flows are tested through the real dispatcher.

## How it's built

| Path | What it does |
| :--- | :--- |
| `sangkat_bot/app.py` | Wires settings, DB, Khmer copy and routers; global error handler |
| `sangkat_bot/handlers/` | `resident.py` (buttons, picker, typed text), `admin.py` (posting flow), `group.py` (`/bind`) |
| `sangkat_bot/db.py`, `schema.sql` | Every SQL query (SQLite today; one file to change for PostgreSQL) |
| `sangkat_bot/seed.py` | Loads all 1,661 DataEF communes + `data/seed/*.csv` |
| `sangkat_bot/formatting.py`, `posts.py` | Card text; how a post becomes photo + caption + voice reply |
| `sangkat_bot/clerks.py`, `handlers/manage.py` | Who may post (super-admins, clerks by @username) and `/addclerk` `/removeclerk` `/clerks` |
| `sangkat_bot/news_ai.py`, `media.py` | AI helper: clerk notes → Claude JSON → flyer (Chrome) + voice (edge-tts) |
| `sangkat_bot/keywords.py`, `khmer/` | Typed-Khmer matching with a normalizer copied from KAI_AI |
| `data/seed/bot_copy_kh.json` | **All** Khmer text the bot shows — edit wording here |

Adding a commune is data, not code: add its rows to `data/seed/commune_configs.csv` and `local_contacts.csv`, re-run `seed`, and `/bind` its group.

## Rules

- **Never modify `E:\KAI_AI`.** The Khmer normalizer in `sangkat_bot/khmer/` is a copy; re-copy it rather than editing.
- Never show a phone number that isn't in the data. Missing numbers display as "កំពុងផ្ទៀងផ្ទាត់"; `DEMO_MODE=true` adds a demo-data notice to every card.
- Logs never contain what people type, or the bot token. `.env` is git-ignored.
