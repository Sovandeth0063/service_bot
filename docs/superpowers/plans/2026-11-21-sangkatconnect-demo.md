# SangkatConnect Demo MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **For human teammates:** tick each box as you finish it and commit. The first unticked box is where to resume. Run all commands from the repo root `E:\service_bot`.

**Goal:** A Telegram bot for Sangkat Tonle Basak (`120101`) that gives older residents one-tap emergency, health, hall, service and news information, and lets a clerk post news as text + picture + voice to the commune group — reliable enough to film a competition demo video.

**Architecture:** One Python process, aiogram 3 with long polling, SQLite file database rebuilt from `data/seed/` + DataEF CSVs. Pure logic (normalizing, matching, formatting, post rendering, queries) lives in small modules with unit tests; Telegram handlers are thin and verified manually with a live bot.

**Tech Stack:** Python 3.14, aiogram 3.33, python-dotenv, sqlite3 (stdlib), pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-11-21-sangkatconnect-demo-design.md` (read it first; this plan does not repeat its reasoning).

## Global Constraints

- Python **3.14** (`py -3`); dependency `aiogram>=3.33,<4`. No PostgreSQL, Docker, webhooks or LLMs.
- **Never modify `E:\KAI_AI`.** The Khmer normalizer is *copied* into `sangkat_bot/khmer/`.
- All user-facing Khmer text comes from `data/seed/bot_copy_kh.json` (add keys there, never hard-code Khmer in Python).
- Read every CSV with `encoding="utf-8-sig"`; keep admin codes as **zero-padded strings**; CSV `true`/`false` → bool; empty string → `NULL`.
- Timestamps are stored as **UTC ISO-8601** strings (`datetime.astimezone(UTC).isoformat(timespec="seconds")`), so SQL string comparison is correct.
- Phones: never invent a number. `missing` → copy key `phone_missing`. `DEMO_MODE=true` → every contact card ends with copy key `demo_footer`.
- Messages use `parse_mode="HTML"`; every DB/user string inserted into HTML goes through `html.escape`.
- Logs never contain message text or the bot token.
- Resident keyboard: `is_persistent=True`, `resize_keyboard=True`, layout `[["emergency"], ["health", "announcements"], ["services", "location"]]`.
- News feed: latest **3**, non-deleted, non-expired, sent **oldest → newest**. Caption limit **1024** characters.

## Review Focus

1. A resident who never used a deep link types text or taps an old button → gets the commune picker, not an error. *(Task 6, `resolve_commune` test)*
2. Admin publishes when the commune has no `telegram_group_id` (group not bound) → clear Khmer error, nothing saved, FSM cleared. *(Task 7, `publish_target` test)*
3. Announcement text longer than a caption allows → text sent separately, photo with header only. *(Task 5, `test_long_text_with_photo_splits`)*
4. `expires_at` written with `+07:00` compared against UTC "now" → an item expiring at 12:00 Phnom Penh time is hidden at 05:01 UTC. *(Task 3, `test_latest_hides_expired_across_timezones`)*
5. Whitespace-only, emoji-only or empty text from a resident → polite fallback, no crash. *(Task 2, `test_blank_and_emoji_do_not_match`)*

---

### Task 1: Project scaffold, settings, and phone-link check

**Files:**
- Create: `pyproject.toml`, `.env.example`, `sangkat_bot/__init__.py`, `sangkat_bot/config.py`, `scripts/phone_check.py`, `tests/__init__.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True)
  class Settings:
      bot_token: str
      admin_user_ids: frozenset[int]
      demo_commune_code: str      # default "120101"
      db_path: Path               # default Path("data/sangkat.db")
      seed_dir: Path              # Path("data/seed")
      dataef_dir: Path            # Path("data/raw/dataef")
      demo_mode: bool             # default True
  def load_settings(env: Mapping[str, str] | None = None) -> Settings  # env=None → os.environ after load_dotenv()
  ```

- [ ] **Step 1: Create `pyproject.toml`** — project `sangkat-bot`, `requires-python = ">=3.12"`, deps `aiogram>=3.33,<4`, `python-dotenv>=1.0`; optional `dev = ["pytest>=8", "pytest-asyncio>=0.24"]`; `[tool.pytest.ini_options] testpaths=["tests"]`, `asyncio_mode="auto"`; setuptools package-data `sangkat_bot = ["schema.sql", "khmer/resources/*.json"]`.
- [ ] **Step 2: Create a venv and install** — `py -3 -m venv .venv && .venv\Scripts\python -m pip install -e ".[dev]"`. Expected: `Successfully installed aiogram-3.33...`.
- [ ] **Step 3: Write `.env.example`**
  ```
  BOT_TOKEN=123456:replace-me
  ADMIN_USER_IDS=111111111
  DEMO_COMMUNE_CODE=120101
  DB_PATH=data/sangkat.db
  DEMO_MODE=true
  ```
- [ ] **Step 4: Write failing tests `tests/test_config.py`**
  ```python
  def test_load_settings_parses_values():
      s = load_settings({"BOT_TOKEN": "t", "ADMIN_USER_IDS": "1, 22", "DEMO_MODE": "false"})
      assert s.bot_token == "t" and s.admin_user_ids == frozenset({1, 22})
      assert s.demo_commune_code == "120101" and s.demo_mode is False
      assert s.db_path == Path("data/sangkat.db")

  def test_missing_token_raises():
      with pytest.raises(ValueError, match="BOT_TOKEN is not set"):
          load_settings({})

  def test_empty_admin_list_is_allowed():
      assert load_settings({"BOT_TOKEN": "t"}).admin_user_ids == frozenset()
  ```
- [ ] **Step 5: Run** `.venv\Scripts\python -m pytest tests/test_config.py -v` → FAIL (import error).
- [ ] **Step 6: Implement `load_settings`** in `sangkat_bot/config.py` (`DEMO_MODE` true unless value is `false`/`0`/`no`, case-insensitive).
- [ ] **Step 7: Run** the tests → PASS.
- [ ] **Step 8: Write `scripts/phone_check.py`** — sends one message to every `ADMIN_USER_IDS` user (they must have pressed Start on the bot) with these lines, each on its own line: `117`, `023 426 948`, `023426948`, `+855 23 426 948`, `012 786 693`.
- [ ] **Step 9: Manual check (needs a real phone).** Run `.venv\Scripts\python scripts/phone_check.py`; on Android and iOS note which lines are tappable. Record the result in the spec §5.3 under "Phone display rules" (one line: winning format). If spaced local numbers work, keep data as-is; otherwise Task 4's `format_phone` converts to the winning format.
- [ ] **Step 10: Commit** — `git add -A && git commit -m "chore: scaffold project, settings, phone-link check"`

---

### Task 2: Vendored Khmer normalizer and keyword matching

**Files:**
- Create: `sangkat_bot/khmer/{__init__.py,normalizer.py,constants.py,exceptions.py,resources.py}`, `sangkat_bot/khmer/resources/normalizer_rules.json`, `sangkat_bot/keywords.py`, `tests/test_keywords.py`

**Interfaces:**
- Produces:
  ```python
  # sangkat_bot/khmer/__init__.py
  def normalize(text: str) -> NormalizedText          # re-export; .text is the normalized string
  # sangkat_bot/keywords.py
  INTENTS = ("emergency", "health", "announcements", "services", "location")
  def normalize_text(text: str) -> str                 # normalize(...).text, whitespace collapsed, stripped
  def load_keywords(path: Path) -> list[tuple[str, str]]   # (intent, normalized keyword), CSV order kept
  def match_intent(text: str, keywords: list[tuple[str, str]]) -> str | None
  ```

- [ ] **Step 1: Copy (do not edit the source)** `E:\KAI_AI\shared\kai_khmer\{normalizer,constants,exceptions,resources}.py` and `resources\normalizer_rules.json` into `sangkat_bot/khmer/`. In the copies only, replace `kai_khmer` with `sangkat_bot.khmer` in imports and in `resources.py`'s default package name. Add to the top of each copied file: `# Vendored from KAI_AI shared/kai_khmer (same author), 2026-11-21. Do not edit here; re-copy instead.` Remove references to dictionary/model resources if they make import fail (only `NORMALIZER_RULES` is needed).
- [ ] **Step 2: Write failing tests `tests/test_keywords.py`** (load `data/seed/keywords_kh.csv`)
  ```python
  @pytest.mark.parametrize("text,intent", [
      ("ផ្ទះ\u200bខ្ញុំ\u200bឆេះ", "emergency"),
      ("ខ្ញុំឈឺ ចង់ទៅពេទ្យ", "health"),
      ("សំបុត្រ\u200bកំណើត", "services"),
      ("\u17a3ត្តសញ្ញាណប័ណ្ណ", "services"),   # deprecated ឣ normalizes to អ
      ("119", "emergency"),
      ("ពេទ្យ ភ្លើង", "emergency"),             # emergency wins: CSV order is priority
      ("សាលាសង្កាត់បើកម៉ោងប៉ុន្មាន", "location"),
  ])
  def test_match_intent(text, intent, keywords): assert match_intent(text, keywords) == intent

  @pytest.mark.parametrize("text", ["hello", "", "   ", "👍", "\u200b"])
  def test_blank_and_emoji_do_not_match(text, keywords): assert match_intent(text, keywords) is None
  ```
