"""[1] Ingest — daftar file input, metadata, dan proxy 480p untuk analisis (cache per hash file)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from autoreels.config import PATHS
from autoreels.media import VIDEO_EXTS, MediaInfo, file_hash, probe, run_ffmpeg

CACHE_ROOT = PATHS["work"] / "_cache"
PROXY_HEIGHT = 480


@dataclass
class SourceClip:
    name: str          # nama file (dipakai di EDL sebagai source_file)
    path: Path
    hash: str
    info: MediaInfo
    proxy: Path

    @property
    def cache_dir(self) -> Path:
        return CACHE_ROOT / self.hash


def list_inputs(input_path: str | Path, only: list[str] | None = None) -> list[Path]:
    """File video di input. `only` = nama file yang dipilih pengguna (None = semua isi folder)."""
    p = Path(input_path)
    if p.is_file():
        files = [p]
    elif p.is_dir():
        files = sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXTS)
    else:
        raise FileNotFoundError(f"Input tidak ditemukan: {p}")
    if only is not None:
        wanted = set(only)
        missing = sorted(wanted - {f.name for f in files})
        if missing:
            raise FileNotFoundError(f"Klip yang dipilih tidak ada di {p}: {', '.join(missing)}")
        files = [f for f in files if f.name in wanted]
    if not files:
        raise FileNotFoundError(f"Tidak ada file video di {p}")
    names = [f.name for f in files]
    if len(set(names)) != len(names):
        raise ValueError("Ada nama file video yang sama; ganti nama agar unik.")
    return files


def make_job_id(pillar: str) -> str:
    return f"{datetime.now():%Y%m%d-%H%M%S}-{re.sub(r'[^a-z0-9]+', '', pillar.lower())}"


def _make_proxy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.mp4")
    # ffmpeg otomatis menerapkan rotasi metadata (autorotate) saat decode.
    run_ffmpeg([
        "-i", str(src), "-an",
        "-vf", f"scale=-2:{PROXY_HEIGHT}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-pix_fmt", "yuv420p",
        str(tmp),
    ])
    tmp.replace(dst)


def ingest(input_path: str | Path, log=print, progress=None, only: list[str] | None = None) -> list[SourceClip]:
    clips: list[SourceClip] = []
    files = list_inputs(input_path, only)
    for n, f in enumerate(files):
        if progress:
            progress.update(n, len(files), f"klip {n + 1}/{len(files)}: {f.name}")
        h = file_hash(f)
        cache = CACHE_ROOT / h
        cache.mkdir(parents=True, exist_ok=True)
        meta_file = cache / "meta.json"
        if meta_file.exists():
            info = MediaInfo(**json.loads(meta_file.read_text(encoding="utf-8")))
            info.path = str(f)
        else:
            info = probe(f)
            meta_file.write_text(json.dumps(info.to_dict(), indent=2), encoding="utf-8")
        if info.width == 0:
            log(f"  [lewati] {f.name}: tidak ada stream video")
            continue
        proxy = cache / "proxy.mp4"
        if not proxy.exists():
            log(f"  membuat proxy 480p: {f.name}")
            _make_proxy(f, proxy)
        clips.append(SourceClip(f.name, f.resolve(), h, info, proxy))
    return clips
