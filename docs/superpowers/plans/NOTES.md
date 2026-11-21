# Build notes & pending manual checks

Built unattended on 2026-11-21. Everything that needs a real bot token or a phone is listed here — do these first when you sit down with the bot.

## Pending manual checks (need BOT_TOKEN + phones)

- [ ] **Task 1 step 9 — phone links.** `.venv\Scripts\python scripts/phone_check.py`; on Android + iOS note which of `117`, `023 426 948`, `023426948`, `+855 23 426 948`, `012 786 693` are tappable. If spaced local numbers are NOT tappable, change `format_phone()` in `sangkat_bot/formatting.py` to the format that is, and update its test.
- [ ] **Task 6 step 6 — resident flow** on a real phone (deep link, 5 buttons, typed `ភ្លើង`, sticker, `/start` from a fresh account → picker).
- [ ] **Task 7 step 4 — clerk flow** (text + flyer + voice → preview → publish → group; resident 📢; `/delete_last`; sticker at photo step; skip all; publish before `/bind`).
- [ ] **Task 8 step 4 — `/bind 120101`** in the test group (bot is group admin) → confirmation + pinned onboarding message.
- [ ] **Task 9 — live resilience + full run-sheet** (`docs/demo-runsheet.md`) end-to-end.

- [ ] **Test-call 012 496 065** (Tonle Bassac administrative police post, from a 2020 brochure) before filming the 🚨 card. If it's wrong, set its `phone_numbers` empty in `data/seed/local_contacts.csv` and re-seed.

## Khmer wording to review
(Add anything that reads oddly during the manual checks.)
