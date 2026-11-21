# MVP Scope & Data Requirements — Refined
## SangkatConnect (Working Title) — Review of PRD v1.0 + Architecture v1.0

| Field | Details |
| :--- | :--- |
| **Purpose** | Tighten the MVP to what proves the core value, fix gaps found in review, and list every piece of data needed before launch |
| **Inputs reviewed** | `product_requirements_document_prd.md`, `end_to_end_system_architecture.md` |
| **Date** | 2026-11-21 |

---

## 1. Review Summary

### What is already strong (keep as-is)
* **Deep-link onboarding** (`t.me/Bot?start=<commune_code>`) — removes the province/district picker, which is the biggest drop-off point for older users.
* **Persistent Reply Keyboard instead of inline menus** — correct choice for this audience.
* **Telegram `file_id` for media** — no storage cost or infrastructure.
* **Emergency lookups read only from the local DB** — no runtime dependency on outside services.
* **Privacy minimization** — store only `telegram_user_id` + `commune_code`.
* **Usability testing with older adults before launch** — keep this; it matters more than any feature.

### The risks that matter more than features
The docs are thorough on engineering but thin on the three things most likely to sink the pilot:

| # | Risk | Why it matters | Mitigation for MVP |
| :--- | :--- | :--- | :--- |
| R1 | **Commune buy-in** | The bot has to be an **admin** of the commune's official group to post. Without the commune chief/clerk's agreement, nothing else works. | Secure 1 committed pilot commune *before* writing code (Week 0). Get a named clerk as content owner. |
| R2 | **Admin adoption** | Clerks already post directly in the group. `/announce` adds steps for them and helps residents more than it helps the clerk. If they skip it, the feed stays empty. | Make posting take 3 taps or fewer **and** let admins forward an existing group post to the bot to archive it (see FR-05 changes). |
| R3 | **Wrong or outdated data** | One wrong emergency number destroys trust and could cause harm. | Every record gets `verified_at` + `verified_by`; test-call every number before launch; re-check every month. |
| R4 | **Tap-to-call assumption is unverified** | Telegram does not reliably turn 3-digit short codes (`117`, `118`, `119`) into tappable links, and detection of local formats varies by client. The whole emergency UX depends on this. | **Week 1 device spike:** test on real Android + iOS. Fallback: send key numbers as `sendContact` cards (big tappable card with a call option) and use `+855` format for normal numbers. |
| R5 | **Group vs. Channel** | Many communes use a Telegram **channel**, Facebook page, or both, not a group. | Confirm what the pilot commune actually uses. Posting to a channel uses the same API call (bot must be channel admin), so support both. Pick a pilot that is active on Telegram. |

### Factual items to re-verify (likely errors in current docs)
* ~~DataEF dataset IDs look auto-generated~~ — **Checked 2026-11-21: all four IDs are real** and download via `https://data.mef.gov.kh/api/v1/public-datasets/<id>/file`. But: CSVs have a UTF-8 BOM, there is **no ឃុំ/សង្កាត់ type column**, the boundary GeoJSON is the **2018 edition (117 of 1,661 communes missing)**, and DataEF has **no facility-level data** (hospitals/police/fire must come from OSM + manual collection). Details in `data/README.md`.
* **Emergency short codes:** `117` / `118` / `119` are confirmed by several government travel advisories; `666` (Phnom Penh fire) by Canada's advisory + Phnom Penh Post. **`115` was not confirmed anywhere** — keep it inactive until verified. Still test-call all of them from a Cambodian SIM.
* **Service office levels:** the schema allows only `commune` or `district_owso`. As I understand it, the **Family Book and Residence Book are handled through the commune administrative police post**, **National ID through the police identification office**, while **birth/marriage certificates go through the commune civil registrar**. OWSO mostly handles business/permit services. Confirm with the pilot clerk and widen the `office_level` values (see §4).
* **Fees:** some civil registration services (e.g., birth registration within the legal time limit) may be free while late registration costs money. Store fee *conditions*, not just one number.

---

## 2. Refined MVP Scope

**MVP goal (one sentence):** *An older resident in one pilot commune can find the right emergency or hospital number in under 15 seconds, and see the commune's last few official announcements without scrolling the group.*

Everything is judged against that sentence.

### 2.1 Scope tiers

