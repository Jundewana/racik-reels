"""Skor momen di dalam adegan: bagian mana dari adegan yang paling layak dipotong.

Per sampel (5/dtk, dari analisis kualitas): subjek (motor/orang) terlihat utuh & cukup besar, ketajaman relatif
terhadap adegannya, kamera stabil, kecerahan wajar. Disimpan sebagai `Scene.moment_curve` [[detik, skor 0–1], …].
Director diberi tahu momen terbaik tiap adegan; validasi menggeser potongan b-roll ke momen terbaik bila pilihan
Director jauh lebih buruk (Director memilih adegan dari deskripsi 1–3 frame, jadi tidak tahu detik terbaiknya).
"""

from __future__ import annotations

import numpy as np

EDGE = 0.12            # subjek dengan pusat < 12% dari tepi frame = terpotong / baru masuk
SUBJECT_AREA_FULL = 0.06   # luas kotak subjek ≥ 6% frame = cukup besar (skor ukuran penuh)
WEIGHTS = {"subject": 0.4, "sharp": 0.25, "stable": 0.25, "exposure": 0.1}


def sample_scores(samples) -> list[float]:
    """Skor 0–1 per sampel di satu adegan (FrameSample dari analyze/quality.py)."""
    if not samples:
        return []
    sharp = np.array([s.sharpness for s in samples], float)
    ref = float(np.median(sharp)) or 1.0
    any_subject = any(s.tracked for s in samples)
    out = []
    for k, s in enumerate(samples):
        sharp_n = min(1.0, s.sharpness / (ref * 1.2))
        if k:
            jump = float(np.hypot(s.dx - samples[k - 1].dx, s.dy - samples[k - 1].dy))
        else:
            jump = 0.0
        stable = 1.0 - min(1.0, jump / 3.0)
        exposure = 1.0 if 40 <= s.brightness <= 220 else 0.4
        if not any_subject:
            subject = 0.5  # adegan tanpa objek (pemandangan): netral, ditentukan kualitas gambar
        elif not s.tracked:
            subject = 0.0
        else:
            inside = EDGE <= s.subject_x <= 1 - EDGE
            size = min(1.0, s.subject_area / SUBJECT_AREA_FULL)
            subject = (0.6 if inside else 0.2) + 0.4 * size
        out.append(WEIGHTS["subject"] * subject + WEIGHTS["sharp"] * sharp_n + WEIGHTS["stable"] * stable
                   + WEIGHTS["exposure"] * exposure)
    return [round(float(x), 3) for x in out]


def window_score(curve: list[list[float]], start: float, end: float) -> float | None:
    """Rata-rata skor sampel di [start, end]; None bila tidak ada sampel (kurva kosong/di luar jangkauan)."""
    vals = [v for t, v in curve if start - 1e-6 <= t <= end + 1e-6]
    if not vals:
        near = [v for t, v in curve if start - 0.2 <= t <= end + 0.2]
        return float(np.mean(near)) if near else None
    return float(np.mean(vals))


def best_window(curve: list[list[float]], lo: float, hi: float, length: float,
                avoid: list[tuple[float, float]] | None = None) -> tuple[float, float] | None:
    """(mulai, skor) jendela sepanjang `length` dengan skor tertinggi di [lo, hi], tidak menimpa `avoid`."""
    if not curve or hi - lo < length - 1e-6:
        return None
    best = None
    for t in np.arange(lo, hi - length + 1e-6, 0.1):
        a, b = float(t), float(t) + length
        if any(a < y and x < b for x, y in avoid or []):
            continue
        sc = window_score(curve, a, b)
        if sc is not None and (best is None or sc > best[1] + 1e-9):
            best = (round(a, 3), sc)
    return best


def top_moments(curve: list[list[float]], start: float, end: float, length: float = 2.0) -> str:
    """Ringkasan untuk Director: rentang momen terbaik adegan, mis. '3.2–5.2'. Kosong bila adegan pendek/datar."""
    if end - start < length + 0.6:
        return ""
    found = best_window(curve, start, end, length)
    if found is None:
        return ""
    whole = window_score(curve, start, end) or 0.0
    if found[1] - whole < 0.05:  # adegan merata — tidak ada momen yang menonjol
        return ""
    return f"{found[0]:.1f}–{found[0] + length:.1f}"
