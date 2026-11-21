# Super-admin guide: set up, demo and run the bot

This guide is for the person who **runs the bot**. It takes you from an empty computer to a working
demo, step by step. No coding is needed: you copy and paste a few commands.

| Who | What they can do |
| :--- | :--- |
| **Super-admin** (you) | Run the bot. Post news for any sangkat, or all of them at once. Add and remove clerks |
| **Clerk** | Post news for **their own sangkat only**. Guide: [`clerk-guide.md`](clerk-guide.md) |
| **Resident** | Tap the 5 big buttons; read, look at and listen to the news. Guide: [`resident-guide.md`](resident-guide.md) |

**Contents**
1. [What you need](#1-what-you-need)
2. [Install (one time, about 15 minutes)](#2-install-one-time-about-15-minutes)
3. [Fill in the settings file](#3-fill-in-the-settings-file-env)
4. [Start the bot](#4-start-the-bot)
5. [Make yourself super-admin](#5-make-yourself-super-admin)
6. [Link the sangkat Telegram group](#6-link-the-sangkat-telegram-group)
7. [Add a clerk](#7-add-a-clerk)
8. [Run the demo (10 minutes)](#8-run-the-demo-10-minutes)
9. [Managing clerks](#9-managing-clerks)
10. [The AI helper](#10-the-ai-helper)
11. [Every day: start, stop, restart](#11-every-day-start-stop-restart)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. What you need

- [ ] A **Windows laptop** that stays on and online during the demo. The bot runs on it.
- [ ] **Python 3.12 or newer** from <https://www.python.org/downloads/>. In the installer, tick
      **"Add python.exe to PATH"**.
- [ ] **Microsoft Edge or Google Chrome.** Edge comes with Windows; the AI helper uses it to draw flyers.
- [ ] The **project folder**: on GitHub (<https://github.com/Sovandeth0063/service_bot>) click
      **Code → Download ZIP**, or `git clone` it.
- [ ] The **bot token**: either ask the team owner for the existing bot's token, or make your own test bot
      (see [section 3](#3-fill-in-the-settings-file-env)).
- [ ] *Optional:* a **Claude API key** for the AI helper (from <https://console.anthropic.com>).
- [ ] **Telegram accounts for the demo**, each with a username (Telegram → Settings → Username):
  - you (super-admin);
  - a second account for the **clerk**;
  - optionally a third account for the **resident** (you can also play the resident yourself).
- [ ] A **Telegram group** that stands in for the sangkat group.

> ⚠️ **Only one computer may run the same bot at a time.** If two computers start the same bot token, they
> fight over messages and both misbehave. Agree who runs it, or give each person their own test bot.

---

## 2. Install (one time, about 15 minutes)

1. Put the project in a **short folder path**, for example `C:\service_bot`.
   Not on the Desktop or deep inside Downloads: Windows can't install one of the libraries when the
   path is too long.
2. Open the folder, click the address bar, type `powershell` and press **Enter**. A blue window opens
   in that folder.
3. Copy and paste these lines **one at a time**, pressing Enter after each:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev,ai]"
copy .env.example .env
```

- The first line makes a private Python just for this project.
- The second installs everything, including the AI helper. It takes a few minutes.
- The third creates your settings file, which you fill in next.

---

## 3. Fill in the settings file (`.env`)

Open `.env` in Notepad: right-click → Open with → Notepad. Fill in these lines:

| Line | What to put |
| :--- | :--- |
| `BOT_TOKEN=` | The bot's token. **Existing bot:** ask the team owner. **Your own test bot:** in Telegram, message **@BotFather**, send `/newbot`, follow the steps, and paste the token it gives you |
| `ADMIN_USERNAMES=` | Your Telegram username **without the @**, e.g. `ADMIN_USERNAMES=sovandeth_hour`. Several people: separate them with commas |
| `ANTHROPIC_API_KEY=` | *Optional.* Your Claude key (`sk-ant-…`) to turn on the AI helper. Leave empty to post by hand |
| `ADMIN_USER_IDS=` | Leave empty. An older way to name super-admins by number |
| `DEMO_COMMUNE_CODE`, `DB_PATH`, `DEMO_MODE` | Leave as they are |

Save the file.

> 🔒 `.env` holds secrets (the token and the key). Never send it in a chat or upload it. It is never put on GitHub.

Then load the sangkat data, one time:

```powershell
.venv\Scripts\python -m sangkat_bot.seed
```

It prints a short table, ending with lines such as `commune_configs  5`.

---

## 4. Start the bot

```powershell
.venv\Scripts\python -m sangkat_bot
```

When you see **`Start polling`**, the bot is live. **Leave this window open**: closing it stops the bot.
To stop it on purpose, click the window and press **Ctrl + C**.

> Using your own test bot? Its name is whatever you chose at @BotFather. Wherever this guide says
> **@kh_svc_desk_x7_bot**, use your bot's name instead.

---

## 5. Make yourself super-admin

1. In Telegram, open **@kh_svc_desk_x7_bot** and press **Start** (or send `/start`).
2. The bot replies **"✅ អ្នកជាអ្នកគ្រប់គ្រងធំ…"** (you are the super-admin).
3. Pick a sangkat if asked. The big buttons appear, including **📝 ផ្សាយដំណឹង** (post news).
4. Tap **Menu** (bottom left). You'll see the super-admin commands **/clerks**, **/addclerk** and **/removeclerk**.

The ✅ message comes only the **first time**. Later, the /clerks command in the menu shows you're still super-admin.
No ✅ message and no /clerks? See [Troubleshooting](#12-troubleshooting).

---

## 6. Link the sangkat Telegram group

Do this once per group, so news posts appear in it.

1. Add the bot to your test group.
2. Make the bot an **admin** of the group, and allow **post messages** and **pin messages**.
   Do this **before** step 3.
3. In the group, send:
   ```
   /bind 120101
   ```
4. The bot replies ✅ and pins a welcome message with a **📱 សួរជំនួយការ** button. Residents tap it to open the bot.

From then on, the bot shows every resident the way in, with no setup and no usernames needed:
- **Someone joins the group:** the bot greets them by name with the 📱 button.
- **Anyone taps Menu → /help in the group** (or sends `/start`): the bot replies with the steps and the 📱 button.

The **5 big buttons only appear in the private chat with the bot**, never inside a group: Telegram doesn't allow it.
Residents tap 📱 to get there.
5. Optional: send `/guide` in the group. The bot pins a short "how to use" message.

**Sangkat codes**

| Code | Sangkat |
| :--- | :--- |
| `120101` | ទន្លេបាសាក់ (Tonle Basak), the main demo sangkat |
| `120109` | ទួលទំពូងទី ២ (Tuol Tumpung 2) |
| `120110` | ទួលទំពូងទី ១ (Tuol Tumpung 1) |
| `120111` | បឹងត្របែក (Boeng Trabaek) |
| `120112` | ផ្សារដើមថ្កូវ (Phsar Daeum Thkov) |

> Each computer keeps its **own** records of linked groups, clerks and posts. If the bot moves to another
> computer, repeat sections 5–7 there.

---

## 7. Add a clerk

1. In **your private chat** with the bot, send (use the clerk's real username):
   ```
   /addclerk @sok_dara 120101
   ```
   The bot replies **"✅ @sok_dara ជាអ្នកផ្សាយដំណឹងសម្រាប់សង្កាត់ទន្លេបាសាក់…"**.
2. On the **clerk's phone**: open the bot and press **Start**.
   The clerk gets **"✅ អ្នកអាចផ្សាយដំណឹង…"** and the **📝 ផ្សាយដំណឹង** button.
3. Check with `/clerks`. The clerk now shows **✅ បានភ្ជាប់** (linked).

---

## 8. Run the demo (10 minutes)

Do one practice run first, then send `/delete_last` from the posting account so the group starts clean.

| # | Who | Do this | You should see |
| :--- | :--- | :--- | :--- |
| 1 | Resident | Join the group: the bot greets them with a **📱 សួរជំនួយការ** button (also pinned, and under Menu → /help). Tap it, then **Start** | The bot opens already set to Tonle Basak, with **5 big buttons** |
| 2 | Resident | Tap **🚨 សង្គ្រោះបន្ទាន់** | Police 117, fire 118, ambulance 119 and nearby services. Tapping a number opens the phone dialer |
| 3 | Resident | Tap **📍 សាលាសង្កាត់** | Office hours, address and a map pin |
| 4 | Resident | Type **ភ្លើង** (fire) | The emergency card again: typing works too |
| 5 | Clerk | Tap **📝 ផ្សាយដំណឹង** and paste: *vaccine kids sat 5 dec 8am at sangkat hall bring health book* | **⏳**, then after about 30 seconds: a **flyer**, **clean Khmer text**, a **voice note** and a **📍 map** button |
| 6 | Clerk | Read the question under the preview: **"❓ …ចប់ម៉ោងប៉ុន្មាន?"** (when does it end?). Tap **✏️ កែ** and type *ends 11am* | All three are made again, now with **៨:០០ – ១១:០០ ព្រឹក** |
| 7 | Clerk | Tap **✅ ទន្លេបាសាក់** | "✅ បានផ្សាយរួចរាល់" (published). A clerk sees only their own sangkat |
| 8 | Group | Look at the group | The flyer with the text, the **📱** and **📍** buttons, and the voice note under it |
| 9 | Resident | Tap **📢 ដំណឹងថ្មី** | The same news: read, look, listen ▶️, and **📍** opens the hall on Google Maps |
| 10 | You | Send `/clerks` | Who can post, and whether they have opened the bot |

No AI key? At step 5 the clerk sends text, then a picture, then a voice note (or skips them) instead.
Steps 6 and the 📍 button only happen with the AI helper.

For filming the competition video, use the shot list in [`demo-runsheet.md`](demo-runsheet.md).

---

## 9. Managing clerks

All in **your private chat** with the bot.

| Send | What it does |
| :--- | :--- |
| `/addclerk @name 120101` | Makes @name a clerk for that sangkat. Sending it again with another code **moves** them |
| `/removeclerk @name` | Stops them posting **straight away**. Use it if a phone is lost or someone leaves |
| `/clerks` | Lists everyone who can post: ✅ linked, or ⏳ hasn't pressed Start yet |
| `/addclerk` (alone) | Shows how to use it, and the list of sangkat codes |

**How it stays safe**
- **The role belongs to the person's account, not the name.** The first time an added username opens the
  bot, the role is tied to that account. If they rename themselves later, they keep the role; someone who
  takes their old username gets nothing.
- **A clerk can only post for their own sangkat.** The bot checks this itself, not just the buttons.
- **Only super-admins** can add or remove clerks. To remove a super-admin, take their name out of
  `ADMIN_USERNAMES` in `.env` and restart the bot.
- **Everything is logged**: who posted, deleted, linked a group, or added or removed a clerk, and when.
- After `/removeclerk`, the old **📝** button can stay on the clerk's screen until their next tap. It no
  longer works.

---

## 10. The AI helper

With a Claude key in `.env`, clerks just type the news, messy is fine. The bot makes **clean text + a flyer
+ a Khmer voice note + a 📍 map button**.

| | |
| :--- | :--- |
| **Turn on** | Put the key in `.env` as `ANTHROPIC_API_KEY=sk-ant-…`, then restart the bot |
| **Turn off** | Empty that line, then restart. Clerks then send text, picture and voice by hand |
| **Cost** | About 1 US cent per post. Each ✏️ កែ fix is about another cent |
| **Speed** | About 30 seconds per post |
| **Needs** | Internet, and Edge or Chrome on the laptop |

- **It never makes up facts.** It uses only what the clerk typed. If the end time is missing, it asks
  (❓) instead of guessing.
- **The clerk checks every post** in the preview before it goes out.
- **Privacy:** the notes are sent to Anthropic (to write) and Microsoft (to make the voice). That's fine
  for public news; never put private details in a post.
- **If it fails** (no internet, for example), the bot says so and the clerk continues by hand. Nothing is lost.

---

## 11. Every day: start, stop, restart

Open PowerShell in the project folder (address bar → `powershell` → Enter), then:

| Task | Command |
| :--- | :--- |
| Start the bot | `.venv\Scripts\python -m sangkat_bot`, and leave the window open |
| Stop the bot | **Ctrl + C** in that window |
| Restart (needed after editing `.env`) | Stop, then start again |
| Reload the sangkat data | `.venv\Scripts\python -m sangkat_bot.seed`. Linked groups, clerks and posted news are kept |
| Wipe a private chat before filming | `.venv\Scripts\python scripts/clear_chat.py` |

---

## 12. Troubleshooting

| Problem | Fix |
| :--- | :--- |
| `py` is not recognized | Python isn't installed, or "Add to PATH" wasn't ticked. Reinstall Python and tick it |
| Install error mentioning **long path** | Move the project to a short folder such as `C:\service_bot`, delete the `.venv` folder, and repeat section 2 |
| The bot window shows **`BOT_TOKEN is not set`** | Fill in `BOT_TOKEN=` in `.env` and save |
| The bot window shows **Token is invalid** or **Unauthorized** | The token is wrong or cut short. Copy it again from @BotFather (or the team owner), with no spaces |
| The bot window shows **Conflict** or **terminated by other getUpdates** | The same bot is running on another computer or in another window. Stop one of them |
| No "✅ អ្នកជាអ្នកគ្រប់គ្រងធំ" message, and no /clerks in the menu | Check `ADMIN_USERNAMES` matches your username exactly (no @), save, restart the bot, send `/start` |
| The clerk has no 📝 button | `/clerks`: if they show ⏳, ask them to press Start. Check the username's spelling. They must have a Telegram username |
| A clerk renamed themselves **before** pressing Start | `/removeclerk @old_name`, then `/addclerk @new_name 120101` |
| `/bind` does nothing | Make the bot a group **admin** first. Clerks can bind only their own sangkat's code |
| "⚠️ មិនអាចរៀបចំដោយស្វ័យប្រវត្តិបានទេ" while posting | The AI helper couldn't connect. The clerk continues by hand. Check the internet and the API key |
| A resident in the group "sees no buttons" | Normal: the big buttons are only in the bot's private chat. Tell them to tap **📱 សួរជំនួយការ** (in the welcome, pinned message or a news post), or **Menu → /help** in the group. Residents need no username and don't have to be added |
| The bot doesn't answer anyone | Is the laptop on and online? Is the bot window still open? Start it again |
| A wrong post went out | The person who posted it sends `/delete_last` |

---

## Quick card

```
Install:   py -3 -m venv .venv
           .venv\Scripts\python -m pip install -e ".[dev,ai]"
           copy .env.example .env     → fill BOT_TOKEN, ADMIN_USERNAMES (+ ANTHROPIC_API_KEY)
           .venv\Scripts\python -m sangkat_bot.seed
Run:       .venv\Scripts\python -m sangkat_bot        (keep window open; Ctrl+C stops)

You:       /start → ✅ super-admin
Group:     bot = admin → /bind 120101
Clerks:    /addclerk @name 120101 · /removeclerk @name · /clerks

Codes: 120101 ទន្លេបាសាក់ · 120109 ទួលទំពូងទី ២ · 120110 ទួលទំពូងទី ១
       120111 បឹងត្របែក · 120112 ផ្សារដើមថ្កូវ
One bot = one computer at a time.
```
