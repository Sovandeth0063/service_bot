"""The "how to use" guides: /help in the bot, and /guide pinned in the commune group.

Built from the button labels in the copy file, so the guide always matches the keyboard.
"""

from __future__ import annotations

from html import escape

from sangkat_bot.copy import Copy


def resident_guide(copy: Copy) -> str:
    parts = [f"<b>{escape(copy.t('guide.title'))}</b>", escape(copy.t("guide.intro"))]
    for row in copy.keyboard_layout:
        for intent in row:
            parts.append(f"<b>{escape(copy.button(intent))}</b>\n{escape(copy.t(f'guide.items.{intent}'))}")
    tips = "\n".join(escape(tip) for tip in copy.lines("guide.tips"))
    parts.append(f"<b>{escape(copy.t('guide.tips_header'))}</b>\n{tips}")
    return "\n\n".join(parts)


def group_guide(copy: Copy) -> str:
    button = copy.t("open_bot_button")
    steps = "\n".join(escape(step.replace("{open_bot_button}", button)) for step in copy.lines("guide.group_steps"))
    return f"<b>{escape(copy.t('guide.group_title'))}</b>\n\n{steps}\n\n{escape(copy.t('guide.group_footer'))}"
