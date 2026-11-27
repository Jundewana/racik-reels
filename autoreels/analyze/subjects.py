"""Titik fokus subjek untuk crop 9:16 — saliency spectral residual (numpy/OpenCV, CPU).

Objek (motor, orang, mobil) dideteksi lebih dulu oleh analyze/objects.py; saliency dipakai bila tak ada objek.
"""

from __future__ import annotations

import numpy as np

# Lebar crop 9:16 dari video 16:9 = (9/16) / (16/9) ≈ 0.316 lebar sumber.
CENTER_BIAS = 0.6  # 0 = selalu tengah, 1 = ikut saliency penuh


def saliency_cx(gray: np.ndarray) -> float:
    """Kembalikan posisi horizontal (0–1) pusat perhatian visual dalam frame abu-abu."""
    import cv2

    h, w = gray.shape[:2]
    small = cv2.resize(gray, (64, 64)).astype(np.float32)
    spectrum = np.fft.fft2(small)
    log_amp = np.log(np.abs(spectrum) + 1e-8)
    phase = np.angle(spectrum)
    residual = log_amp - cv2.blur(log_amp, (3, 3))
    sal = np.abs(np.fft.ifft2(np.exp(residual + 1j * phase))) ** 2
    sal = cv2.GaussianBlur(sal.astype(np.float32), (9, 9), 2.5)
    sal = cv2.resize(sal, (max(16, int(64 * w / h)), 64))
    weights = sal.sum(axis=0)
    total = float(weights.sum())
    if total <= 0:
        return 0.5
    xs = np.linspace(0, 1, len(weights))
    cx = float((xs * weights).sum() / total)
    return 0.5 + CENTER_BIAS * (cx - 0.5)


SUBJECT_BIAS = 0.95  # objek terdeteksi (motor/orang): hampir tidak ditarik ke tengah (harus diikuti)


def smooth(values: list[float], window: int = 5) -> list[float]:
    if len(values) < 3:
        return values
    arr = np.asarray(values, dtype=float)
    pad = window // 2
    padded = np.pad(arr, pad, mode="edge")
    kernel = np.ones(window) / window
    return np.convolve(padded, kernel, mode="valid").tolist()


def clamp_cx(cx: float, src_aspect: float, out_aspect: float = 9 / 16) -> float:
    """Batasi pusat crop agar jendela crop tidak keluar frame."""
    half = min(0.5, (out_aspect / src_aspect) / 2)
    return min(1 - half, max(half, cx))
