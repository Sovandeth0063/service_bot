# How residents use the bot (user flow)

This guide is for **residents**: anyone living in the sangkat.
They don't need to type or know any commands. **Everything is done by tapping big buttons.**

---

## 1. Getting in (first time)

**The easy way: from the sangkat group**

1. Open the sangkat's Telegram group.
2. Tap a **📱 សួរជំនួយការ** button. You'll find one:
   - in the bot's **welcome message** when you join the group;
   - in the **pinned message** at the top (tap the pinned line to jump to it);
   - under every **news post**;
   - or tap **Menu → /help** in the group, and the bot replies with one.
3. Telegram opens the bot. Tap **ចាប់ផ្តើម (Start)**.
4. Done! The bot already knows your sangkat and shows the big buttons.

> The big buttons appear only in the **private chat with the bot**, never inside the group.
> That is how Telegram works. The group is only the doorway.

**Found the bot another way** (search, a friend shared it…)

1. Tap **Start**.
2. The bot asks **សូមជ្រើសរើសសង្កាត់របស់អ្នក៖** (choose your sangkat).
3. Tap your sangkat, for example **ទន្លេបាសាក់ (ចំការមន)**.
4. The big buttons appear.

The bot remembers your choice, so you only do this once.

---

## 2. The five big buttons

They sit at the bottom of the screen and never move.

```
┌─────────────────────────────┐
│      🚨 សង្គ្រោះបន្ទាន់       │
├──────────────┬──────────────┤
│ 🏥 មន្ទីរពេទ្យ  │ 📢 ដំណឹងថ្មី   │
├──────────────┼──────────────┤
│ 📄 សេវាឯកសារ  │ 📍 សាលាសង្កាត់ │
└──────────────┴──────────────┘
```

| Button | What you get |
| :--- | :--- |
| **🚨 សង្គ្រោះបន្ទាន់** (emergency) | Police **117**, fire **118**, ambulance **119**, Phnom Penh fire **666**, plus the nearest police post, fire station and 24-hour hospitals. **Tap a number to call it straight away.** |
| **🏥 មន្ទីរពេទ្យ** (hospitals) | Nearby hospitals and health centers: opening hours, phone, and a map link. |
| **📢 ដំណឹងថ្មី** (news) | The 3 newest announcements from the sangkat. Each one has **text to read, a picture to look at, and a voice note to listen to ▶️**. If the news happens somewhere, tap **📍 មើលទីតាំងលើផែនទី** to open the place in Google Maps. |
| **📄 សេវាឯកសារ** (documents) | Pick a service and see the papers to bring, the fee, where to go and how long it takes: <br>• សំបុត្រកំណើត (birth certificate) <br>• លិខិតបញ្ជាក់ទីលំនៅ (residence certificate) <br>• សៀវភៅស្នាក់នៅ / សៀវភៅគ្រួសារ (residence / family book) |
| **📍 សាលាសង្កាត់** (sangkat hall) | Office days and hours, address, and a **map pin** you can open in Google Maps or show a tuk-tuk driver. |

---

## 3. Typing works too (optional)

If someone prefers typing, short Khmer words work:

| Type | Same as |
| :--- | :--- |
| ភ្លើង, ឆេះ, ប៉ូលីស, ចោរ | 🚨 emergency |
| ពេទ្យ, ឈឺ | 🏥 hospitals |
| ដំណឹង, ព័ត៌មាន | 📢 news |
| សំបុត្រកំណើត, ឯកសារ | 📄 documents |
| ទីតាំង, ផែនទី, ម៉ោង | 📍 sangkat hall |

If the bot doesn't understand, it politely says so and points back to the buttons.

---

## 4. Getting help

- Tap **Menu → /help** (or type `/help`). The bot shows a step-by-step guide to every button.
- **Buttons disappeared?** Tap the **⌨️** icon next to the typing box.
- Stickers, photos or voice messages sent to the bot get a reply pointing back to the buttons. The bot only answers buttons and short words.

---

## 5. Where news comes from

1. A sangkat clerk posts the news (see `docs/clerk-guide.md`).
2. It appears in the **sangkat group**, with a **📱** button under it that opens the bot, and a **📍** map button when there's a place.
3. It is also saved in the bot under **📢 ដំណឹងថ្មី**, so people who missed it in the busy group can still find it later.

---

## Good to know

- **Free.** It only uses Telegram.
- **Private.** The bot only stores your Telegram ID and your sangkat. It never stores what you type.
- **Phone numbers marked "កំពុងផ្ទៀងផ្ទាត់"** (being verified) don't have a confirmed number yet. The bot never guesses a number.
- **Demo:** every card ends with a "test data" note. Numbers should be checked before real use.

---

## Quick card

```
Group → 📱 button (welcome, pinned, news, or Menu → /help) → Start
   (or: Start → pick your sangkat)

🚨 emergency   → tap a number to call
🏥 hospitals   → hours, phone, map
📢 news        → read · look · listen ▶️ · 📍 map
📄 documents   → what to bring
📍 hall        → hours + map pin

Help → Menu → /help
```
