# How to post news (clerk guide)

This guide is for the sangkat clerk. Posting one news item takes about a minute.

Only clerks can post. A clerk is someone whose Telegram ID is in `ADMIN_USER_IDS` in the `.env` file.

---

## Before your first post (one time only)

Link the bot to your sangkat's Telegram group:

1. Add **@kh_svc_desk_x7_bot** to the group.
2. Make the bot an **admin** of the group, so it can post and pin.
3. In the group, type: **`/bind 120101`**
   (use your own sangkat's code: Tonle Basak is 120101)
4. Optional: type **`/guide`** in the group. The bot pins a short "how to use" message for residents.

The bot will say ✅ when the group is linked.

---

## Posting news

⚠️ **Do this in your private chat with the bot, not in the group.**
The group only listens to `/bind` and `/guide`.

### 1. Start
Open the private chat with the bot and tap **📝 ផ្សាយដំណឹង**.
(You can also tap **Menu → /announce**.)

> Don't see the 📝 button? Send **/start** first and pick your sangkat.

### 2. Send the text
Type the news, for example:
*ការចាក់វ៉ាក់សាំងកុមារ ថ្ងៃសៅរ៍ ទី៥ ខែធ្នូ ម៉ោង ៨:០០ ព្រឹក នៅសាលាសង្កាត់។*

### 3. Send a picture
Send a photo or a flyer from your phone's gallery.

### 4. Send a voice note
Hold the 🎤 microphone button and read the news out loud.
This helps people who can't read.

> You can tap **⏭️ រំលង** (skip) at any step, but **for best results send all three:
> text + picture + voice.**

### 5. Check and publish
The bot shows you a **preview**, exactly how the post will look.

Then choose who it is for:

| Tap | What happens |
| :--- | :--- |
| **✅ ទន្លេបាសាក់** (or another sangkat name) | Posted for that one sangkat |
| **✅ គ្រប់សង្កាត់ទាំង 5** | Posted for all five sangkats |
| **❌ បោះបង់** | Cancelled, nothing is posted |

### 6. Done ✅
- The news appears in the **sangkat group**: the picture, the text under it, and the voice note below.
- Residents also find it in the bot under **📢 ដំណឹងថ្មី**.

> If a sangkat's group is not linked yet, the news still goes into **📢 ដំណឹងថ្មី**.
> The bot tells you which groups to link and the exact `/bind` command to send.

---

## Made a mistake?

| Problem | What to do |
| :--- | :--- |
| Want to stop while posting | Send **/cancel** |
| Posted something wrong | Send **/delete_last**. It removes your last post from the group and from 📢 |
| Pressed a big button (🚨, 🏥…) by accident while posting | Posting stops. Start again with **📝 ផ្សាយដំណឹង** |

---

## Good to know

- **📢 ដំណឹងថ្មី shows the 3 newest posts.** A new post pushes the oldest one out.
- **Voice notes:** speak slowly and clearly, and say times in words ("ម៉ោងប្រាំបីព្រឹក").
- **Pictures:** a simple flyer with big text works best for older residents.
- **No flyer or voice?** The tech team can make them from your text:
  - flyer: `scripts/make_flyer.py`
  - Khmer voice: `scripts/make_voice.py`
  Then you send them in steps 3 and 4.

---

## Quick card

```
Private chat with the bot
  → 📝 ផ្សាយដំណឹង
  → text → picture → 🎤 voice
  → check the preview
  → ✅ choose the sangkat (or all 5)
  → done!

Oops? → /delete_last
Stop? → /cancel
```
