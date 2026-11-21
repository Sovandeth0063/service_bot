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
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg

VOICES = ("km-KH-SreymomNeural", "km-KH-PisethNeural")


async def synthesize(text: str, mp3: Path, voice: str) -> None:
    await edge_tts.Communicate(text, voice, rate="-10%").save(str(mp3))  # a little slower for older listeners


def to_voice_note(mp3: Path, ogg: Path) -> None:
    """Telegram shows a playable voice bubble only for OGG/Opus."""
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(mp3),
         "-ac", "1", "-c:a", "libopus", "-b:a", "32k", str(ogg)],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("speech", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--voice", choices=VOICES, default=VOICES[0])
    args = parser.parse_args()
    text = args.speech.read_text(encoding="utf-8").strip()
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "speech.mp3"
        asyncio.run(synthesize(text, mp3, args.voice))
        to_voice_note(mp3, args.out)
    print(f"wrote {args.out} ({args.out.stat().st_size // 1024} KB, voice {args.voice})")


if __name__ == "__main__":
    main()