| Tier | Feature | Decision | Notes |
| :--- | :--- | :--- | :--- |
| **P0 — must ship** | Deep-link binding + fallback picker | Keep | |
| | Persistent 5-button keyboard | Keep, **shorten labels** (§2.2) | |
| | 🚨 Emergency contacts | Keep | Depends on the R4 spike result |
| | 🏥 Health facilities (1 health center + 2–3 hospitals) | Keep | |
| | 📍 Hall location, hours, phone, map | Keep | |
| | 📢 Admin announce → group post → feed | Keep, **with changes** (§2.3) | |
| | Admin delete (removes from feed **and** group) | Keep | Admins will make mistakes; this is required |
| **P1 — ship if data is verified by Week 2** | 📄 Public service guides | **Cut from 5 to the 3 the clerk says are asked most** | If not verified in time, the button shows hall phone + hours + "call before you go" |
| | Khmer keyword fallback | Keep, small (~30 keywords) | Also handle voice/sticker/photo from residents gracefully (reply with menu) |
| | Short Khmer voice welcome on `/start` | **Add** (optional, cheap) | A 15-second voice note explaining the buttons helps low-literacy users. One pre-recorded `file_id` |
| **Cut from MVP** | Villages table + full national DataEF import | Defer | Only the pilot commune rows are needed. Seed 1–3 `communes` rows by hand, or import only the commune list |
| | Redis | Defer | Use Postgres (or in-memory) FSM storage. One service + one DB |
| | "Nationwide-ready 1,652 communes" | Defer | The schema already scales; don't spend MVP time on it |
| | GPS binding, STT, LLM Q&A, web CMS, scheduling | Already Phase 2 | Agree |

### 2.2 Keyboard: shorter labels, emergency on top

Long labels like `🏛️ សេវាសាធារណៈឃុំ/សង្កាត់` get cut off on small Android screens. Suggested layout (Khmer wording to be confirmed by native speakers and in user testing):

```
┌──────────────────────────────────┐
│        🚨 សង្គ្រោះបន្ទាន់          │   ← full width, always top row
├────────────────┬─────────────────┤
│  🏥 មន្ទីរពេទ្យ  │  📢 ដំណឹងថ្មី    │
├────────────────┼─────────────────┤
│  📄 សេវាឯកសារ  │  📍 សាលាសង្កាត់  │   ← "សាលាឃុំ" for rural communes
└────────────────┴─────────────────┘
```

* Use **ឃុំ or សង្កាត់ based on the commune's type** instead of "ឃុំ/សង្កាត់" with a slash. Store `commune_type` per commune.
* Never change button positions after launch; older users remember where buttons are.

### 2.3 Announcement flow changes (FR-05)

| Change | Why |
| :--- | :--- |
| Add **`expires_at`** (optional) and **`event_date`** (optional). The feed shows only non-expired items. | "Latest 5 active" was never defined. A vaccination day that already happened should not appear as news. |
| Show the **latest 3** (not 5), sent **oldest → newest** | In chat, the last message sent sits right above the keyboard. Newest-last puts the most important item where the eye already is. 5 messages with voice notes is too much scrolling. |
| Every group post includes an inline **URL button** `📱 សួរជំនួយការ` linking to `t.me/Bot?start=<commune_code>` | Ongoing onboarding: every announcement is also an invite, not just the pinned message. |
| **Forward-to-archive:** a whitelisted admin forwards any existing group message to the bot → bot asks "Add to news feed?" → Yes | Covers clerks who post directly in the group out of habit (R2). |
| Admin flow ≤ 3 taps: `/announce` (or a `📝 ផ្សាយដំណឹង` button shown only to admins) → send content → ✅ | Admins are smartphone users too; a button is easier than a command. |

### 2.4 Admin & group setup (missing from current docs)

The docs assume you already have `telegram_user_id` and `telegram_group_id`, but don't say how you get them. Add:

* **Admin invite link:** super admin generates a one-time token → `t.me/Bot?start=admin_<token>` → clerk taps it → bot records their `telegram_user_id` for that commune. No need to ask clerks for their numeric user ID.
* **Group binding:** add bot to the group as admin → super admin sends `/bind <commune_code>` *in the group* → bot saves `telegram_group_id` from the update and confirms. (`my_chat_member` alone tells you the bot joined, not which commune it belongs to.)
* **Health check message:** bot DMs the super admin if it loses admin rights in a group (already in Architecture §8; make it P0).

---

## 3. Data Needed

Grouped by **who provides it** and **how often it changes**. Nothing goes live until every P0 row is marked verified.

### 3.1 National / shared data (collect once, re-check every 6 months)

