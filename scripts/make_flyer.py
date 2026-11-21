r"""Render a square news flyer (PNG) from a small JSON spec, using Chrome for correct Khmer text.

Usage: .venv\Scripts\python scripts/make_flyer.py data/demo_media/<news>/flyer.json

Writes flyer.png next to the spec. Spec keys:
  who, tag, icon, title, subtitle (optional), facts: [{icon, label, value}] x1-3, note (optional), footer
Needs Google Chrome or Microsoft Edge, and internet for the Kantumruy Pro font.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sangkat_bot.media import render_flyer  # noqa: E402


def main() -> None:
    spec_path = Path(sys.argv[1]).resolve()
    out = render_flyer(json.loads(spec_path.read_text(encoding="utf-8")), spec_path.with_name("flyer.png"))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