- [ ] **Step 3: Run** `.venv\Scripts\python -m pytest tests/test_keywords.py -v` → FAIL.
- [ ] **Step 4: Implement** `keywords.py`: keywords are normalized at load time with the same `normalize_text`; `match_intent` returns the intent of the first keyword (CSV order) that is a substring of the normalized text; empty normalized text → `None`.
- [ ] **Step 5: Run** → PASS. If `"សាលាសង្កាត់បើកម៉ោងប៉ុន្មាន"` resolves to `announcements` or similar, fix keyword *order* in the CSV, not the code.
- [ ] **Step 6: Commit** — `git commit -am "feat: vendor Khmer normalizer, add keyword intent matching"` (use `git add -A` first).

---

### Task 3: Database schema, queries and seed loader

**Files:**
- Create: `sangkat_bot/schema.sql`, `sangkat_bot/db.py`, `sangkat_bot/seed.py`, `tests/conftest.py`, `tests/test_seed_and_db.py`

**Interfaces:**
- Consumes: `Settings` (Task 1).
- Produces (all take `conn: sqlite3.Connection`, rows are `sqlite3.Row`):
  ```python
  def connect(db_path: Path) -> sqlite3.Connection   # row_factory=Row, PRAGMA foreign_keys=ON, applies schema.sql (CREATE IF NOT EXISTS)
  def get_commune(conn, code: str) -> Row | None     # communes ⋈ districts ⋈ provinces LEFT JOIN commune_configs:
        # commune_code, commune_kh, commune_en, district_kh, province_kh, province_code, commune_type,
        # hall_name_kh, hall_phone, office_days_kh, office_hours_kh, address_kh, lat, lon, google_maps_url,
        # telegram_group_id, is_active, verification_status
  def list_active_communes(conn) -> list[Row]
  def upsert_user(conn, user_id: int, commune_code: str) -> None
  def get_user_commune(conn, user_id: int) -> str | None
  def emergency_numbers(conn, province_code: str) -> list[Row]       # is_active, scope 'national' or f'province:{code}', by sort_order
  def local_contacts(conn, commune_code: str, categories: Sequence[str], only_24h: bool = False) -> list[Row]  # is_active; ordered by categories order then sort_order
  def public_services(conn, commune_code: str) -> list[Row]          # commune_code = code OR NULL, is_active, by sort_order
  def get_service(conn, service_key: str) -> Row | None
  def set_group(conn, commune_code: str, group_id: int) -> None
  def insert_announcement(conn, *, commune_code: str, source: str, posted_by: int | None, text_kh: str | None,
                          photo_file_id: str | None, voice_file_id: str | None, event_date: str | None,
                          expires_at: datetime | None, created_at: datetime) -> int
  def set_announcement_messages(conn, ann_id: int, group_message_id: int | None, group_voice_message_id: int | None) -> None
  def latest_announcements(conn, commune_code: str, now: datetime, limit: int = 3) -> list[Row]  # newest `limit`, returned oldest→newest
  def last_admin_announcement(conn, commune_code: str, posted_by: int) -> Row | None             # not deleted
  def mark_deleted(conn, ann_id: int) -> None
  def audit(conn, actor_user_id: int, commune_code: str | None, action: str, target_id: str | None, metadata: dict) -> None
  # sangkat_bot/seed.py
  def run_seed(conn, dataef_dir: Path, seed_dir: Path) -> dict[str, int]   # table → row count
  # `python -m sangkat_bot.seed` → load_settings(), connect(), run_seed(), print counts
  ```

