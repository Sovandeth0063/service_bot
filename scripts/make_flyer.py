r"""Render a square news flyer (PNG) from a small JSON spec, using Chrome for correct Khmer text.

Usage: .venv\Scripts\python scripts/make_flyer.py data/demo_media/<news>/flyer.json

Writes flyer.png next to the spec. Spec keys:
  who, tag, icon, title, subtitle (optional), facts: [{icon, label, value}] x3, note (optional), footer
Needs Google Chrome or Microsoft Edge, and internet for the Kantumruy Pro font.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

BROWSERS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)

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
  .facts {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 26px; }}
  .fact {{ background: #fff; border: 4px solid var(--green); border-radius: 28px; text-align: center; padding: 20px 8px 24px; }}
  .fact .i {{ font-size: 60px; }}
  .fact .l {{ font-size: 30px; color: #4f5f57; }}
  .fact .v {{ font-size: {value_size}px; font-weight: 700; color: var(--green-dark); line-height: 1.35; }}
  .note {{ background: #fff4d6; border-left: 12px solid var(--amber); border-radius: 18px; font-size: 40px;
           font-weight: 600; padding: 20px 30px; }}
  .bottom {{ background: var(--green-dark); color: #e8f3ec; text-align: center; font-size: 30px; padding: 22px; }}
</style></head>
<body>
  <div class="top"><span class="who">{who}</span><span class="tag">{tag}</span></div>
  <main>
    <div class="hero"><div class="icon">{icon}</div><h1>{title}</h1>{subtitle}</div>
    <div class="facts">{facts}</div>
    {note}
  </main>
  <div class="bottom">{footer}</div>
</body></html>
"""


def render_html(spec: dict) -> str:
    facts = "".join(
        f'<div class="fact"><div class="i">{escape(f["icon"])}</div><div class="l">{escape(f["label"])}</div>'
        f'<div class="v">{escape(f["value"])}</div></div>'
        for f in spec["facts"]
    )
    return TEMPLATE.format(
        who=escape(spec["who"]), tag=escape(spec["tag"]), icon=escape(spec["icon"]), title=escape(spec["title"]),
        title_size=spec.get("title_size", 92), value_size=spec.get("value_size", 54),
        subtitle=f'<div class="sub">{escape(spec["subtitle"])}</div>' if spec.get("subtitle") else "",
        note=f'<div class="note">{escape(spec["note"])}</div>' if spec.get("note") else "",
        facts=facts, footer=escape(spec["footer"]),
    )


def main() -> None:
    spec_path = Path(sys.argv[1]).resolve()
    out = spec_path.with_name("flyer.png")
    browser = next((b for b in BROWSERS if b.is_file()), None)
    if browser is None:
        raise SystemExit("Chrome or Edge not found.")
    html = render_html(json.loads(spec_path.read_text(encoding="utf-8")))
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "flyer.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run(
            [str(browser), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1080,1080",
             "--virtual-time-budget=8000", f"--screenshot={out}", page.as_uri()],
            check=True, capture_output=True,
        )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
