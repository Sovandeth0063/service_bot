# Product Requirements Document (PRD)
## Centralized Commune Public Service & Announcement Telegram Chatbot

| Field | Details |
| :--- | :--- |
| **Project Name** | SangkatConnect (ជំនួយការឃុំ-សង្កាត់) — Working Title |
| **Document Version** | 1.0 (MVP Scope) |
| **Target Platform** | Telegram Bot API (Group Integration + Private Chat Assistant) |
| **Target Pilot Scope** | 1 to 3 Pilot Communes / Sangkats in Cambodia |
| **Primary Data Backbone** | DataEF (`data.mef.gov.kh`) 2025 Administrative Hierarchy (CSV) |

---

## 1. Executive Summary & Problem Statement

### The Problem
Local Commune and Sangkat offices in Cambodia increasingly use Telegram groups to communicate with residents. However, two major friction points limit their effectiveness:
1. **Buried Announcements:** Official notices, community events, vaccination drives, and utility outages get lost quickly under daily group chatter, making it hard for residents to find verified updates.
2. **High Friction for Low-Digital-Literacy Users:** Older adults and residents with limited digital skills struggle to search chat histories, navigate government websites, or type accurate Khmer queries on mobile keyboards when they urgently need a hospital phone number, fire emergency contact, or civil registration checklist.

### The Solution
A **commune-bound Telegram chatbot** that serves each Commune/Sangkat Telegram group as a centralized information hub. Verified local admins broadcast announcements through the bot (automatically archiving them into a clean feed), while residents access emergency numbers, health facilities, and public service guides in **1 to 2 taps** using large, permanent Khmer buttons—with zero typing required.

---

## 2. Target Users & Personas

### 2.1 Primary Resident Persona — Older Adult / Low Digital Literacy
* **Profile:** Age 50–75+, owns an Android or iOS smartphone, uses Telegram primarily to receive voice notes, photos, and calls from family members.
* **Pain Points:** Small text, English menus, slash commands (`/start`, `/help`), typing Khmer Unicode accurately, getting lost in multi-step inline menus.
* **Key Needs:** Instant access to tap-to-call emergency numbers (fire, police, ambulance, hospital), clear voice/image announcements, and a familiar, unchanging button layout.

### 2.2 Secondary Resident Persona — Working Adult / Household Representative
* **Profile:** Age 25–50, handles family administrative paperwork (birth certificates, residence books, ID renewals).
* **Pain Points:** Making wasted trips to the Sangkat Hall because of missing documents or unclear office hours and fees.
* **Key Needs:** Accurate checklists of required documents, official government fees, processing times, and a Google Maps link to the Sangkat Hall or District OWSO.

### 2.3 Operational Persona — Commune / Sangkat Admin
* **Profile:** Commune clerk, Sangkat officer, or authorized village representative.
* **Pain Points:** No time to learn a complex web CMS; needs to publish urgent updates directly from a smartphone.
* **Key Needs:** A guided, mistake-proof Telegram flow (with preview and confirmation) to broadcast text, flyer images, or voice announcements to their commune group.

### 2.4 System Persona — Platform Super Admin
* **Profile:** Project developer or system maintainer.
* **Key Needs:** Easy onboarding of new communes keyed by DataEF's official `commune_code`, bulk CSV updates, and admin whitelist management.

---

## 3. UX & Accessibility Principles (Non-Negotiable for MVP)

Every interface decision must optimize for older adults with low digital literacy:

1. **Zero-Setup Onboarding via Group Deep Links:** Each commune Telegram group pins a single message with a deep link (`https://t.me/YourBot?start=<commune_code>`). Tapping it opens the bot already bound to that resident's commune—no province/district/commune picker required on first launch.
2. **Persistent Bottom Reply Keyboard (No Inline Maze):** Use Telegram's permanent bottom **Reply Keyboard** with 5 large Khmer buttons paired with clear emojis. Unlike inline buttons that scroll out of view, the Reply Keyboard remains anchored at the bottom of the screen.
3. **One-Tap Phone Calling:** Format all phone numbers cleanly (e.g., `118`, `012 345 678`) with no distracting symbols inside the digits so Telegram automatically renders them as blue tap-to-call links.
4. **Voice & Visual First Announcements:** Allow admins to attach a photo flyer or a short Khmer voice message (`sendVoice`) alongside or instead of long blocks of text.
5. **Forgiving Free-Text Fallback:** Never respond with "Invalid command." If a user accidentally types a message, run lightweight Khmer keyword matching; if no match is found, gently show a short Khmer prompt pointing back to the bottom buttons.