| Data | Fields | Source | Verification |
| :--- | :--- | :--- | :--- |
| Emergency short codes | `name_kh`, `number`, `category`, `scope` (national / Phnom Penh only) | TRC emergency numbers page; MoH; test calls | Test-call each from a Cambodian SIM; note date |
| Pilot commune admin record(s) | `commune_code`, `district_code`, `province_code`, `commune_kh`, `commune_en`, **`commune_type`** (ឃុំ / សង្កាត់) | DataEF commune list (verify URL) or NCDD gazetteer | Cross-check code + Khmer spelling with the clerk |
| Service guide defaults | see §3.3 | Clerk + official MoI guidance | Clerk signs off |

### 3.2 Per-commune data (P0 — required before activation)

| # | Data | Fields | Who provides | Verification |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Commune hall** | `hall_name_kh`, `phone` (1–2), `office_days_kh`, `office_hours_kh` (incl. lunch break), `address_kh`, `google_maps_url` | Clerk | Visit or call; open map link on a phone |
| 2 | **Police post** (commune admin police) | `name_kh`, `phone_numbers`, `is_24h`, `maps_url` | Clerk / police post | Test call |
| 3 | **Fire response** (district/provincial unit that actually covers this commune) | `name_kh`, `phone_numbers`, `maps_url` | Clerk / district | Test call |
| 4 | **Ambulance** (if a local number exists beyond 119) | `name_kh`, `phone_numbers` | Health center | Test call |
| 5 | **Commune health center** | `name_kh`, `phone`, `hours_kh`, `is_24h`, `maps_url` | Health center / HDX-OSM as starting point | Test call + confirm hours |
| 6 | **2–3 referral/national hospitals** (the ones residents actually go to) | `name_kh`, `phone` (emergency desk, not admin office), `is_24h`, `maps_url`, `sort_order` | Clerk + health center | Test call to the emergency desk |
| 7 | **Telegram group/channel ID** | `telegram_group_id`, `chat_type` (group / channel) | Captured by `/bind` | Bot posts a test message |
| 8 | **At least 1 admin** (ideally 2, so one absence doesn't stop posting) | `telegram_user_id`, `full_name`, `role` | Captured by admin invite link | Admin sends a test announcement |
| 9 | **Seed announcements** (2–3 real ones) | text / photo / voice | Clerk | So the feed isn't empty on day one |

> **Every contact row also carries:** `source` (who told you), `verified_at`, `verified_by`, `is_active`. Re-verify **monthly** for emergency + health, **quarterly** for everything else.

### 3.3 Public service guides (P1 — top 3, chosen by the clerk)

Per service:

| Field | Example | Notes |
| :--- | :--- | :--- |
| `title_kh` | សំបុត្រកំណើត | |
| `required_docs_kh` | Bulleted checklist (max ~6 items) | Plain words; no legal references |
| `fee_khr` + `fee_conditions_kh` | "ឥតគិតថ្លៃ បើចុះក្នុងរយៈពេល… / … រៀល បើយឺត" | Fees often depend on conditions |
| `processing_time_kh` | "១ ថ្ងៃ" | |
| `where_kh` + `office_level` | Commune hall / commune police post / district office / OWSO | Widen the schema check (see §4) |
| `who_must_come_kh` | "ឪពុក ឬម្តាយ ត្រូវមកផ្ទាល់" | Most common reason for wasted trips |
| `verified_by`, `verified_at` | Clerk name, date | |

### 3.4 Bot copy (Khmer text you must write and test)

This is data too, and it is the part older users actually see:

* Welcome message (2 lines) + optional 15s voice welcome
* 5 button labels (§2.2)
* Emergency card layout (national block + local block)
* "Didn't understand" fallback line
* Admin prompts: send content / preview / published / deleted / error ("bot isn't an admin in the group")
* Keyword list (~30 words + common misspellings seen during testing)

Have 2 native speakers review, then test with 3–5 older adults (PRD Week 5).

### 3.5 Usage data the bot records (for KPIs, no PII)

| Event | Fields |
| :--- | :--- |
| `start` | `commune_code`, `via` (deep_link / picker / announcement_button), timestamp |
| `menu_tap` | `commune_code`, `button`, `latency_ms` |
| `keyword_match` / `keyword_miss` | `commune_code`, `intent` (**not** the raw text) |
| `announcement_published` / `deleted` | `commune_code`, `admin_id`, `content_type` |

Exception: log a misspelled keyword **only** in aggregate form during the Week 5 test so you can improve the keyword list. Never store free text in production logs.

---

## 4. Schema Changes Implied

```sql
-- communes: Khum vs Sangkat wording
ALTER TABLE communes ADD COLUMN commune_type VARCHAR(10) CHECK (commune_type IN ('khum','sangkat'));

-- commune_configs: group OR channel
ALTER TABLE commune_configs ADD COLUMN chat_type VARCHAR(10) NOT NULL DEFAULT 'group'
    CHECK (chat_type IN ('group','channel'));

-- local_contacts: provenance + freshness
ALTER TABLE local_contacts
    ADD COLUMN source      TEXT,
    ADD COLUMN verified_at TIMESTAMPTZ,
    ADD COLUMN verified_by VARCHAR(150),
    ADD COLUMN is_active   BOOLEAN NOT NULL DEFAULT TRUE;
-- also: allow a nationwide row (commune_code NULL) for 117/118/119 short codes,
-- or move short codes into their own small table.

-- public_services: realistic office levels + conditions
ALTER TABLE public_services
    DROP CONSTRAINT public_services_office_level_check,
    ADD CONSTRAINT public_services_office_level_check
        CHECK (office_level IN ('commune_hall','commune_police','district_office','district_owso')),
    ADD COLUMN fee_conditions_kh TEXT,
    ADD COLUMN who_must_come_kh  TEXT,
    ADD COLUMN verified_at       TIMESTAMPTZ,
    ADD COLUMN verified_by       VARCHAR(150);

-- announcements: expiry + events + archived-from-forward
ALTER TABLE announcements
    ADD COLUMN event_date DATE,
    ADD COLUMN expires_at TIMESTAMPTZ,
    ADD COLUMN source     VARCHAR(20) NOT NULL DEFAULT 'announce'
        CHECK (source IN ('announce','forwarded'));

-- admin invite tokens
CREATE TABLE admin_invites (
    token        VARCHAR(64) PRIMARY KEY,
    commune_code VARCHAR(10) NOT NULL REFERENCES communes(commune_code),
    created_by   BIGINT NOT NULL,
    used_by      BIGINT,
    expires_at   TIMESTAMPTZ NOT NULL,
    used_at      TIMESTAMPTZ
);
```

Drop `villages` from the MVP migration (add it back in Phase 2).

---

## 5. Adjusted 6-Week Plan

| Week | Focus | Exit criteria |
| :--- | :--- | :--- |
| **0** (before coding) | Commune partnership + confirm group/channel + name the clerk as content owner | Written/verbal OK from the commune chief; clerk agrees to post ≥2×/week |
| **1** | **Tap-to-call device spike** (Android + iOS, short codes vs. `+855` vs. `sendContact`) + start data collection (§3.2) | Chosen phone-number format proven on real devices |
| **2** | Data verification (all test calls) + top-3 service guides signed off + Khmer copy draft | All P0 rows have `verified_at` |
| **3–4** | Build: binding, keyboard, directory views, announce/forward/delete, admin invite, `/bind`, keyword fallback | Works end-to-end in a test group |
| **5** | Test with 3–5 older adults + 1–2 real clerks posting | ≥85% find emergency number in <15s; clerk publishes without help |
| **6** | Launch in 1 commune (add 2nd/3rd only after 2 stable weeks) | Pinned link posted; first 3 real announcements in feed |

---

## 6. RAG Decision (checked against `E:\KAI_AI`, 2026-11-21)

**No RAG in the MVP/demo.** The bot's data is ~30 structured rows, and its most important answers are phone numbers that must be exactly right. Generated answers add the risk of a wrong number for no gain, and older users mostly tap buttons anyway. KAI_AI's stack (Qdrant + BGE-M3 + reranker + gateway + OpenClaw/Ollama) is also far heavier than a $15/month single-container bot.

**Reuse from KAI_AI now:** the Khmer normalizer from `shared/kai_khmer` (stdlib-only, tiny rules file; the 2.8 MB dictionary/tokenizer is not needed). In testing it fixed typing variants that plain substring matching misses: deprecated `ឣ` → `អ` (so `ឣត្តសញ្ញាណប័ណ្ណ` matches the services keyword), and split vowels `េ`+`ា` → `ោ`. Copy the files into this repo; don't `pip install -e` KAI_AI's `shared/` (that writes build metadata into KAI_AI).

**Phase 2 option:** when the keyword matcher misses, forward the question to KAI's gateway (`POST /api/v1/chat/query`, `channel=telegram`) over an ingested corpus of announcements + service guides, with citations. Hard rule: phone numbers and addresses are always answered from the database, never from generated text.

---

## 7. Open Questions for You

1. Do you already have a pilot commune that has agreed, and does it use a Telegram **group**, **channel**, or Facebook page?
2. Will commune staff post announcements themselves, or will you (or a volunteer) post for them at first?
3. Is the pilot urban (សង្កាត់, e.g., Phnom Penh) or rural (ឃុំ)? This changes which emergency numbers and hospitals apply, and how far away they are.
4. Who will re-check phone numbers each month after launch? This needs a named person, not "the system".
