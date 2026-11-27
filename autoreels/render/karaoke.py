"""Video contoh subtitle karaoke dari audio ucapan (uji Tahap 3, sebelum ada rekaman video bicara).

Latar warna brand 1080×1920 + subtitle karaoke + audio yang sudah dibersihkan (tanpa jeda & kata pengisi).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from autoreels.config import PATHS, load_brand, load_style
from autoreels.media import run_ffmpeg
from autoreels.render.reframe import OUT_H, OUT_W
from autoreels.render.text_ass import build_ass, font_full_name, karaoke_events


def render_karaoke_preview(audio: Path, words, out: Path, duration: float, style_name: str = "info_lowongan") -> Path:
    style = load_style(style_name)
    brand = load_brand()
    work = out.parent / "_karaoke"
    if work.exists():
        shutil.rmtree(work)
    (work / "fonts").mkdir(parents=True)
    font_file = PATHS["fonts"] / (style.get("font") or brand.get("fonts", {}).get("heading"))
    shutil.copy(font_file, work / "fonts" / font_file.name)
    (work / "text.ass").write_text(build_ass(karaoke_events(words, duration), style, font_full_name(font_file)),
                                   encoding="utf-8")
    bg = brand.get("colors", {}).get("purple", "#2B176E").lstrip("#")
    run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=0x{bg}:s={OUT_W}x{OUT_H}:r=30:d={duration:.3f}",
        "-i", str(Path(audio).resolve()),
        "-filter_complex", "[0:v]subtitles=text.ass:fontsdir=fonts,format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out.resolve()),
    ], cwd=work)
    shutil.rmtree(work, ignore_errors=True)
    return out
