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

### 2. Send the news, any way you like
**If the AI helper is on** (the bot says *"…ខ្ញុំនឹងរៀបចំជា អត្ថបទ រូបភាព និងសំឡេង ឲ្យ"*):

Just type or paste what you know. It can be messy, in any order, even mixed with English:
*vaccine kids sat 5 dec 8am at sangkat hall bring health book*

The bot replies **⏳ កំពុងរៀបចំ…**. About half a minute later it shows the finished post:
**clean text + a flyer picture + a Khmer voice note**. Go to step 5.

- Have your own picture? Send the photo and write the news in its caption. The bot keeps your
  photo and makes only the text and voice.
- The AI uses only what you wrote. If you leave out the time, there will be no time in the post.
  It never guesses.

**If the AI helper is off**, do it by hand: steps 2a to 2c.

#### 2a. Text
Type the news, for example:
*ការចាក់វ៉ាក់សាំងកុមារ ថ្ងៃសៅរ៍ ទី៥ ខែធ្នូ ម៉ោង ៨:០០ ព្រឹក នៅសាលាសង្កាត់។*

#### 2b. Picture
Send a photo or a flyer from your phone's gallery.

#### 2c. Voice note
Hold the 🎤 microphone button and read the news out loud.
This helps people who can't read.

> You can tap **⏭️ រំលង** (skip) at any step, but **for best results send all three:
> text + picture + voice.**

### 5. Check and publish
The bot shows you a **preview**, exactly how the post will look.
**Check the date, time and place carefully**, especially on AI-made posts.

Then choose who it is for:

| Tap | What happens |
| :--- | :--- |
| **✅ ទន្លេបាសាក់** (or another sangkat name) | Posted for that one sangkat |
| **✅ គ្រប់សង្កាត់ទាំង 5** | Posted for all five sangkats |
| **✏️ កែ** (AI posts only) | Type what to change, e.g. *"the time is 7 PM, not 6"*. Text, picture and voice are all made again |
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
- **AI helper:** it is on when `ANTHROPIC_API_KEY` is set in `.env`, and it needs internet.
  If it fails, the bot says so and continues by hand, keeping what you typed.
  Your notes are sent to Anthropic (to write the post) and Microsoft (to make the voice).
  That is fine for public news. Don't put private details in a post.
- **No AI helper?** The tech team can make flyers and voices from your text:
  `scripts/make_flyer.py` and `scripts/make_voice.py`.

---

## Quick card

```
Private chat with the bot
  → 📝 ផ្សាយដំណឹង
  → type the news (messy is fine)
    (AI off: text → picture → 🎤 voice)
  → check the preview (✏️ កែ to fix)
  → ✅ choose the sangkat (or all 5)
  → done!

Oops? → /delete_last
Stop? → /cancel
```