---

## 4. MVP Scope Definition

| Capability | In Scope (MVP — Pilot 1–3 Communes) | Out of Scope (Phase 2 / V2) |
| :--- | :--- | :--- |
| **Commune Binding** | Group-to-`commune_code` mapping + pinned deep link onboarding + manual commune switch fallback | GPS "Share Location" point-in-polygon detection using DataEF GeoJSON |
| **Resident Menu** | 5-button persistent Khmer Reply Keyboard (Emergency, Health, Announcements, Services, Hall Location) | Multi-language switcher (English/Chinese), personalized village alerts |
| **Announcements** | Admin posts text, photo, or voice note via bot -> posts to group -> saves to "Latest 5 Announcements" feed | Scheduled posts, draft approval workflows, read-receipt analytics |
| **Emergency Contacts** | National short codes (`117`, `118`, `119`, `115`) + verified local fire, police, ambulance, and nearest 24/7 hospital | Live GPS dispatch, SOS button, SMS fallback alerts |
| **Public Services** | Top 5 civil registration guides (documents, official OWSO fees, processing days, office hours, Maps pin) | Online form filling, document uploads, KHQR fee payment |
| **Search / Q&A** | Lightweight Khmer keyword matcher (e.g., "ភ្លើង", "ពេទ្យ", "សំបុត្រកំណើត") | LLM/RAG conversational AI, Khmer speech-to-text voice queries |
| **Admin Portal** | Telegram-native `/announce` flow restricted by `telegram_user_id` whitelist + Google Sheet / CSV seed loader | Full web-based CMS dashboard and ministry multi-tier RBAC |

---

## 5. Functional Requirements

### FR-01: Commune Group Binding & Resident Onboarding
* **User Story:** As an older resident in my Sangkat's Telegram group, I want to tap one pinned link to open the chatbot so I immediately get information for my local area without selecting provinces or districts.
* **Acceptance Criteria:**
  * Every onboarded commune is mapped 1-to-1 to its official DataEF `commune_code` and `telegram_group_id`.
  * Tapping `https://t.me/<BotUsername>?start=<commune_code>` stores `(telegram_user_id, commune_code)` in the database and displays a warm 2-line Khmer welcome message confirming the commune name plus the persistent Reply Keyboard.
  * If a user opens the bot directly without a deep link, the bot prompts them to select from the currently active pilot communes via large buttons.

### FR-02: Persistent Khmer Main Menu
* **User Story:** As a low-digital-literacy user, I want big, recognizable Khmer buttons always visible at the bottom of my screen so I never have to type commands.
* **Acceptance Criteria:**
  * The persistent Reply Keyboard displays the following 5 buttons (`resize_keyboard=True`, `is_persistent=True`):
    * `🚨 លេខសង្គ្រោះបន្ទាន់` (Emergency Contacts)
    * `🏥 មន្ទីរពេទ្យ និងមណ្ឌលសុខភាព` (Hospitals & Health Centers)
    * `📢 ដំណឹង និងកម្មវិធីថ្មីៗ` (Latest Announcements & Events)
    * `🏛️ សេវាសាធារណៈឃុំ/សង្កាត់` (Commune Public Services)
    * `📍 ទីតាំងសាលាឃុំ/សង្កាត់` (Commune Hall Location & Hours)

### FR-03: One-Tap Emergency Contacts
* **User Story:** As a resident facing a fire, crime, or medical emergency, I want to tap once and immediately call the right hotline or local station.
* **Acceptance Criteria:**
  * Tapping `🚨 លេខសង្គ្រោះបន្ទាន់` returns a single concise message within 1.5 seconds containing:
    * National short codes: Police (`117`), Fire (`118` / `666` in Phnom Penh), Ambulance (`119`), MoH (`115`).
    * Verified local contacts bound to the user's `commune_code`: Sangkat Police Post, District Fire Unit, and nearest 24/7 emergency hospital.
  * All phone numbers are formatted cleanly for native tap-to-call on both iOS and Android Telegram clients.

