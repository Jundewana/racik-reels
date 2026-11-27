"""Warna seragam: koreksi per klip sebelum look gaya (`color_grade`) agar footage dari HP berbeda terasa satu Reel.

Tiap sumber gambar (adegan b-roll; klip pembicara diukur sekali per klip agar tidak berkedip) diukur dari 3 frame kecil:
kecerahan, warna cahaya (dari piksel hampir abu-abu saja), saturasi. Hanya pencilan yang dikoreksi: kecerahan di luar
median ±25 (dalam batas 85–160), warna cahaya yang menyimpang dari median Reel (dinetralkan setengah, maks ±5%,
dilewati bila piksel abu-abu terlalu sedikit), saturasi yang jauh dari median. Perbedaan isi adegan dibiarkan. Kekuatan per gaya:
`color_match` di config/styles/*.yaml (0 = mati, bawaan 0,6).
"""

from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import numpy as np

from autoreels.media import ffmpeg_bin

DEFAULT_STRENGTH = 0.6
LUMA_RANGE = (85.0, 160.0)       # kecerahan wajar Reel (0–255); di luar ini pasti dikoreksi
LUMA_BAND = 25.0                 # dalam ±25 dari median Reel = wajar (perbedaan isi adegan, bukan salah eksposur)
GAMMA_LIMIT = (0.8, 1.35)        # eq gamma (>1 = lebih terang)
WB_LIMIT = (0.95, 1.05)          # keseimbangan warna: maks ±5% per kanal
GREY_SAT = 0.15                  # piksel "abu-abu" (jalan, tembok, awan) untuk menaksir warna cahaya
GREY_MIN_SHARE = 0.05            # piksel abu-abu < 5% (mis. penuh dedaunan) → keseimbangan warna tidak disentuh
SAT_LIMIT = (1.0, 1.15)          # saturasi hanya dinaikkan (footage pucat), tidak pernah diturunkan
SAT_DEADBAND = 0.08              # selisih saturasi absolut dari median < 0,08 diabaikan
DEADBAND = 0.03                  # perubahan < 3% diabaikan (footage yang sudah bagus tidak disentuh)
SAMPLE_W, SAMPLE_H = 64, 36


@dataclass
class ColorStats:
    luma: float
    cast: tuple[float, float, float]   # warna cahaya dari piksel abu-abu: R,G,B ÷ rata-rata (1,1,1 = netral)
    sat: float
    grey_share: float = 1.0            # porsi piksel abu-abu (dasar taksiran `cast`)


@dataclass
class Correction:
    gains: tuple[float, float, float]   # keseimbangan warna per kanal (±5%)
    saturation: float
    gamma: float = 1.0                  # kecerahan lewat gamma: nada tengah bergeser, bagian terang tidak terbakar

    def filter(self) -> str:
        parts = []
        if max(abs(g - 1) for g in self.gains) >= DEADBAND / 2:
            r, g, b = self.gains
            parts.append(f"colorchannelmixer=rr={r:.3f}:gg={g:.3f}:bb={b:.3f}")
        eq = []
        if abs(self.gamma - 1) >= DEADBAND:
            eq.append(f"gamma={self.gamma:.3f}")
        if abs(self.saturation - 1) >= DEADBAND:
            eq.append(f"saturation={self.saturation:.3f}")
        if eq:
            parts.append("eq=" + ":".join(eq))
        return ",".join(parts)


def stats_from_rgb(frames: np.ndarray) -> ColorStats:
    """frames: (n, h, w, 3) uint8 RGB. Warna cahaya ditaksir dari piksel hampir abu-abu saja (bukan grey world
    seluruh gambar, yang keliru pada adegan hijau dedaunan/langit biru)."""
    px = frames.reshape(-1, 3).astype(np.float32)
    luma_px = px @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    mx, mn = px.max(axis=1), px.min(axis=1)
    sat_px = np.where(mx > 8, (mx - mn) / np.maximum(mx, 1), 0)
    grey = (sat_px < GREY_SAT) & (luma_px > 30) & (luma_px < 230)
    share = float(grey.mean())
    mean = px[grey].mean(axis=0) if grey.any() else np.ones(3, np.float32)
    level = float(mean.mean()) or 1.0
    return ColorStats(luma=float(luma_px.mean()), cast=tuple(float(c / level) for c in mean),
                      sat=float(sat_px.mean()), grey_share=share)


def measure(path: str | Path, start: float, end: float) -> ColorStats | None:
    """Ukur 3 frame (25%, 50%, 75%) di rentang [start, end]. None bila gagal dibaca."""
    frames = []
    for k in (0.25, 0.5, 0.75):
        t = start + (end - start) * k
        proc = subprocess.run(
            [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(path),
             "-frames:v", "1", "-vf", f"scale={SAMPLE_W}:{SAMPLE_H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True)
        if proc.returncode == 0 and len(proc.stdout) == SAMPLE_W * SAMPLE_H * 3:
            frames.append(np.frombuffer(proc.stdout, np.uint8).reshape(SAMPLE_H, SAMPLE_W, 3))
    return stats_from_rgb(np.stack(frames)) if frames else None


def _clamp(v: float, lo_hi: tuple[float, float]) -> float:
    return min(max(v, lo_hi[0]), lo_hi[1])


def plan_corrections(stats: dict[str, ColorStats], strength: float = DEFAULT_STRENGTH) -> dict[str, Correction]:
    """Koreksi per sumber agar mendekati patokan Reel. stats: kunci sumber → ukuran."""
    if strength <= 0 or len(stats) < 1:
        return {}
    vals = list(stats.values())
    mid = median(s.luma for s in vals)
    lo, hi = max(LUMA_RANGE[0], mid - LUMA_BAND), min(LUMA_RANGE[1], mid + LUMA_BAND)
    greys = [s for s in vals if s.grey_share >= GREY_MIN_SHARE]
    ref_cast = [(median(s.cast[c] for s in greys) + 1.0) / 2 for c in range(3)] if greys else [1.0] * 3
    ref_sat = median(s.sat for s in vals)
    out = {}
    for key, s in stats.items():
        target = min(max(s.luma, lo), hi)  # hanya pencilan (terlalu gelap/terang) yang digeser
        want = s.luma * (target / max(s.luma, 1.0)) ** strength
        # ffmpeg eq: keluaran = masukan^(1/gamma) → gamma = ln(luma)/ln(target) (skala 0–1)
        gamma = _clamp(math.log(min(max(s.luma, 1.0), 254) / 255) / math.log(min(want, 254) / 255), GAMMA_LIMIT)
        if s.grey_share >= GREY_MIN_SHARE:
            wb = [_clamp((ref_cast[c] / max(s.cast[c], 1e-3)) ** strength, WB_LIMIT) for c in range(3)]
            norm = sum(wb) / 3  # rona saja; kecerahan diatur expo
            wb = [w / norm for w in wb]
        else:
            wb = [1.0, 1.0, 1.0]
        gains = tuple(round(w, 3) for w in wb)
        sat = (_clamp((ref_sat / max(s.sat, 1e-3)) ** strength, SAT_LIMIT)
               if abs(s.sat - ref_sat) > SAT_DEADBAND and s.sat > 0.02 else 1.0)
        out[key] = Correction(gains=gains, saturation=round(sat, 3), gamma=round(gamma, 3))
    return out
