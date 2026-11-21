# Clerk roles by Telegram username (short design)

Approved in chat on 2026-11-21. The user chose ideas 1, 2 and 3, adding clerks by username rather than numeric id.

## Why
Today the clerk list is numeric Telegram ids in `.env`. A sangkat can't edit that file or restart the
bot, every clerk can post to every sangkat, and a lost phone stays a clerk until someone edits `.env`.

## What
- **Super-admins** come from `.env`:
  - `ADMIN_USERNAMES=sok_dara,other_admin` (new);
  - `ADMIN_USER_IDS` still works.
  - They post to any sangkat or to all of them, and they manage clerks.
- **Clerks** post only for their own sangkat. The preview shows one ✅ button, for that sangkat.
- Super-admin commands, in the private chat with the bot:
  - `/addclerk @username 120101`: add a clerk, or move them to another sangkat;
  - `/removeclerk @username`: remove a clerk, effective immediately;
  - `/clerks`: list clerks, each shown as ✅ linked or ⏳ hasn't opened the bot yet.
- **The username is locked to the account on first contact.** The first message or tap from that
  username records the person's Telegram account on the clerk row. From then on:
  - the check is by account, so a later username change keeps the role;
  - someone who later takes over the old username gets nothing.
  The clerk gets a "✅ you can post for …" message and the clerk command menu.
- A clerk may `/bind` and `/guide` only for their own sangkat's group.
- The server checks every publish against the clerk's own sangkat, so a forged or old
  `ann:publish:all` button does nothing for a clerk.

## Rules
- Usernames are stored lower-case without `@`. Accepted input: `@name`, `name` or `t.me/name`,
  5 to 32 characters of letters, digits and underscore.
- A clerk without a Telegram username can't be added this way. The clerk guide says to set one in
  Telegram's settings first.
- Super-admins from `.env` can't be removed with `/removeclerk`. Taking a username out of `.env`
  removes its super role at the next start.
- Every add and remove is written to `audit_logs`.

## Approaches considered
1. **Username to add, locked to the account on first contact (chosen).** The user only ever types
   usernames, and the role can't be taken over through a recycled username.
2. Username only, checked on every message. Simpler, but anyone who claims a freed username becomes
   a clerk.
3. One-time invite codes. Safe, but an extra step, and the user prefers usernames.

## How (builder notes)
- New `clerks` table: `username` (unique), `telegram_user_id` (unique, filled on first contact),
  `role` ('super' or 'clerk'), `commune_code`, `added_by`, `added_at`. SQL lives in `db.py`.
- `sangkat_bot/clerks.py` holds:
  - `normalize_username`;
  - `Role(is_super, commune_code)` and `role_of(conn, settings, user_id)`;
  - an outer middleware that does the first-contact linking.
- Handlers call `role_of` in place of the old `is_admin(user_id, settings)`.

## Tasks
- [x] clerks table, db helpers, `clerks.py` and the linking middleware
- [x] `/addclerk`, `/removeclerk` and `/clerks`, plus a command menu for super-admins
- [x] Clerks limited to their own sangkat: preview buttons, publish check, `/bind`, `/guide`
- [x] Copy, `.env` (`ADMIN_USERNAMES`), README and clerk guide
