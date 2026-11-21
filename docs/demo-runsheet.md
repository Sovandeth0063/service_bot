# Demo video run-sheet (2–3 minutes)

For whoever records the shortlist video. Judges are **non-technical and technical**, so show the experience first, then 30 seconds of how it's built.

## Before recording

- [ ] `.venv\Scripts\python -m sangkat_bot.seed` then `.venv\Scripts\python -m sangkat_bot` — leave the terminal open (it is also a shot later).
- [ ] The test group is bound (`/bind 120101`) and the **pinned** welcome message is visible at the top.
- [ ] Resident phone: **large font** (Telegram → Settings → Chat settings → text size), Do-Not-Disturb on, battery > 50 %, chat with the bot **cleared**.
- [ ] Clerk phone: logged in as a clerk or super-admin (`/clerks` shows ✅). With the AI helper on (`ANTHROPIC_API_KEY` in `.env`), have one line of rough notes ready to paste, e.g. *vaccine kids sat 5 dec 8am to 11am at sangkat hall bring health book*. Without it: a sample **flyer image** and a **15–30 s Khmer voice note**.
- [ ] Do one full dry run, then `/delete_last` so the group starts clean.
- [ ] Screen recording on both phones (or film them with a second phone, steady and well lit).

## Shot list

### 1. The problem (10 s)
A busy commune group: an official notice buried under chat. Voice-over: older residents can't find it, can't search, struggle to type Khmer.

### 2. Resident story (≈ 60 s) — *non-technical judges*
1. In the group, tap the **pinned 📱 សួរជំនួយការ** button → the bot opens already set to **សង្កាត់ទន្លេបាសាក់**. No menus, no typing.
2. Show the **five big buttons** at the bottom; they never move.
3. Tap **🚨 សង្គ្រោះបន្ទាន់** → national 117 / 118 / 119 / 666 plus the nearest fire brigade, police and 24-hour hospitals → **tap a number → the phone dialer opens**.
4. Tap **📍 សាលាសង្កាត់** → hours, address and a **map pin** to show a tuk-tuk driver.
5. Type **ភ្លើង** (fire) instead of tapping → the emergency card still appears.

### 3. Clerk story (≈ 45 s)
1. Clerk opens the bot privately → **📝 ផ្សាយដំណឹង**.
2. **AI helper on:** pastes one messy line of notes → **⏳** → the preview arrives as a **flyer + clean Khmer text + voice note + 📍 map button**. (Optional, if time allows: leave out the end time, show the **❓** question, answer with **✏️ កែ**.) Taps **✅ ទន្លេបាសាក់**.
   **AI helper off:** sends the text → the **flyer** → a **voice note** → preview → **✅ ទន្លេបាសាក់**.
3. Cut to the group: the flyer with the text underneath, the **📱** and **📍** buttons, and the voice note right below it.
4. Resident taps **📢 ដំណឹងថ្មី** → the same post plays in the bot: read it, look at it, or **listen to it**.

### 4. Under the hood (≈ 30 s) — *technical judges*
Show the terminal / code briefly while saying:
- Built on **official DataEF data**: all **1,661 communes** load with their government codes. Adding a commune means adding data rows. No code changes.
- **Every phone number has a source and a verification status**. Missing ones say "កំពុងផ្ទៀងផ្ទាត់" (being verified). The bot never guesses a number, and no AI writes phone numbers.
- **The AI helper only rewrites what the clerk typed**: one Claude call returns the text, the speech script and the flyer fields. It never invents a date or time, and asks when something is missing. The clerk approves every post.
- **Only approved clerks can post**, each for their own sangkat. Super-admins add them by Telegram username (`/addclerk @name 120101`), and the role is locked to the account.
- **Khmer typing is forgiving**: invisible spaces, old letters (`ឣ` → `អ`) and split vowels are normalized before matching.
- Logs store **no personal messages**. Residents' data is just their Telegram id + commune.
- `pytest` → **all tests green**, including full resident and clerk flows run against a simulated Telegram.

### 5. Close (10 s)
"One link in the group. Five big buttons. News you can read, see, or hear."

## Don't show
- Cards for places whose phone says **កំពុងផ្ទៀងផ្ទាត់** (Preah Ang Duong, Koh Pich fire…). Stick to the **🚨** card and Calmette.
- The demo-data notice at the bottom of the cards is fine to show, since it's honest. Don't zoom in on it.
