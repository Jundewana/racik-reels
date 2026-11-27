"""Analisis musik: pilih lagu per mood, deteksi beat & tempo (librosa), cari bagian lagu yang 'naik'."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from autoreels.analyze.models import MusicInfo
from autoreels.config import PATHS
from autoreels.media import AUDIO_EXTS, file_hash

MUSIC_CACHE = PATHS["work"] / "_cache" / "music"
ANALYSIS_VERSION = 2  # v2: dekode lewat ffmpeg (v1 salah membaca AAC/M4A bernama .mp3 → 0 BPM)
MIN_BEATS = 8
WINDOW_SEC = 30.0  # panjang jendela lagu yang dinilai energinya


def list_tracks(mood: str) -> list[Path]:
    folder = PATHS["music"] / mood
    if not folder.is_dir():
        return []
    return sorted(f for f in folder.iterdir() if f.suffix.lower() in AUDIO_EXTS)


# Bila folder mood kosong, pakai mood terdekat (urutan = paling mirip lebih dulu).
MOOD_FALLBACK = {
    "inspiratif": ["santai", "dramatis", "upbeat"],
    "dramatis": ["inspiratif", "upbeat", "santai"],
    "santai": ["inspiratif", "upbeat", "dramatis"],
    "upbeat": ["santai", "inspiratif", "dramatis"],
}


def choose_track(mood: str, seed: str) -> Path | None:
    """Pilih lagu secara deterministik (seed = job id) agar render ulang memakai lagu yang sama."""
    tracks = list_tracks(mood)
    if not tracks:
        return None
    idx = int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(tracks)
    return tracks[idx]


def choose_track_with_fallback(mood: str, seed: str) -> tuple[Path | None, str]:
    """(lagu, mood yang benar-benar dipakai). Folder mood kosong → mood terdekat yang ada lagunya."""
    for m in [mood, *MOOD_FALLBACK.get(mood, ["upbeat", "santai", "inspiratif", "dramatis"])]:
        track = choose_track(m, seed)
        if track:
            return track, m
    return None, mood


def _decode(path: Path, sr: int = 22050) -> np.ndarray:
    """Dekode audio apa pun lewat ffmpeg → float32 mono. Unduhan YouTube sering berupa AAC/M4A yang diberi
    ekstensi .mp3; libsndfile/mpg123 (librosa) gagal membacanya, ffmpeg tidak."""
    import subprocess

    from autoreels.media import ffmpeg_bin

    proc = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                           "-f", "f32le", "-"], capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Lagu tidak bisa dibaca: {path.name}: {proc.stderr.decode('utf-8', 'replace')[:300]}")
    return np.frombuffer(proc.stdout, dtype=np.float32)


def _analyze_track(path: Path) -> dict:
    cache = MUSIC_CACHE / f"{file_hash(path)}_v{ANALYSIS_VERSION}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    import librosa

    sr = 22050
    y = _decode(path, sr)
    duration = len(y) / sr
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    rms_t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    data = {
        "tempo": float(np.atleast_1d(tempo)[0]),
        "duration": duration,
        "beats": beats,
        "rms": rms.tolist()[:: 4],
        "rms_t": rms_t.tolist()[:: 4],
    }
    MUSIC_CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def _best_start(data: dict, needed: float) -> float:
    """Pilih beat awal (kelipatan 4 beat / 'birama') dengan energi tertinggi untuk sepanjang Reel."""
    beats = data["beats"]
    rms = np.asarray(data["rms"])
    rms_t = np.asarray(data["rms_t"])
    if len(beats) < 8 or len(rms) == 0:
        return 0.0
    window = max(needed, 10.0)
    best, best_score = beats[0], -1.0
    for b in beats[::4]:
        if b + window + 1.0 > data["duration"]:
            break
        mask = (rms_t >= b) & (rms_t < b + window)
        if not mask.any():
            continue
        # energi tinggi & stabil, sedikit preferensi bagian awal lagu
        score = float(rms[mask].mean()) - 0.2 * float(rms[mask].std()) - 0.002 * b
        # awal yang 'menghentak': energi 2 dtk pertama dibanding 2 dtk sebelumnya
        pre = rms[(rms_t >= b - 2) & (rms_t < b)]
        post = rms[(rms_t >= b) & (rms_t < b + 2)]
        if len(pre) and len(post):
            score += 0.3 * max(0.0, float(post.mean() - pre.mean()))
        if score > best_score:
            best, best_score = b, score
    return float(best)


def _rotated(tracks: list[Path], seed: str) -> list[Path]:
    if not tracks:
        return []
    i = int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(tracks)
    return tracks[i:] + tracks[:i]


def _usable_analysis(path: Path, log) -> dict | None:
    """Analisis lagu; None (dengan peringatan) bila tidak bisa dibaca atau ketukannya tidak terdeteksi."""
    try:
        data = _analyze_track(path)
    except Exception as e:  # noqa: BLE001 — satu lagu rusak tidak boleh menggagalkan job
        log(f"  [musik] lewati {path.name}: {str(e)[:120]}")
        return None
    if len(data.get("beats", [])) < MIN_BEATS:
        log(f"  [musik] lewati {path.name}: ketukan tidak terdeteksi ({data.get('tempo', 0):.0f} BPM)")
        return None
    return data


def prepare_music(mood: str, seed: str, needed_sec: float, forced: Path | None = None,
                  log=print) -> MusicInfo | None:
    """Siapkan musik: lagu pilihan pengguna (forced), atau lagu dari folder mood style.
    Folder mood kosong → mood terdekat (dicatat di log & checklist). MusicInfo.mood = mood yang dipakai."""
    used_mood = mood
    if forced:
        path = forced
        used_mood = Path(forced).parent.name
    else:
        path, used_mood = choose_track_with_fallback(mood, seed)
        if path is not None and used_mood != mood:
            log(f"  [musik] folder '{mood}' kosong → memakai lagu '{used_mood}' (isi assets/music/{mood}/ agar sesuai style)")
    if path is None:
        log("  [musik] tidak ada lagu sama sekali di assets/music/ — video tanpa musik")
        return None
    data = _usable_analysis(path, log)
    if data is None and not forced:
        # lagu terpilih rusak/tanpa ketukan → coba lagu lain (urutan tetap per job agar render ulang konsisten)
        for alt_mood in [used_mood, *MOOD_FALLBACK.get(used_mood, [])]:
            for alt in _rotated(list_tracks(alt_mood), seed):
                if alt == path:
                    continue
                data = _usable_analysis(alt, log)
                if data is not None:
                    path, used_mood = alt, alt_mood
                    log(f"  [musik] memakai lagu pengganti: {alt.name}")
                    break
            if data is not None:
                break
    if data is None:
        log("  [musik] tidak ada lagu yang ketukannya terbaca — video tanpa musik")
        return None
    start = _best_start(data, needed_sec + 2)
    beats = [round(b - start, 3) for b in data["beats"] if start <= b <= start + needed_sec + 10]
    return MusicInfo(
        path=str(path),
        mood=used_mood,
        tempo=round(data["tempo"], 2),
        duration=round(data["duration"], 2),
        start_offset=round(start, 3),
        beats=beats,
    )
