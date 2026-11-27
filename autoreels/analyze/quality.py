"""Skor kualitas per adegan: ketajaman, kecerahan, goyangan — plus jejak crop subjek.

Satu kali baca proxy per klip (sampel 5 fps), lalu metrik diagregasi per adegan.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from autoreels.analyze.models import Scene
from autoreels.analyze.moments import sample_scores
from autoreels.analyze.objects import main_subject
from autoreels.analyze.subjects import SUBJECT_BIAS, clamp_cx, saliency_cx, smooth

SAMPLE_FPS = 5.0

# Ambang "unusable" (proxy 480p). Disetel konservatif: lebih baik membuang footage jelek.
MIN_SHARPNESS = 12.0
MIN_BRIGHTNESS = 35.0
MAX_BRIGHTNESS = 240.0
MAX_SHAKE = 6.0


@dataclass
class FrameSample:
    t: float
    sharpness: float
    brightness: float
    dx: float
    dy: float
    cx: float
    tracked: bool = False  # cx dari objek terdeteksi (motor/orang/…), bukan saliency
    subject_x: float = 0.5     # posisi asli subjek (0–1, sebelum bias & batas crop) — skor momen
    subject_area: float = 0.0  # luas kotak subjek relatif frame


def sample_clip(proxy: Path) -> tuple[list[FrameSample], float]:
    import cv2

    cap = cv2.VideoCapture(str(proxy))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV tidak bisa membuka {proxy}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps / SAMPLE_FPS))
    samples: list[FrameSample] = []
    prev_small = None
    window = None
    idx = 0
    width_ratio = 1.0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            width_ratio = w / h
            sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            bright = float(gray.mean())
            small = cv2.resize(gray, (320, int(320 * h / w))).astype(np.float32)
            if window is None:
                window = cv2.createHanningWindow((small.shape[1], small.shape[0]), cv2.CV_32F)
            dx = dy = 0.0
            if prev_small is not None:
                (dx, dy), _ = cv2.phaseCorrelate(prev_small, small, window)
            prev_small = small
            subj = main_subject(frame)
            cx = 0.5 + SUBJECT_BIAS * (subj[0] - 0.5) if subj is not None else saliency_cx(gray)
            samples.append(FrameSample(idx / fps, sharp, bright, float(dx), float(dy), cx, subj is not None,
                                       *(subj or (0.5, 0.0))))
        idx += 1
    cap.release()
    for s in samples:  # penghalusan per adegan di score_scene (tidak melintasi potongan adegan)
        s.cx = clamp_cx(s.cx, width_ratio)
    return samples, width_ratio


MAX_PAN_PER_SEC = 0.4  # geser crop maks 40% lebar frame per detik
TRACK_SHARE = 0.4  # porsi sampel berobjek agar adegan dianggap punya subjek yang diikuti
HOLD_SEC = 0.6  # objek sesaat tak terdeteksi (blur gerak/tertutup) → posisi terakhirnya dipertahankan


def crop_track(inside: list[FrameSample]) -> list[float]:
    """Jejak pusat crop per sampel. Adegan dengan objek (motor/orang) di ≥ 40% sampel: celah deteksi diisi interpolasi
    antar deteksi (tepi adegan = deteksi terdekat), bukan saliency. Selain itu: saliency, dengan posisi objek terakhir
    ditahan sebentar. Lalu dihaluskan ±0,4 dtk agar kamera virtual tidak bergetar tapi tetap mengejar subjek cepat."""
    hits = [s for s in inside if s.tracked]
    if len(hits) >= max(2, TRACK_SHARE * len(inside)):
        xs = np.interp([s.t for s in inside], [s.t for s in hits], [s.cx for s in hits]).tolist()
    else:
        xs, last = [], None
        for s in inside:
            if s.tracked:
                last = (s.t, s.cx)
                xs.append(s.cx)
            elif last is not None and s.t - last[0] <= HOLD_SEC:
                xs.append(last[1])
            else:
                xs.append(s.cx)
    xs = smooth(xs, window=5) if len(xs) >= 5 else xs
    for k in range(1, len(xs)):  # batas kecepatan geser: deteksi yang pindah objek tidak membuat crop melompat
        step = MAX_PAN_PER_SEC * max(inside[k].t - inside[k - 1].t, 1e-3)
        xs[k] = xs[k - 1] + max(-step, min(step, xs[k] - xs[k - 1]))
    return xs


def score_scene(scene: Scene, samples: list[FrameSample]) -> Scene:
    inside = [s for s in samples if scene.start <= s.t < scene.end]
    if len(inside) < 2:
        inside = sorted(samples, key=lambda s: abs(s.t - (scene.start + scene.end) / 2))[:2]
    sharp = float(np.median([s.sharpness for s in inside]))
    bright = float(np.mean([s.brightness for s in inside]))
    shifts = np.array([[s.dx, s.dy] for s in inside[1:]]) if len(inside) > 1 else np.zeros((1, 2))
    motion = float(np.linalg.norm(shifts, axis=1).mean())
    jitter = np.linalg.norm(np.diff(shifts, axis=0), axis=1) if len(shifts) > 1 else np.zeros(1)
    shake = float(np.median(jitter))

    reasons = []
    if sharp < MIN_SHARPNESS:
        reasons.append(f"blur (ketajaman {sharp:.0f} < {MIN_SHARPNESS:.0f})")
    if bright < MIN_BRIGHTNESS:
        reasons.append(f"terlalu gelap (kecerahan {bright:.0f})")
    if bright > MAX_BRIGHTNESS:
        reasons.append(f"terlalu terang (kecerahan {bright:.0f})")
    if shake > MAX_SHAKE:
        reasons.append(f"goyang (jitter {shake:.1f}px)")

    track = crop_track(inside)
    n = len(inside)
    head = track[: max(1, n // 4)]
    tail = track[-max(1, n // 4):]
    return scene.model_copy(update={
        "sharpness": round(sharp, 1),
        "brightness": round(bright, 1),
        "shake": round(shake, 2),
        "motion": round(motion, 2),
        "usable": not reasons,
        "reasons": reasons,
        "crop_cx_start": round(float(np.mean(head)), 3),
        "crop_cx_end": round(float(np.mean(tail)), 3),
        "crop_path": [[round(s.t, 2), round(float(x), 3)] for s, x in zip(inside, track)],
        "moment_curve": [[round(s.t, 2), v] for s, v in zip(inside, sample_scores(inside))],
    })
