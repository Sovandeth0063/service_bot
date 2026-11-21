r"""Turn Khmer text into a Telegram voice note (OGG/Opus), for demo news.

Usage: .venv\Scripts\python scripts/make_voice.py <speech.txt> <out.ogg> [--voice km-KH-PisethNeural]

Uses Microsoft's free neural Khmer voices through edge-tts (needs internet; the text is
sent to Microsoft's speech service, so use it only for public announcement text).
Write the speech file the way it should be *said*: numbers and times in words.
Needs: pip install -e ".[media]"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sangkat_bot.media import VOICES, make_voice_note  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("speech", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--voice", choices=VOICES, default=VOICES[0])
    args = parser.parse_args()
    text = args.speech.read_text(encoding="utf-8").strip()
    asyncio.run(make_voice_note(text, args.out, args.voice))
    print(f"wrote {args.out} ({args.out.stat().st_size // 1024} KB, voice {args.voice})")


if __name__ == "__main__":
    main()
