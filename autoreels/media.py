"""Helper ffmpeg/ffprobe: cari binary, jalankan perintah, probe metadata.

Bila perintah ffmpeg gagal, error menampilkan perintah lengkap + stderr (aturan CLAUDE.md).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from autoreels.config import get_settings

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


class FFmpegError(RuntimeError):
    pass


@lru_cache
def ffmpeg_bin() -> str:
    """Cari ffmpeg: FFMPEG_BIN di .env, PATH, lalu lokasi umum winget di Windows."""
    configured = get_settings().ffmpeg_bin
    if configured and Path(configured).is_file():
        return str(Path(configured))
    found = shutil.which(configured or "ffmpeg")
    if found:
        return found
    winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    if winget.is_dir():
        for exe in winget.glob("*FFmpeg*/**/bin/ffmpeg.exe"):
            return str(exe)
    raise FFmpegError(
        "ffmpeg tidak ditemukan. Pasang dengan `winget install Gyan.FFmpeg` "
        "atau isi FFMPEG_BIN di .env dengan path lengkap ffmpeg.exe."
    )


@lru_cache
def ffprobe_bin() -> str:
    ff = Path(ffmpeg_bin())
    candidate = ff.with_name(ff.name.replace("ffmpeg", "ffprobe"))
    if candidate.is_file():
        return str(candidate)
    found = shutil.which("ffprobe")
    if found:
        return found
    raise FFmpegError("ffprobe tidak ditemukan di samping ffmpeg.")


def run_ffmpeg(args: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """Jalankan ffmpeg dengan argumen (tanpa nama binary). Gagal → FFmpegError berisi perintah & stderr."""
    cmd = [ffmpeg_bin(), "-hide_banner", "-nostdin", "-y", *args]
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        printable = subprocess.list2cmdline(cmd)
        raise FFmpegError(
            f"Perintah ffmpeg gagal (exit {proc.returncode}).\n"
            f"Direktori: {cwd or os.getcwd()}\nPerintah:\n{printable}\n\nstderr:\n{proc.stderr[-4000:]}"
        )
    return proc


def run_ffmpeg_stderr(args: list[str]) -> str:
    """Jalankan ffmpeg untuk analisis (mis. ebur128/blackdetect) dan kembalikan stderr-nya."""
    return run_ffmpeg(args).stderr


@dataclass
class MediaInfo:
    path: str
    duration: float
    width: int
    height: int
    fps: float
    rotation: int
    has_audio: bool

    @property
    def display_width(self) -> int:
        return self.height if abs(self.rotation) in (90, 270) else self.width

    @property
    def display_height(self) -> int:
        return self.width if abs(self.rotation) in (90, 270) else self.height

    def to_dict(self) -> dict:
        return asdict(self)


def probe(path: str | Path) -> MediaInfo:
    cmd = [ffprobe_bin(), "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise FFmpegError(f"ffprobe gagal untuk {path}:\n{subprocess.list2cmdline(cmd)}\n{proc.stderr}")
    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    duration = float(data.get("format", {}).get("duration") or 0)
    if video is None:
        return MediaInfo(str(path), duration, 0, 0, 0.0, 0, has_audio)
    num, _, den = (video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    rotation = 0
    for sd in video.get("side_data_list", []) or []:
        if "rotation" in sd:
            rotation = int(sd["rotation"])
    if not rotation and "rotate" in (video.get("tags") or {}):
        rotation = int(video["tags"]["rotate"])
    return MediaInfo(str(path), duration, int(video["width"]), int(video["height"]), round(fps, 3), rotation, has_audio)


def file_hash(path: str | Path, chunk: int = 4 * 1024 * 1024) -> str:
    """Hash cepat (ukuran + 4 MB awal + 4 MB akhir) untuk kunci cache per file."""
    p = Path(path)
    size = p.stat().st_size
    h = hashlib.sha1(str(size).encode())
    with open(p, "rb") as f:
        h.update(f.read(chunk))
        if size > chunk:
            f.seek(max(size - chunk, chunk))
            h.update(f.read(chunk))
    return h.hexdigest()[:16]