- [ ] **Step 1: Write `schema.sql`** — tables from spec §5.2 (columns as listed there and in `data/seed/*.csv` headers). `communes.commune_type TEXT`, `announcements.source TEXT CHECK (source IN ('seed','admin'))`, `announcements.is_deleted INTEGER NOT NULL DEFAULT 0`. All `CREATE TABLE IF NOT EXISTS`.
- [ ] **Step 2: Write `tests/conftest.py`** — fixture `conn(tmp_path)` → `connect(tmp_path/"t.db")` then `run_seed(conn, Path("data/raw/dataef"), Path("data/seed"))`.
- [ ] **Step 3: Write failing tests `tests/test_seed_and_db.py`**
  ```python
  def test_counts(conn):
      c = run_seed(conn, DATAEF, SEED)
      assert c["provinces"] == 25 and c["districts"] == 210 and c["communes"] == 1661
      assert c["villages"] == 16 and c["emergency_numbers"] == 5 and c["local_contacts"] == 10
      assert c["public_services"] == 3 and c["seed_announcements"] == 4

  def test_codes_are_zero_padded_and_type_set(conn):
      assert get_commune(conn, "010201")["commune_en"] == "Banteay Neang"
      tb = get_commune(conn, "120101")
      assert tb["commune_kh"] == "ទន្លេបាសាក់" and tb["commune_type"] == "sangkat" and tb["is_active"] == 1

  def test_666_only_in_phnom_penh(conn):
      assert "666" in [r["number"] for r in emergency_numbers(conn, "12")]
      assert "666" not in [r["number"] for r in emergency_numbers(conn, "01")]
      assert "115" not in [r["number"] for r in emergency_numbers(conn, "12")]   # inactive

  def test_inactive_contacts_hidden(conn):
      names = [r["name_en"] for r in local_contacts(conn, "120101", ["health_center", "police"])]
      assert "Health Center (TBD)" not in names and "Tonle Basak Administrative Police Post" not in names

  def test_reseed_preserves_group_users_and_admin_posts(conn):
      set_group(conn, "120101", -100123); upsert_user(conn, 5, "120101")
      insert_announcement(conn, commune_code="120101", source="admin", posted_by=5, text_kh="x",
                          photo_file_id=None, voice_file_id=None, event_date=None, expires_at=None, created_at=NOW)
      c = run_seed(conn, DATAEF, SEED)
      assert get_commune(conn, "120101")["telegram_group_id"] == -100123
      assert get_user_commune(conn, 5) == "120101" and c["seed_announcements"] == 4
      assert conn.execute("select count(*) from announcements where source='admin'").fetchone()[0] == 1

  def test_latest_hides_expired_across_timezones(conn):
      # seed row "ID card" expires 2026-11-28T12:00+07:00 == 05:00 UTC
      before = datetime(2026, 11, 28, 4, 59, tzinfo=UTC); after = datetime(2026, 11, 28, 5, 1, tzinfo=UTC)
      assert any("អត្តសញ្ញាណប័ណ្ណ" in r["text_kh"] for r in latest_announcements(conn, "120101", before))
      assert not any("អត្តសញ្ញាណប័ណ្ណ" in r["text_kh"] for r in latest_announcements(conn, "120101", after))

  def test_latest_is_three_oldest_first(conn):
      rows = latest_announcements(conn, "120101", datetime(2026, 11, 21, 12, tzinfo=UTC))
      assert len(rows) == 3 and [r["created_at"] for r in rows] == sorted(r["created_at"] for r in rows)
      assert not any("អុំទូក" in r["text_kh"] for r in rows)   # expired water-festival item

  def test_deleted_hidden(conn):
      rid = latest_announcements(conn, "120101", NOW)[-1]["id"]; mark_deleted(conn, rid)
      assert rid not in [r["id"] for r in latest_announcements(conn, "120101", NOW)]
  ```
  (`NOW = datetime(2026, 11, 21, 12, tzinfo=UTC)`; `DATAEF`, `SEED` are the repo paths.)
