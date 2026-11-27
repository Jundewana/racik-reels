"""Efek suara transisi: whoosh (whip/slide), thump (zoom-punch), pop (teks hook muncul).

Bunyi disintesis sendiri dengan numpy (derau tersaring + nada meluncur) lalu disimpan di assets/sfx/ — buatan
sendiri, jadi bebas royalti (tidak mengunduh SFX pihak lain). Dicampur ke audio Reel pada titik potong; volume per
gaya: `sfx_db` di config/styles/*.yaml (tidak diisi / null = tanpa SFX).
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from autoreels.edl import EDL, Transition

SR = 48000
PEAK = 10 ** (-3 / 20)          # puncak tiap bunyi −3 dBFS sebelum diberi volume gaya
SOUNDS = {Transition.whip: "whoosh", Transition.slide_left: "whoosh", Transition.zoom_punch: "thump"}
LEAD = {"whoosh": 0.22, "thump": 0.02, "pop": 0.0}   # detik bunyi dimulai sebelum titik potong (puncak whoosh di potongan)


def _write(path: Path, stereo: np.ndarray, normalize: bool = True) -> None:
    if normalize:
        stereo = stereo / max(1e-9, float(np.abs(stereo).max())) * PEAK
    data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def _whoosh(dur: float = 0.5) -> np.ndarray:
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    noise = np.random.default_rng(7).standard_normal(n)
    cutoff = 300 + 5200 * np.sin(np.pi * t) ** 2            # tapis lolos-rendah menyapu naik lalu turun
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    out, y = np.empty(n), 0.0
    for i in range(n):  # tapis satu kutub bervariasi waktu (sekali saat membuat file)
        y += alpha[i] * (noise[i] - y)
        out[i] = y
    env = np.sin(np.pi * np.clip(t / 0.62, 0, 1) / 2) ** 2 * np.clip((1 - t) / 0.38, 0, 1) ** 1.5
    mono = out * env
    pan = t                                                  # bergerak kiri → kanan
    return np.stack([mono * np.cos(pan * np.pi / 2), mono * np.sin(pan * np.pi / 2)], axis=1)


def _thump(dur: float = 0.35) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    freq = 45 + 70 * np.exp(-t / 0.05)                      # nada turun 115 → 45 Hz
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.09)
    click = np.random.default_rng(3).standard_normal(len(t)) * np.exp(-t / 0.004) * 0.3
    mono = body + click
    return np.stack([mono, mono], axis=1)


def _pop(dur: float = 0.12) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    freq = 600 + 500 * np.exp(-t / 0.02)
    mono = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.03) * np.clip(t / 0.002, 0, 1)
    return np.stack([mono, mono], axis=1)


def ensure_sfx(folder: Path) -> dict[str, Path]:
    """Buat file SFX bila belum ada; kembalikan nama → path."""
    makers = {"whoosh": _whoosh, "thump": _thump, "pop": _pop}
    paths = {}
    for name, make in makers.items():
        p = folder / f"{name}.wav"
        if not p.exists():
            _write(p, make())
        paths[name] = p
    return paths


def _read(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        raw = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
    return raw.reshape(-1, 2)


def sfx_cues(edl: EDL, times: list[tuple[float, float]]) -> list[tuple[float, str]]:
    """(detik mulai bunyi, nama) — transisi berbunyi + pop saat teks hook muncul."""
    cues = []
    if edl.hook.overlay_text:
        cues.append((0.05, "pop"))
    for seg, (start, _) in zip(edl.segments[1:], times[1:]):
        name = SOUNDS.get(seg.transition_in)
        if name:
            cues.append((max(0.0, start - LEAD[name]), name))
    return cues


def render_sfx_track(cues: list[tuple[float, str]], total: float, gain_db: float, folder: Path, out: Path) -> Path:
    """Satu jalur stereo sepanjang video berisi semua bunyi pada waktunya."""
    sounds = {k: _read(p) for k, p in ensure_sfx(folder).items()}
    track = np.zeros((int(SR * total) + 1, 2), np.float32)
    g = 10 ** (gain_db / 20)
    for at, name in cues:
        snd = sounds[name]
        i = int(at * SR)
        j = min(len(track), i + len(snd))
        if i < j:
            track[i:j] += snd[: j - i] * g
    _write(out, track, normalize=False)
    return out

