# SangkatConnect Demo MVP — Design

| | |
| :--- | :--- |
| **Date** | 2026-11-21 |
| **Status** | Draft — awaiting approval |
| **Build budget** | 5 hours (build only; a teammate records the video) |
| **Demo commune** | Sangkat Tonle Basak `120101`, Khan Chamkar Mon, Phnom Penh |
| **Background docs** | `product_requirements_document_prd.md`, `end_to_end_system_architecture.md`, `mvp_scope_and_data_refined.md`, `data/README.md` |

---

## 1. Intent

A competition entry. Judges first review a **recorded demo video** to shortlist teams; shortlisted teams then demo **live on stage**. Judges are both **non-technical** (they must *feel* that an older, low-literacy resident can get help in one or two taps) and **technical** (they look at how it's built and whether the data can be trusted).

This build exists to make that video possible. A teammate records it, so every feature below must be **reliable enough to film on a laptop** and **readable enough for a teammate to continue**.

### The three story moments the video must show
1. **Resident:** taps the pinned link in the commune group → Khmer welcome + big buttons → taps 🚨 → number opens the dialer → taps 📢 → sees the flyer, reads the text, plays the voice note.
2. **Clerk:** taps `📝 ផ្សាយដំណឹង` in a private chat → sends text, a photo, and a voice note → preview → ✅ → it appears in the group, with an "open the bot" button under it.
3. **Under the hood (~30 s):** official DataEF codes for all 1,661 communes; every contact has a source and a verification status; Khmer typing variants are normalized; adding a commune is adding rows, not code; tests pass.

## 2. Goals, non-goals, anti-goals

**Goals**
* All 5 resident buttons work for commune `120101` from `data/seed/`.
* News posts support **text, picture, and voice together** (each optional, at least one required) — for readers and non-readers alike.
* A teammate can clone the repo, follow the README, and run the bot in under 15 minutes.
* Pure logic (formatting, keyword matching, expiry, seed loading) has unit tests.

**Non-goals (this build)**
* Hosting, webhooks, HTTPS, Docker, PostgreSQL (stage-demo phase, later).
* GPS binding, speech-to-text, text-to-speech, LLM/RAG answers, web dashboard.
* Admin invite links, forward-to-archive, scheduled posts, multi-commune switching UI beyond a simple picker.

**Anti-goals (would be a failure even if it "works")**
* Showing an **unverified or missing phone number as if it were verified**, or inventing one.
* Making residents type commands or English.
* The bot crashing or hanging mid-recording (any handler error must reply politely and keep running).
* Any change to `E:\KAI_AI`.

## 3. Constraints

* Windows 11 laptop, **Python 3.14** (only version installed), git 2.56.
* Telegram Bot API via **long polling** — no public URL needed.
* Khmer UI text comes from `data/seed/bot_copy_kh.json`; data from `data/seed/*.csv` (see `data/README.md`).
* Telegram limits that shape the design:
  * A **voice note cannot be in the same message** as a photo; and voice cannot join a photo media group. → A post is *photo + caption*, then the *voice note as a reply to it*.
  * Photo **captions max 1,024 characters**. → If text is longer, send the text as its own message and the photo without caption.
  * Bots **cannot message a user first**. → Residents enter via deep link `t.me/<bot>?start=120101`.
  * `file_id` values are reusable by the same bot forever. → Store `file_id`s; no media storage.

## 4. Approaches considered

| | Approach | Trade-off | Decision |
| :--- | :--- | :--- | :--- |
| **A** | Python + aiogram 3, long polling, SQLite, one process | Fastest and least fragile for filming; matches architecture "Option A"; can reuse KAI's Khmer normalizer. Less "production" on camera. | **Chosen** (user approved) |
| B | FastAPI webhook + PostgreSQL in Docker + tunnel (the full architecture) | Looks production-grade, but ~1 h of setup in a 5 h budget and more moving parts to break while filming. | Deferred to the stage-demo phase |
| C | Node.js + grammY | Works, but loses the Khmer normalizer and departs from the architecture doc. | Dropped |

Upgrade path to B is kept open: DB access goes through one module (`db.py`) with portable SQL, so moving to PostgreSQL later is contained.

## 5. Design

### 5.1 Layout

```
service_bot/
├── pyproject.toml            # deps: aiogram 3.x, python-dotenv, pytest, pytest-asyncio
├── .env.example              # BOT_TOKEN, ADMIN_USER_IDS, DEMO_COMMUNE_CODE, DB_PATH
├── README.md                 # setup + run + demo script for the teammate
├── sangkat_bot/
│   ├── __main__.py           # python -m sangkat_bot → start polling
│   ├── config.py             # reads .env
│   ├── db.py                 # sqlite3 connection, schema, all queries
│   ├── schema.sql
│   ├── seed.py               # python -m sangkat_bot.seed → load DataEF + data/seed
│   ├── copy.py               # loads bot_copy_kh.json, fills {commune_type_kh}/{commune_kh}
│   ├── khmer/                # vendored copy of KAI_AI shared/kai_khmer normalizer (4 files + rules json)
│   ├── keywords.py           # normalize → intent
│   ├── formatting.py         # emergency card, contact lines, services, hall, announcement caption
│   ├── keyboards.py          # resident reply keyboard, admin keyboard, inline buttons
│   └── handlers/
│       ├── resident.py       # /start <code>, 5 buttons, picker, fallback, non-text fallback
│       ├── admin.py          # announce FSM, /delete_last
│       └── group.py          # /bind in group
└── tests/                    # pytest for keywords, formatting, expiry, seed, copy
```

### 5.2 Data (SQLite, `data/sangkat.db`, rebuilt by `seed`)

Tables follow the architecture DDL with the refinements from `mvp_scope_and_data_refined.md §4`:

* `provinces`, `districts`, `communes` — **all** DataEF 2025 rows (codes stay zero-padded text; files read with `utf-8-sig`). `communes.commune_type` set to `sangkat` for province `12`, else NULL.
* `villages` — only the 16 demo villages (`data/seed/demo_villages.csv`).
* `commune_configs` — from `commune_configs.csv`, plus `telegram_group_id` (set by `/bind`).
* `emergency_numbers` — from `national_emergency_numbers.csv` (`scope` = `national` or `province:12`; only `is_active=true` shown).
* `local_contacts` — from `local_contacts.csv` (only `is_active=true` shown), keeps `verification_status`, `source`, `source_ref`.
* `public_services` — from `public_services.csv`.
* `users` — `telegram_user_id`, `commune_code`, `first_seen_at`, `last_active_at`. Nothing else.
* `announcements` — `id, commune_code, source ('seed'|'admin'), posted_by, text_kh, photo_file_id, voice_file_id, group_message_id, group_voice_message_id, event_date, expires_at, is_deleted, created_at`. Seeded from `demo_announcements.csv` (text-only).
* `audit_logs` — publish/delete/bind events.

`seed` is idempotent: it **drops and recreates** reference tables (admin hierarchy, contacts, emergency numbers, services). It **preserves** `users`, `audit_logs`, `commune_configs.telegram_group_id`, and admin-published announcements; seeded announcements carry `source='seed'` and are deleted and re-inserted on each run (so they never duplicate).

### 5.3 Resident experience

* `/start 120101` → upsert user → welcome (2 lines) + persistent reply keyboard (`is_persistent=True`, `resize_keyboard=True`), layout from `bot_copy_kh.json`: 🚨 alone on top, then 2 × 2.
* `/start` without a valid active code → picker of active communes (one button each) → bind → welcome.
* **🚨 Emergency:** one message. National block (active numbers in `sort_order`, Phnom Penh `666` only when province is `12`), then local block (police, fire, ambulance, 24 h hospitals) for the user's commune. Each line: name, number(s) on their own line, map link.
* **🏥 Health:** health center first (if active), then hospitals by `sort_order`: name, hours or "24 ម៉ោង", phone, map link.
* **📢 News:** latest **3** non-deleted, non-expired announcements, sent **oldest → newest** so the newest sits above the keyboard; each replayed exactly as published (photo + caption, then voice). Empty → "មិនទាន់មានដំណឹងថ្មីទេ។".
* **📄 Services:** inline buttons, one per service → detail card (documents as a checklist, fee or "ask" text, where, who must come).
* **📍 Hall:** name, days/hours, phone, address, map link — plus a native Telegram **location pin** (`send_location`) so it can be opened in any map app.
* **Typed text:** normalize (vendored KAI normalizer + strip ZWSP) → first matching intent → same handler as the button. No match → polite fallback. Voice/sticker/photo from residents → `non_text_fallback`.

**Phone display rules**
* `verified` / `unverified_published`: show the number. Numbers are plain text on their own line (Telegram linkifies them for tap-to-call). **First build task checks this on a real phone** (risk R4): send `117`, `023 426 948`, `023426948`, `+855 23 426 948`, and see which become tappable on Android and iOS; the formatter uses the winning format (one function, `format_phone()`).
* `conflicting`: show the first number (it is the best guess) — same display.
* `missing`: show the place and map link with "លេខទូរស័ព្ទ៖ កំពុងផ្ទៀងផ្ទាត់". **Never** fabricate.
* Footer under every contact card in **demo mode** (`DEMO_MODE=true`): "⚠️ ទិន្នន័យសាកល្បង" (demo data), so nothing filmed looks officially verified.

### 5.4 Clerk (admin) experience

* Admins = `ADMIN_USER_IDS` in `.env`, each mapped to `DEMO_COMMUNE_CODE`. Admins see an extra row on their keyboard: `📝 ផ្សាយដំណឹង`.
* **Announce FSM** (aiogram FSM, in-memory storage):
  1. `ask_text` — send text, or tap "រំលង" (skip).
  2. `ask_photo` — send a photo, or skip.
  3. `ask_voice` — send a voice note (or audio file), or skip.
  4. `preview` — bot shows exactly what the group will see + `✅ ផ្សាយ` / `❌ បោះបង់`. If all three were skipped → back to step 1 with a gentle message.
  5. `publish` — post to the group using one **rendering rule** (also used by the preview and the 📢 feed):
     * **Lead message:** if there is a photo → photo with caption = header + text (if header + text > 1,024 chars, send header + text as a text message first and the photo with header only). No photo → a text message with header + text (header alone for voice-only posts). The lead message carries the inline URL button `📱 សួរជំនួយការ` → deep link.
     * **Voice:** if present, sent as a **reply to the lead message**.
     * Save the row + both message ids; write `audit_logs`; confirm to the admin.
* `/cancel` at any step exits. `/delete_last` deletes the admin's latest announcement from the group (both messages) and marks it deleted.
* Errors from Telegram (bot not in group, no rights) → the admin gets `error_not_admin_in_group`; the bot keeps running.

### 5.5 Group binding

* An admin adds the bot to the group, then sends `/bind 120101` in the group. The bot saves the group id on that commune, replies with confirmation, and posts the **onboarding message** (welcome line + `📱 សួរជំនួយការ` deep-link button) and tries to **pin** it (works if the bot is a group admin with pin rights; otherwise it says so).
* All other group messages are ignored.

### 5.6 Reliability & privacy

* One global error handler: log the exception (no message text, no token), reply with the fallback line, keep polling.
* Logs: `event`, `commune_code`, `intent`/`button`, `latency_ms`. Never raw user text.
* Store only `telegram_user_id` + `commune_code` + timestamps for residents.

### 5.7 Tests (pytest)

Unit tests for pure functions only — no live Telegram calls:
* keyword matching (incl. ZWSP, `ឣ`→`អ`, split vowel `េ`+`ា`), no-match case;
* emergency/health/hall formatting (missing phone text, `666` only for province 12, demo footer);
* announcement selection (expired hidden, deleted hidden, latest 3 oldest→newest);
* caption split at 1,024 chars;
* seed loader (BOM handling, zero-padded codes, idempotent re-run keeps `telegram_group_id`);
* copy template filling (`សង្កាត់` for `120101`).

## 6. Decided vs. left to the builder

**Decided (by the user):** competition video first, stage later; news = text + picture + voice; build-only 5 h; approach A; teammate continues from specs/tasks in the repo.

**Claude's calls (correct if wrong):** SQLite file DB; admins via `.env`; latest 3 news oldest→newest; native location pin for the hall; demo-data footer; `/bind` posts and pins the onboarding message; vendor KAI's normalizer by copying (KAI_AI untouched; a header comment records where it came from); the module layout above; git repo initialised in `E:\service_bot` so the teammate can push it to GitHub.

**Left to the builder:** exact handler wiring, message spacing, emoji choices within the copy file, test fixtures.

## 7. Prerequisites the user prepares (in parallel)

1. Bot token from **@BotFather** (`/newbot`); set the bot's name/description in Khmer; **disable privacy mode is NOT needed** (commands to the bot still arrive).
2. A test Telegram **group** standing in for the commune group; add the bot and make it **admin** (post + pin rights).
3. Two Telegram accounts/phones: clerk (its numeric user id → `ADMIN_USER_IDS`; get it from @userinfobot) and resident.
4. A sample flyer image and a 15–30 s Khmer voice note for the clerk story.