- [ ] **Step 4: Run** `.venv\Scripts\python -m pytest tests/test_seed_and_db.py -v` → FAIL.
- [ ] **Step 5: Implement `db.py`** with the signatures above (parameterised SQL only; `audit` stores `metadata` with `json.dumps(..., ensure_ascii=False)`).
- [ ] **Step 6: Implement `run_seed`** — in one transaction: delete + reload `provinces`, `districts`, `communes` (from `provinces_2025.csv`, `districts_2025.csv`, `communes_2025.csv`; set `commune_type='sangkat'` where `province_code='12'`), `villages` (`seed/demo_villages.csv`), `emergency_numbers`, `local_contacts`, `public_services`; upsert `commune_configs` **keeping an existing `telegram_group_id`**; delete `announcements where source='seed'` and insert `demo_announcements.csv` (convert `expires_at`/`created_at` to UTC). Return counts with keys used in `test_counts`.
- [ ] **Step 7: Run** → PASS. Then `.venv\Scripts\python -m sangkat_bot.seed` → prints the same counts and creates `data/sangkat.db`.
- [ ] **Step 8: Commit** — `git add -A && git commit -m "feat: sqlite schema, queries and idempotent seed loader"`

---

### Task 4: Khmer copy and message formatting

**Files:**
- Create: `sangkat_bot/copy.py`, `sangkat_bot/formatting.py`, `tests/test_formatting.py`
- Modify: `data/seed/bot_copy_kh.json` (add keys below)

**Interfaces:**
- Consumes: rows from Task 3.
- Produces:
  ```python
  # copy.py
  def load_copy(path: Path) -> dict
  def commune_type_kh(commune_type: str | None) -> str          # 'sangkat' → 'សង្កាត់', else 'ឃុំ'
  class Copy:
      def __init__(self, data: dict, commune_type: str | None, commune_kh: str): ...
      def t(self, key: str) -> str                  # dotted keys ("admin.publish"); fills {commune_type_kh} and {commune_kh}
      def button(self, intent: str) -> str          # buttons[intent], filled
      def button_intent(self, text: str) -> str | None   # exact label → intent
  # formatting.py
  def format_phone(raw: str | None) -> list[str]   # split on "|", strip, drop empties; apply Task 1 winning format
  def contact_block(row: Row, copy: Copy) -> str   # bold name, hours (or t("hours_24h") if is_24h), each phone on its own line or t("phone_missing"), map link
  def emergency_card(national: list[Row], local: list[Row], copy: Copy, demo_mode: bool) -> str
  def health_card(contacts: list[Row], copy: Copy, demo_mode: bool) -> str
  def hall_card(commune: Row, copy: Copy, demo_mode: bool) -> str
  def service_card(service: Row, copy: Copy) -> str  # title, docs as "☐ item" lines (split on "|"), fee or fee_conditions_kh, where_kh, who_must_come_kh
  ```