### FR-04: Hospitals & Health Centers Directory
* **User Story:** As an older resident needing medical care, I want to see the nearest Commune Health Center and referral hospitals with hours, phone numbers, and directions.
* **Acceptance Criteria:**
  * Displays the local Commune Health Center first, followed by 2–4 nearest referral or national hospitals.
  * Each entry includes: Khmer name, operating hours (e.g., 24/7 or 07:30–17:00), tap-to-call phone number, and a clickable Google Maps URL.

### FR-05: Centralized Announcements & Events Feed
* **User Story (Admin):** As a Commune Admin, I want to send an announcement (text, flyer image, or voice note) through the bot so it posts cleanly to our Telegram group and stays searchable for residents.
* **User Story (Resident):** As a resident, I want to tap one button to read or listen to the 5 most recent official commune announcements without scrolling through group chat messages.
* **Acceptance Criteria:**
  * Whitelisted admins initiate `/announce` in private chat with the bot.
  * The bot accepts a text message, a photo with caption, or a voice note, then renders a formatted preview with `[✅ បញ្ជូន / Publish]` and `[❌ បោះបង់ / Cancel]` buttons.
  * Upon confirmation, the bot posts the announcement to the commune's Telegram group with an official header (`📢 ដំណឹងពីសង្កាត់/ឃុំ [Commune Name]`) and saves the record (including Telegram `file_id` for media) in the database.
  * Residents tapping `📢 ដំណឹង និងកម្មវិធីថ្មីៗ` receive the latest 5 active announcements ordered newest-first, replaying any attached photo or voice note natively.

### FR-06: Top 5 Public Service Guides
* **User Story:** As a citizen preparing to visit the Sangkat Hall, I want to check required documents, official fees, and processing times ahead of time.
* **Acceptance Criteria:**
  * Tapping `🏛️ សេវាសាធារណៈឃុំ/សង្កាត់` shows a simple list of the top 5 resident services:
    1. Birth Certificate (`សំបុត្រកំណើត`)
    2. Residence Book (`សៀវភៅស្នាក់នៅ`)
    3. Family Book (`សៀវភៅគ្រួសារ`)
    4. National ID Referral / Verification (`បញ្ជាក់អត្តសញ្ញាណប័ណ្ណ`)
    5. Marriage / General Administrative Certification (`សំបុត្រអាពាហ៍ពិពាហ៍ / លិខិតបញ្ជាក់ផ្សេងៗ`)
  * Selecting any service displays: Required documents checklist, official government fee (in KHR), expected processing duration, and where to submit (Sangkat Hall vs. District OWSO).

### FR-07: Commune Hall Location & Hours
* **User Story:** As a resident, I want to check when the Sangkat Hall is open, call the front desk, or hand my phone to a tuk-tuk/PassApp driver with the map pin.
* **Acceptance Criteria:**
  * Returns Sangkat Hall name, official working days/hours, tap-to-call phone number, physical address in Khmer, and a direct Google Maps link.

### FR-08: Lightweight Khmer Keyword Fallback
* **User Story:** As a resident who types a short word instead of pressing a button, I still want to get the right phone number or guide.
* **Acceptance Criteria:**
  * Free-text messages are normalized (stripping Khmer zero-width spaces `\u200b`) and checked against a keyword map (e.g., `ភ្លើង`, `អគ្គិភ័យ` -> Emergency; `ពេទ្យ`, `ឈឺ`, `សុខភាព` -> Health; `កំណើត`, `សៀវភៅ`, `អត្តសញ្ញាណ` -> Public Services).
  * Unmatched messages return a polite 1-line Khmer prompt reminding the user to tap any button below.

---

## 6. Data Requirements & Sources

