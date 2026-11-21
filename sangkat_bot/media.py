"""Flyer pictures and Khmer voice notes for news, used by the bot and by scripts/make_*.py.

The flyer is drawn by headless Chrome (or Edge), so Khmer text shapes correctly; it needs
internet for the Kantumruy Pro font. The voice uses Microsoft's free neural Khmer voices
through edge-tts (needs internet and `pip install -e ".[media]"`): only public announcement
text is sent there.
"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from html import escape
from pathlib import Path

BROWSERS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)
VOICES = ("km-KH-SreymomNeural", "km-KH-PisethNeural")

TEMPLATE = """<!doctype html>
<html lang="km"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Kantumruy+Pro:wght@400;600;700&display=block">
<style>
  :root {{ --green: #1f7a4d; --green-dark: #155c39; --cream: #fbf7ef; --ink: #1d2a24; --amber: #f2b632; }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ width: 1080px; height: 1080px; background: var(--cream); font-family: "Kantumruy Pro", sans-serif;
         color: var(--ink); display: flex; flex-direction: column; }}
  .top {{ background: var(--green); color: #fff; padding: 44px 64px 36px; display: flex;
          justify-content: space-between; align-items: center; }}
  .who {{ font-size: 40px; font-weight: 600; }}
  .tag {{ background: var(--amber); color: var(--ink); font-size: 30px; font-weight: 700; padding: 8px 26px; border-radius: 40px; }}
  main {{ flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 26px; padding: 10px 56px; }}
  .hero {{ text-align: center; }}
  .icon {{ font-size: 190px; line-height: 1.1; }}
  h1 {{ font-size: {title_size}px; font-weight: 700; color: var(--green-dark); line-height: 1.35; }}
  .sub {{ font-size: 46px; font-weight: 600; color: #3d4d45; }}
  .facts {{ display: grid; grid-template-columns: repeat({fact_count}, 1fr); gap: 26px; }}
  .fact {{ background: #fff; border: 4px solid var(--green); border-radius: 28px; text-align: center; padding: 20px 8px 24px; }}
  .fact .i {{ font-size: 60px; }}
  .fact .l {{ font-size: 30px; color: #4f5f57; }}
  .fact .v {{ font-size: {value_size}px; font-weight: 700; color: var(--green-dark); line-height: 1.35; }}
  .note {{ background: #fff4d6; border-left: 12px solid var(--amber); border-radius: 18px; font-size: 40px;
           font-weight: 600; padding: 20px 30px; }}
  .bottom {{ background: var(--green-dark); color: #e8f3ec; text-align: center; font-size: 30px; padding: 22px; min-height: 30px; }}
</style></head>
<body>
  <div class="top"><span class="who">{who}</span><span class="tag">{tag}</span></div>
  <main>
    <div class="hero"><div class="icon">{icon}</div><h1>{title}</h1>{subtitle}</div>
    {facts}
    {note}
  </main>
  <div class="bottom">{footer}</div>
</body></html>
"""


def render_html(spec: dict) -> str:
    """Flyer page for a spec: who, tag, icon, title, subtitle?, facts [{icon, label, value}] x0-3, note?, footer."""
    facts = spec.get("facts") or []
    cells = "".join(
        f'<div class="fact"><div class="i">{escape(f["icon"])}</div><div class="l">{escape(f["label"])}</div>'
        f'<div class="v">{escape(f["value"])}</div></div>'
        for f in facts
    )
    return TEMPLATE.format(
        who=escape(spec["who"]), tag=escape(spec["tag"]), icon=escape(spec["icon"]), title=escape(spec["title"]),
        title_size=spec.get("title_size", 92), value_size=spec.get("value_size", 54), fact_count=max(len(facts), 1),
        subtitle=f'<div class="sub">{escape(spec["subtitle"])}</div>' if spec.get("subtitle") else "",
        note=f'<div class="note">{escape(spec["note"])}</div>' if spec.get("note") else "",
        facts=f'<div class="facts">{cells}</div>' if facts else "", footer=escape(spec.get("footer") or ""),
    )


def render_flyer(spec: dict, out: Path) -> Path:
    """Screenshot the flyer page to a 1080×1080 PNG. Blocking: call it in a thread from async code."""
    browser = next((b for b in BROWSERS if b.is_file()), None)
    if browser is None:
        raise RuntimeError("Chrome or Edge not found")
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "flyer.html"
        page.write_text(render_html(spec), encoding="utf-8")
        subprocess.run(
            [str(browser), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1080,1080",
             "--virtual-time-budget=8000", f"--screenshot={out.resolve()}", page.as_uri()],
            check=True, capture_output=True, timeout=60,
        )
    if not out.is_file():
        raise RuntimeError("the browser did not write the flyer")
    return out


async def make_voice_note(text: str, out: Path, voice: str = VOICES[0]) -> Path:
    """Khmer speech as a Telegram voice note (OGG/Opus), a little slower for older listeners."""
    import edge_tts  # optional extra: pip install -e ".[media]"

    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "speech.mp3"
        await edge_tts.Communicate(text, voice, rate="-10%").save(str(mp3))
        await asyncio.to_thread(_to_voice_note, mp3, out)
    return out


def _to_voice_note(mp3: Path, ogg: Path) -> None:
    """Telegram shows a playable voice bubble only for OGG/Opus."""
    import imageio_ffmpeg

    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(mp3),
         "-ac", "1", "-c:a", "libopus", "-b:a", "32k", str(ogg)],
        check=True, capture_output=True, timeout=60,
    )