- [ ] **Step 1: Add copy keys** to `bot_copy_kh.json`: `"map_link": "🗺️ មើលផែនទី"`, `"hours_24h": "បើក 24 ម៉ោង"`, `"demo_footer": "⚠️ ទិន្នន័យសាកល្បង — សូមផ្ទៀងផ្ទាត់មុនប្រើពិតប្រាកដ"`, `"services_header": "📄 សូមជ្រើសរើសសេវា៖"`, `"docs_needed": "ឯកសារត្រូវយកមក៖"`, `"fee": "តម្លៃ៖"`, `"where": "កន្លែង៖"`, `"who": "អ្នកត្រូវមក៖"`, `"health_header": "🏥 មន្ទីរពេទ្យ និងមណ្ឌលសុខភាព"`, `"hall_header": "📍 សាលា{commune_type_kh}{commune_kh}"`, and under `admin`: `"skip": "⏭️ រំលង"`, `"ask_photo": "សូមផ្ញើរូបភាព (ឬចុច រំលង)។"`, `"ask_voice": "សូមផ្ញើសារជាសំឡេង (ឬចុច រំលង)។"`, `"need_something": "សូមផ្ញើយ៉ាងហោចណាស់ អត្ថបទ រូបភាព ឬសំឡេង មួយ។"`, `"wrong_type": "សូមផ្ញើតាមប្រភេទដែលបានស្នើ ឬចុច រំលង។"`, `"no_group": "⚠️ មិនទាន់ភ្ជាប់ក្រុមទេ។ សូមវាយ /bind {commune_code} នៅក្នុងក្រុម។"`, `"nothing_to_delete": "មិនមានដំណឹងដែលអាចលុបបានទេ។"`, `"bound": "✅ ក្រុមនេះបានភ្ជាប់ជាមួយ{commune_type_kh}{commune_kh}។"`, `"pin_failed": "⚠️ មិនអាចខ្ទាស់សារបានទេ — សូមផ្តល់សិទ្ធិ ខ្ទាស់សារ ដល់ជំនួយការ។"`. (`{commune_code}` is filled by the caller with `.format`.)
- [ ] **Step 2: Write failing tests `tests/test_formatting.py`** (use the seeded `conn` fixture)
  ```python
  def test_copy_fills_sangkat(copy_tb): assert copy_tb.button("location") == "📍 សាលាសង្កាត់"
  def test_copy_khum_default(): assert commune_type_kh(None) == "ឃុំ"
  def test_button_intent_roundtrip(copy_tb):
      for i in INTENTS: assert copy_tb.button_intent(copy_tb.button(i)) == i
      assert copy_tb.button_intent("random") is None
  def test_format_phone_splits(): assert format_phone("666 | 012 786 693") == ["666", "012 786 693"]   # adjust to Task 1 format
  def test_format_phone_empty(): assert format_phone(None) == [] and format_phone("") == []
  def test_missing_phone_says_verifying(conn, copy_tb):
      row = [r for r in local_contacts(conn, "120101", ["hospital"]) if r["name_en"] == "Preah Ang Duong Hospital"][0]
      assert copy_tb.t("phone_missing") in contact_block(row, copy_tb)
  def test_emergency_card_has_national_and_local(conn, copy_tb):
      card = emergency_card(emergency_numbers(conn, "12"), local_contacts(conn, "120101", ["police", "fire", "ambulance", "hospital"], only_24h=True), copy_tb, demo_mode=True)
      assert "117" in card and "666" in card and "Calmette" not in card and "កាល់ម៉ែត" in card
      assert card.rstrip().endswith(html.escape(copy_tb.t("demo_footer")))
  def test_no_demo_footer_when_off(conn, copy_tb):
      assert copy_tb.t("demo_footer") not in hall_card(get_commune(conn, "120101"), copy_tb, demo_mode=False)
  def test_html_is_escaped(copy_tb):
      row = {"name_kh": "<b>x</b>", "phone_numbers": "", "operating_hours_kh": None, "is_24h": 0, "google_maps_url": None}
      assert "&lt;b&gt;" in contact_block(row, copy_tb)
  def test_service_card_checklist(conn, copy_tb):
      card = service_card(get_service(conn, "birth_certificate"), copy_tb)
      assert card.count("☐") == 4 and "សាលាសង្កាត់" in card
  ```
  (`copy_tb` fixture: `Copy(load_copy(SEED/"bot_copy_kh.json"), "sangkat", "ទន្លេបាសាក់")`. `contact_block` must accept any mapping with those keys.)
- [ ] **Step 3: Run** `.venv\Scripts\python -m pytest tests/test_formatting.py -v` → FAIL.
- [ ] **Step 4: Implement `copy.py` and `formatting.py`.** Map link = `<a href="{url}">{t("map_link")}</a>` only when a URL exists. Blocks separated by a blank line; national numbers as `<b>{name_kh}</b>  {number}`.
- [ ] **Step 5: Run** → PASS.
- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat: Khmer copy loader and message formatting"`

---

### Task 5: Announcement post rendering

**Files:**
- Create: `sangkat_bot/posts.py`, `tests/test_posts.py`

**Interfaces:**
- Produces:
  ```python
  CAPTION_LIMIT = 1024
  @dataclass(frozen=True)
  class Send:
      kind: Literal["text", "photo", "voice"]
      text: str | None        # message text or caption (HTML, already escaped)
      file_id: str | None
      is_lead: bool           # lead message carries the 📱 deep-link button
      reply_to_lead: bool     # voice replies to the lead
  def announcement_body(header: str, text_kh: str | None) -> str   # "<b>{header}</b>" + "\n\n" + escaped text (if any)
  def build_post(header: str, text_kh: str | None, photo_file_id: str | None, voice_file_id: str | None) -> list[Send]
  async def send_post(bot: Bot, chat_id: int, sends: list[Send], lead_markup: InlineKeyboardMarkup | None) -> tuple[int, int | None]
      # returns (lead message_id, voice message_id or None); used for group publish, admin preview and the 📢 feed
  ```