### Tier 1: Official Geographic Backbone (DataEF Static CSVs)
Imported once during setup and updated annually:
* **Cambodia Province List 2025** (`data.mef.gov.kh/datasets/pd_66a8603700604c000123e144`)
* **Cambodia District List 2025** (`data.mef.gov.kh/datasets/pd_66a8603800604c000123e145`)
* **Cambodia Commune List 2025** (`data.mef.gov.kh/datasets/pd_66a8603900604c000123e146`)
* **Cambodia Villages List 2025** *(Optional for MVP)* (`data.mef.gov.kh/datasets/pd_66a8603a00604c000123e147`)

### Tier 2: Seed Reference Directories
* **National Emergency Short Codes:** Telecommunication Regulator of Cambodia (`trc.gov.kh/en/resources/emergency-numbers/`)
* **Health Facility Baseline:** HDX / OpenStreetMap Cambodia Health Facilities (`data.humdata.org/dataset/hotosm_khm_health_facilities`) and Open Development Cambodia NSSF Health Facilities (`data.opendevelopmentcambodia.net/dataset/health-facilities-nssf`)
* **Public Service Procedures & Fees:** Ministry of Interior OWSO Guidelines (`owso.gov.kh`)

### Tier 3: Pilot-Verified Local Data (Per Onboarded Commune)
Before activating any commune, a maintainer must manually verify and populate:
* 1 Sangkat/Commune Hall record (phone, hours, Google Maps URL, Telegram Group ID)
* 1 Local Police Post & 1 Fire Response contact
* 1 Local Health Center + 2–3 nearest Referral/National Hospitals
* At least 1 whitelisted Commune Admin Telegram `user_id`

---

## 7. Non-Functional Requirements (NFRs)

* **Latency:** Resident menu taps must return a response in under 1.5 seconds (95th percentile).
* **Availability:** Target 99.5% uptime; emergency contact lookups rely strictly on local database reads with zero third-party runtime API dependencies.
* **Security & Governance:** Only explicitly whitelisted `telegram_user_id` accounts mapped to a specific `commune_code` can broadcast to that commune's group. All broadcasts and deletions are logged to an immutable audit table.
* **Privacy:** Minimize PII collection—store only `telegram_user_id`, bound `commune_code`, and timestamps. Never collect resident phone numbers, home addresses, or National ID numbers in MVP.
* **Localization:** Full UTF-8 Khmer Unicode support with concise, plain-spoken Khmer phrasing (avoiding heavy bureaucratic jargon where simple words exist).

---

## 8. Success Metrics & Pilot KPIs

| Metric | Target (First 30 Days of Pilot) | Measurement Method |
| :--- | :--- | :--- |
| **Older-Adult Usability Pass Rate** | >= 85% find emergency/hospital number in under 15s without help | Moderated test with 5 older adults (age 55+) prior to launch |
| **Resident Activation Rate** | >= 25% of pilot Telegram group members tap the pinned deep link | Unique `users` rows / Total group member count |
| **Core Utility Engagement** | >= 30 weekly lookups across Emergency, Health, and Services | Bot interaction event logs (anonymized by menu button) |
| **Admin Adoption** | >= 2 official announcements published per week per pilot commune | `announcements` table count |
| **Contact Data Accuracy** | 100% of listed phone numbers verified working before launch | Pre-launch test call checklist |

---

## 9. Pilot Rollout Roadmap (6 Weeks)

* **Weeks 1–2 (Foundation & Data):** Set up database schema, run DataEF CSV ingestion script, and manually verify contacts + OWSO top-5 service guides for 1 pilot commune.
* **Weeks 3–4 (MVP Engineering):** Build webhook server, deep-link onboarding, persistent Khmer Reply Keyboard, tap-to-call directory views, keyword fallback, and admin `/announce` broadcast FSM.
* **Week 5 (Accessibility Usability Testing):** Test the live bot on real phones with 3–5 older adults (family/neighbors). Observe hesitations, shorten Khmer labels, and refine message spacing.
* **Week 6 (Pilot Launch):** Add bot as an admin to 1–3 pilot commune Telegram groups, pin the onboarding deep-link message, train commune admins (10-minute walkthrough), and monitor logs.