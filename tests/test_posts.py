import pytest

from sangkat_bot.posts import CAPTION_LIMIT, Send, announcement_body, build_post

H = "📢 ដំណឹងពីសង្កាត់ទន្លេបាសាក់"


def test_text_only():
    assert build_post(H, "សួស្តី", None, None) == [Send("text", announcement_body(H, "សួស្តី"), None, True, False)]


def test_photo_with_short_text():
    sends = build_post(H, "សួស្តី", "P", None)
    assert len(sends) == 1 and sends[0].kind == "photo" and sends[0].file_id == "P"
    assert "សួស្តី" in sends[0].text and sends[0].is_lead


def test_long_text_with_photo_splits():
    sends = build_post(H, "ក" * 1100, "P", None)
    assert [s.kind for s in sends] == ["text", "photo"]
    assert sends[0].is_lead and not sends[1].is_lead and sends[1].text == f"<b>{H}</b>"


def test_text_exactly_at_limit_stays_caption():
    text = "ក" * (CAPTION_LIMIT - len(announcement_body(H, "")) - 2)
    assert len(announcement_body(H, text)) == CAPTION_LIMIT
    assert [s.kind for s in build_post(H, text, "P", None)] == ["photo"]


def test_all_three():
    sends = build_post(H, "t", "P", "V")
    assert [s.kind for s in sends] == ["photo", "voice"]
    assert sends[1].reply_to_lead and sends[1].file_id == "V" and not sends[1].is_lead


def test_voice_only_has_header_lead():
    sends = build_post(H, None, None, "V")
    assert [s.kind for s in sends] == ["text", "voice"] and sends[0].text == f"<b>{H}</b>"


def test_blank_text_counts_as_none():
    assert build_post(H, "   ", "P", None)[0].text == f"<b>{H}</b>"


def test_nothing_raises():
    with pytest.raises(ValueError):
        build_post(H, None, None, None)
    with pytest.raises(ValueError):
        build_post(H, "  ", None, None)


def test_text_is_escaped():
    assert "&lt;script&gt;" in build_post(H, "<script>", None, None)[0].text


class FakeBot:
    """Records calls; returns messages with increasing ids."""

    def __init__(self):
        self.calls = []

    def _msg(self, kind, **kwargs):
        self.calls.append((kind, kwargs))
        return type("M", (), {"message_id": 100 + len(self.calls)})()

    async def send_message(self, chat_id, text, **kw):
        return self._msg("text", chat_id=chat_id, text=text, **kw)

    async def send_photo(self, chat_id, photo, **kw):
        return self._msg("photo", chat_id=chat_id, photo=photo, **kw)

    async def send_voice(self, chat_id, voice, **kw):
        return self._msg("voice", chat_id=chat_id, voice=voice, **kw)


async def test_send_post_voice_replies_to_lead_and_button_only_on_lead():
    from sangkat_bot.posts import send_post

    bot, markup = FakeBot(), object()
    lead, voice = await send_post(bot, -5, build_post(H, "ក" * 1100, "P", "V"), markup)
    kinds = [c[0] for c in bot.calls]
    assert kinds == ["text", "photo", "voice"] and (lead, voice) == (101, 103)
    assert bot.calls[0][1]["reply_markup"] is markup and bot.calls[1][1]["reply_markup"] is None
    assert bot.calls[2][1]["reply_to_message_id"] == 101