- [ ] **Step 1: Write failing tests `tests/test_posts.py`**
  ```python
  H = "📢 ដំណឹងពីសង្កាត់ទន្លេបាសាក់"
  def test_text_only(): assert build_post(H, "សួស្តី", None, None) == [Send("text", announcement_body(H, "សួស្តី"), None, True, False)]
  def test_photo_with_short_text():
      s = build_post(H, "សួស្តី", "P", None); assert len(s) == 1 and s[0].kind == "photo" and s[0].file_id == "P" and "សួស្តី" in s[0].text and s[0].is_lead
  def test_long_text_with_photo_splits():
      s = build_post(H, "ក" * 1100, "P", None)
      assert [x.kind for x in s] == ["text", "photo"] and s[0].is_lead and not s[1].is_lead and s[1].text == f"<b>{H}</b>"
  def test_all_three():
      s = build_post(H, "t", "P", "V"); assert [x.kind for x in s] == ["photo", "voice"] and s[1].reply_to_lead and s[1].file_id == "V"
  def test_voice_only_has_header_lead():
      s = build_post(H, None, None, "V"); assert [x.kind for x in s] == ["text", "voice"] and s[0].text == f"<b>{H}</b>"
  def test_nothing_raises():
      with pytest.raises(ValueError): build_post(H, None, None, None)
  def test_text_is_escaped(): assert "&lt;script&gt;" in build_post(H, "<script>", None, None)[0].text
  ```
- [ ] **Step 2: Run** `.venv\Scripts\python -m pytest tests/test_posts.py -v` → FAIL.
- [ ] **Step 3: Implement `build_post`** (blank/whitespace `text_kh` counts as no text; length check uses `len(announcement_body(...))`) and `send_post` (`send_message` / `send_photo(caption=…)` / `send_voice(reply_to_message_id=lead_id)`; `parse_mode="HTML"`; markup only on the lead).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: announcement post rendering (text + photo + voice)"`

---

### Task 6: Resident bot — keyboard, buttons, picker, fallback

**Files:**
- Create: `sangkat_bot/keyboards.py`, `sangkat_bot/handlers/__init__.py`, `sangkat_bot/handlers/resident.py`, `sangkat_bot/app.py`, `sangkat_bot/__main__.py`, `tests/test_resident_logic.py`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces:
  ```python
  # keyboards.py
  def resident_keyboard(copy: Copy, is_admin: bool) -> ReplyKeyboardMarkup   # spec layout; admins get extra row [t("admin.announce_button")]
  def commune_picker(communes: list[Row]) -> InlineKeyboardMarkup             # callback_data f"pick:{code}", label "{commune_kh} ({district_kh})"
  def services_menu(services: list[Row]) -> InlineKeyboardMarkup              # callback_data f"svc:{service_key}"
  def open_bot_button(copy: Copy, bot_username: str, commune_code: str) -> InlineKeyboardMarkup  # url f"https://t.me/{bot_username}?start={commune_code}"
  # handlers/resident.py
  def resolve_commune(payload: str | None, stored: str | None, active: set[str]) -> str | None
      # valid active payload wins; else stored if still active; else None (→ picker)
  def resolve_intent(text: str, copy: Copy, keywords: list[tuple[str, str]]) -> str | None   # button label first, then match_intent
  router: Router
  # app.py
  def build_dispatcher(settings: Settings) -> tuple[Bot, Dispatcher]
      # opens DB, loads copy + keywords, puts conn/settings/copy_data/keywords into dp workflow data, includes routers (group, admin, resident — resident last)
  ```

- [ ] **Step 1: Write failing tests `tests/test_resident_logic.py`**
  ```python
  A = {"120101"}
  def test_payload_wins(): assert resolve_commune("120101", None, A) == "120101"
  def test_invalid_payload_falls_back_to_stored(): assert resolve_commune("999999", "120101", A) == "120101"
  def test_no_binding_needs_picker(): assert resolve_commune(None, None, A) is None
  def test_inactive_stored_needs_picker(): assert resolve_commune(None, "010201", A) is None
  def test_button_label_beats_keywords(copy_tb, keywords): assert resolve_intent(copy_tb.button("health"), copy_tb, keywords) == "health"
  def test_typed_text_uses_keywords(copy_tb, keywords): assert resolve_intent("ភ្លើងឆេះ", copy_tb, keywords) == "emergency"
  def test_keyboard_layout(copy_tb):
      kb = resident_keyboard(copy_tb, is_admin=False)
      assert [len(r) for r in kb.keyboard] == [1, 2, 2] and kb.is_persistent and kb.resize_keyboard
      assert len(resident_keyboard(copy_tb, is_admin=True).keyboard) == 4
  ```
