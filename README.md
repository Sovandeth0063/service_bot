# SangkatConnect (ជំនួយការឃុំ-សង្កាត់) — demo bot

A Telegram bot for one commune group. Older residents get emergency numbers, hospitals, the commune hall, document guides and the latest news in **one or two taps**, in Khmer, with no typing. Clerks post news as **text + picture + voice** from their phone; it goes to the commune group and into the bot's news button.

Demo commune: **Sangkat Tonle Basak (`120101`), Khan Chamkar Mon, Phnom Penh.**

- Product & design: [`docs/superpowers/specs/2026-11-21-sangkatconnect-demo-design.md`](docs/superpowers/specs/2026-11-21-sangkatconnect-demo-design.md)
- Build plan (tick-box tasks): [`docs/superpowers/plans/2026-11-21-sangkatconnect-demo.md`](docs/superpowers/plans/2026-11-21-sangkatconnect-demo.md)
- **Pending manual checks:** [`docs/superpowers/plans/NOTES.md`](docs/superpowers/plans/NOTES.md)
- Filming the demo video: [`docs/demo-runsheet.md`](docs/demo-runsheet.md)
- Data sources & what is verified: [`data/README.md`](data/README.md)

## You need

- Windows with **Python 3.12+** (`py -3 --version`)
- A bot token from **@BotFather** (`/newbot`)
- A Telegram **group** standing in for the commune group, with the bot added as **admin** (post + pin rights)
- Two Telegram accounts: a **clerk** and a **resident**. Get the clerk's numeric id from **@userinfobot**.

## Set up (≈ 10 minutes)

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env        # then edit .env: BOT_TOKEN and ADMIN_USER_IDS (the clerk's id)
.venv\Scripts\python -m sangkat_bot.seed   # builds data\sangkat.db from data\seed + DataEF
.venv\Scripts\python -m sangkat_bot        # starts the bot (Ctrl+C to stop)
```

The bot uses long polling, so it runs on a laptop with no public URL. Re-running `seed` is safe: it reloads the reference data and **keeps** users, the bound group, and news posted by clerks.

## First run

1. Add the bot to the commune group and **make it an admin first** (post + pin rights). Doing this can turn a small group into a "supergroup" with a new id, so bind afterwards. Then the clerk (as a normal admin, not "remain anonymous") sends **`/bind 120101`** (or `/bind@kh_svc_desk_x7_bot 120101`). The bot confirms, posts the welcome message with a **📱 សួរជំនួយការ** button, and pins it.
2. The resident taps that button → the bot opens already set to Tonle Basak, with five big buttons.
3. The clerk opens the bot privately and taps **📝 ផ្សាយដំណឹង** (or `/announce`): send text → a picture → a voice note (each can be skipped) → preview → **✅ ផ្សាយ**. `/cancel` stops at any step; `/delete_last` removes the clerk's latest post from the group and the feed.
4. **Guides:** residents tap **Menu → /help** in the bot for a step-by-step Khmer guide to every button. In the group, the clerk sends **`/guide`** to post and pin a short "how to start" message with the 📱 button. Guide wording lives under `guide` in `data/seed/bot_copy_kh.json`.

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
| `sangkat_bot/keywords.py`, `khmer/` | Typed-Khmer matching with a normalizer copied from KAI_AI |
| `data/seed/bot_copy_kh.json` | **All** Khmer text the bot shows — edit wording here |

Adding a commune is data, not code: add its rows to `data/seed/commune_configs.csv` and `local_contacts.csv`, re-run `seed`, and `/bind` its group.

## Rules

- **Never modify `E:\KAI_AI`.** The Khmer normalizer in `sangkat_bot/khmer/` is a copy; re-copy it rather than editing.
- Never show a phone number that isn't in the data. Missing numbers display as "កំពុងផ្ទៀងផ្ទាត់"; `DEMO_MODE=true` adds a demo-data notice to every card.
- Logs never contain what people type, or the bot token. `.env` is git-ignored.