- [ ] **Step 2: Run** `.venv\Scripts\python -m pytest tests/test_resident_logic.py -v` → FAIL.
- [ ] **Step 3: Implement `keyboards.py`, `resolve_commune`, `resolve_intent`** → run tests → PASS.
- [ ] **Step 4: Implement resident handlers** (private chats only, `F.chat.type == "private"`):
  * `CommandStart(deep_link=True)` and plain `/start` → `resolve_commune` → `upsert_user` + welcome + `resident_keyboard`, or `commune_picker`.
  * `pick:<code>` callback → bind + welcome.
  * Any text → if user has no commune → picker; else `resolve_intent` → `emergency` (national + local `["police","fire","ambulance","hospital"]`, `only_24h=True` for hospitals — query hospitals separately and concatenate), `health` (`["health_center","hospital"]`), `announcements` (`latest_announcements(now=datetime.now(UTC))` → `send_post` each with `open_bot_button`; none → `no_announcements`), `services` (`services_header` + `services_menu`), `location` (`hall_card` + `bot.send_location(lat, lon)` if both set), `None` → `fallback`.
  * `svc:<key>` callback → `service_card`.
  * Non-text messages (voice, sticker, photo…) → `non_text_fallback`.
  * Every reply re-attaches `resident_keyboard`.
- [ ] **Step 5: Implement `app.py` + `__main__.py`** — `logging.basicConfig(level=INFO)`; `asyncio.run(dp.start_polling(bot))`; `DefaultBotProperties(parse_mode="HTML")`.
- [ ] **Step 6: Manual check** — `.venv\Scripts\python -m sangkat_bot.seed` then `.venv\Scripts\python -m sangkat_bot`. On the resident phone open `https://t.me/<bot>?start=120101`: welcome in Khmer + 5 buttons; each button answers; typing `ភ្លើង` gives the emergency card; a sticker gives the non-text fallback; `/start` with no payload from a fresh account shows the picker. Note any Khmer wording problems in `docs/superpowers/plans/NOTES.md`.
- [ ] **Step 7: Commit** — `git add -A && git commit -m "feat: resident menu, picker, keyword fallback"`

---

### Task 7: Clerk news flow — text, picture, voice, preview, publish, delete

**Files:**
- Create: `sangkat_bot/handlers/admin.py`, `tests/test_admin_logic.py`

**Interfaces:**
- Consumes: `build_post`, `send_post`, `open_bot_button`, db functions, `Copy`.
- Produces:
  ```python
  class AnnounceForm(StatesGroup): text = State(); photo = State(); voice = State(); preview = State()
  def is_admin(user_id: int, settings: Settings) -> bool
  def publish_target(commune: Row | None) -> int | None   # telegram_group_id, or None when unbound/inactive
  router: Router
  ```
  Callback data: `ann:skip`, `ann:publish`, `ann:cancel`. FSM data keys: `text_kh`, `photo_file_id`, `voice_file_id`.

- [ ] **Step 1: Write failing tests `tests/test_admin_logic.py`**
  ```python
  def test_is_admin(): s = load_settings({"BOT_TOKEN": "t", "ADMIN_USER_IDS": "7"}); assert is_admin(7, s) and not is_admin(8, s)
  def test_publish_target_unbound(conn): assert publish_target(get_commune(conn, "120101")) is None
  def test_publish_target_bound(conn): set_group(conn, "120101", -100500); assert publish_target(get_commune(conn, "120101")) == -100500
  def test_publish_target_missing(): assert publish_target(None) is None
  ```
- [ ] **Step 2: Run** `.venv\Scripts\python -m pytest tests/test_admin_logic.py -v` → FAIL → implement `is_admin`, `publish_target` → PASS.
- [ ] **Step 3: Implement the FSM** (private chat, admins only; non-admins tapping the label get the normal resident fallback):
  * Trigger: text == `t("admin.announce_button")` or `/announce` → state `text`, send `admin.ask_content` with inline `[⏭️ រំលង]` (`ann:skip`).
  * `text` state: text message → store; skip → none. Then state `photo` + `admin.ask_photo`.
  * `photo` state: photo → store largest size `file_id`; skip; anything else → `admin.wrong_type` (stay). Then state `voice` + `admin.ask_voice`.
  * `voice` state: voice or audio → store `file_id`; skip; else `wrong_type`. If all three empty → `need_something`, back to `text`. Else state `preview`: `send_post` to the admin's own chat, then `admin.preview` with `[✅ ផ្សាយ] [❌ បោះបង់]`.
  * `ann:publish`: `target = publish_target(get_commune(...))`; `None` → `admin.no_group` (formatted with commune code), clear state, save nothing. Else `send_post(target, …, open_bot_button)`; on `TelegramForbiddenError`/`TelegramBadRequest` → `admin.error_not_admin_in_group`, clear state, save nothing. Success → `insert_announcement(source="admin", created_at=now UTC, expires_at=None)` + `set_announcement_messages` + `audit("publish")` + `admin.published`.
  * `ann:cancel` or `/cancel` in any state → clear + `admin.cancelled`.
  * `/delete_last` → `last_admin_announcement`; none → `nothing_to_delete`; else delete both group messages (ignore "message not found" errors), `mark_deleted`, `audit("delete")`, `admin.deleted`.
- [ ] **Step 4: Manual check (needs the group from Task 8 — do Task 8 first if `/bind` isn't done):** as clerk, post text + flyer + voice → preview in private chat → ✅ → group shows photo with caption and 📱 button, voice as a reply underneath. Resident taps 📢 → sees the same post. Then `/delete_last` → both messages gone from group and feed. Also try: sticker at the photo step (re-prompt), skip everything (need-something), publish before `/bind` (no_group).
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: clerk news flow with text, photo, voice, preview, delete"`

---

### Task 8: Group binding and pinned onboarding message

**Files:**
- Create: `sangkat_bot/handlers/group.py`, `tests/test_group_logic.py`

**Interfaces:**
- Consumes: `is_admin`, `set_group`, `get_commune`, `open_bot_button`, `audit`.
- Produces:
  ```python
  def parse_bind_args(args: str | None, active: set[str]) -> str | None   # "120101" → "120101"; unknown/inactive/blank → None
  router: Router
  ```

- [ ] **Step 1: Write failing tests `tests/test_group_logic.py`**
  ```python
  def test_parse_bind_valid(): assert parse_bind_args(" 120101 ", {"120101"}) == "120101"
  @pytest.mark.parametrize("a", [None, "", "999999", "12010"])
  def test_parse_bind_invalid(a): assert parse_bind_args(a, {"120101"}) is None
  ```
- [ ] **Step 2: Run** → FAIL → implement → PASS.
- [ ] **Step 3: Implement `/bind <code>`** in groups/supergroups (`F.chat.type.in_({"group","supergroup"})`), admins only (others: ignore silently): `set_group`, `audit("bind")`, reply `admin.bound`, send onboarding message (`welcome` + `open_bot_button`) and try `pin_chat_message`; on failure reply `admin.pin_failed`. Ignore all other group messages (no handler).
- [ ] **Step 4: Manual check** — add the bot to the test group as admin, send `/bind 120101` → confirmation + pinned onboarding message; tapping its button opens the bot already bound to Tonle Basak. If the group upgrades to a supergroup (id changes), `/bind` again.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: /bind group to commune and pin onboarding link"`

---

### Task 9: Resilience, README and demo run-sheet for the teammate

**Files:**
- Create: `README.md`, `docs/demo-runsheet.md`
- Modify: `sangkat_bot/app.py` (error handler + event logging)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Add a global error handler** (`dp.errors.register`) that logs `event=error`, exception type and update id (no text), and, when the update has a private chat, replies with `fallback` + `resident_keyboard`. Add one INFO log per resident intent: `event=intent intent=<x> commune=<code> latency_ms=<n>`.
- [ ] **Step 2: Manual check** — temporarily rename `data/sangkat.db` while the bot runs and tap a button → bot replies with the fallback and keeps running; restore the file. Confirm logs show no Khmer user text.
- [ ] **Step 3: Write `README.md`** — what it is (2 lines + link to spec), prerequisites (Python 3.14, bot token, test group, 2 accounts), setup (`venv`, `pip install -e ".[dev]"`, copy `.env.example` → `.env`, `python -m sangkat_bot.seed`, `python -m sangkat_bot`), `/bind`, how to get your user id (@userinfobot), tests (`python -m pytest`), data sources and verification status (link `data/README.md`), "Never modify E:\KAI_AI".
- [ ] **Step 4: Write `docs/demo-runsheet.md`** — for the teammate recording the video: before-recording checklist (fresh seed, bot running, group bound, pinned message visible, flyer + voice file ready, phone font size large, Do-Not-Disturb on); shot list for the three story moments in spec §1 with the exact taps; the 30-second "under the hood" talking points (1,661 DataEF communes, source + verification status per contact, Khmer normalizer examples `ឣ→អ`, add-a-commune = add rows, `pytest` output on screen); known limits to *not* show (missing phones say "កំពុងផ្ទៀងផ្ទាត់").
- [ ] **Step 5: Full verification** — `.venv\Scripts\python -m pytest -v` → all pass; run the whole run-sheet once end-to-end on real phones.
- [ ] **Step 6: Commit** — `git add -A && git commit -m "docs: README and demo run-sheet; global error handler"`

---

## Time budget (5 h)

| Task | Estimate |
| :--- | :--- |
| 1 Scaffold + phone check | 20 min |
| 2 Normalizer + keywords | 20 min |
| 3 DB + seed | 45 min |
| 4 Copy + formatting | 40 min |
| 5 Post rendering | 20 min |
| 6 Resident handlers | 50 min |
| 7 Clerk flow | 50 min |
| 8 Group bind | 20 min |
| 9 Resilience + docs + full run | 35 min |

If time runs short, cut in this order: `/delete_last` (Task 7), pin on bind (Task 8), latency logs (Task 9). Never cut: emergency card, news with photo + voice, demo footer.
