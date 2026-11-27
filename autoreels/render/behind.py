"""Teks hook di belakang orang (gaya "text behind subject").

Mask orang per frame selama hook dari PP-HumanSeg (opencv_zoo, Apache 2.0, `cv2.dnn`, ±11 ms/frame CPU).
Teks hook dirender seperti biasa, lalu piksel orang dari video asli ditempel lagi di atasnya (ffmpeg alphamerge +
overlay) → huruf tampak berada di belakang kepala/badan. Posisi teks dipilih agar orang hanya menutupi
bagian bawah huruf (separuh atas tetap bersih → terbaca). Tidak ada orang / orang terlalu tinggi / tertutup terlalu banyak → None (hook biasa).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from autoreels.config import PATHS
from autoreels.media import ffmpeg_bin
from autoreels.render.reframe import OUT_H, OUT_W

MODEL = PATHS["assets"] / "models" / "human_segmentation_pphumanseg_2023mar.onnx"
NET_SIZE = 192
BEHIND_SIZE = 150          # ukuran huruf hook di belakang orang (lebih besar dari hook biasa)
BEHIND_CHARS = 11          # huruf per baris pada ukuran itu
COVER_MIN, COVER_MAX = 0.12, 0.5   # tutupan separuh bawah huruf: minimal agar efek terlihat, batas atas skor
TOP_HIT_MAX = 0.03         # separuh atas tiap baris maks 3% tertutup (kata tetap terbaca)
SAFE_TOP = int(OUT_H * 0.15)
EMA = 0.6                  # penghalus mask antar frame (mengurangi kedip tepi)


@dataclass
class BehindPlan:
    y: int                 # pusat vertikal teks
    size: int              # ukuran font
    lines: list[str]
    cover: float           # porsi teks yang tertutup orang


def available() -> bool:
    return MODEL.exists()


def _net():
    return cv2.dnn.readNet(str(MODEL))


def person_prob(net, frame: np.ndarray) -> np.ndarray:
    """Peluang piksel = orang (float32 0–1) seukuran frame."""
    h, w = frame.shape[:2]
    x = cv2.cvtColor(cv2.resize(frame, (NET_SIZE, NET_SIZE)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    net.setInput(((x - 0.5) / 0.5).transpose(2, 0, 1)[None])
    out = net.forward()[0]
    e = np.exp(out - out.max(0))
    return cv2.resize(e[1] / e.sum(0), (w, h), interpolation=cv2.INTER_LINEAR)


def hook_masks(video: Path, t_end: float, fps: int = 30) -> list[np.ndarray]:
    """Mask orang (uint8 0–255, tepi dilembutkan) tiap frame 0..t_end dari video.mp4 (1080×1920, sebelum teks)."""
    net, cap = _net(), cv2.VideoCapture(str(video))
    masks, prev = [], None
    for _ in range(max(1, round(t_end * fps))):
        ok, frame = cap.read()
        if not ok:
            break
        p = person_prob(net, frame)
        prev = p if prev is None else EMA * p + (1 - EMA) * prev
        m = cv2.GaussianBlur(np.clip((prev - 0.35) / 0.3, 0, 1), (9, 9), 0)
        masks.append((m * 255).astype(np.uint8))
    cap.release()
    return masks


def _text_box(lines: list[str], size: int, y: int) -> tuple[int, int, int, int]:
    width = min(OUT_W - 120, int(max(len(x) for x in lines) * size * 0.62))
    height = int(len(lines) * size * 1.12)
    x0 = (OUT_W - width) // 2
    return x0, y - height // 2, x0 + width, y + height // 2


def plan_behind(masks: list[np.ndarray], text: str) -> BehindPlan | None:
    """Pilih posisi teks: separuh atas huruf bersih, separuh bawah sebanyak mungkin di belakang orang."""
    from autoreels.render.text_ass import fit_text

    if not masks or not text.strip():
        return None
    frac = np.mean([m > 127 for m in masks], axis=0)    # porsi frame hook yang piksel ini berisi orang
    strong, ever = frac > 0.5, frac > 0.15
    if strong.mean() < 0.03:  # tidak ada orang berarti
        return None
    lines, size = fit_text(text, BEHIND_SIZE, BEHIND_CHARS)
    best: BehindPlan | None = None
    line_h = int(size * 1.12)
    half = len(lines) * line_h // 2
    for y in range(SAFE_TOP + half, int(OUT_H * 0.55), 8):
        _, y0, _, _ = _text_box(lines, size, y)
        # Gaya "di belakang orang" yang tetap terbaca: kepala/badan hanya boleh menutup BAGIAN BAWAH huruf.
        # Separuh atas tiap baris harus bersih di semua frame hook; efek diukur dari tutupan separuh bawah.
        top_hit, bottom = 0.0, []
        for i, line in enumerate(lines):
            lw = min(OUT_W - 120, int(len(line) * size * 0.62))
            lx0, ly0 = (OUT_W - lw) // 2, y0 + i * line_h
            top = ever[ly0 + int(0.12 * line_h):ly0 + int(0.5 * line_h), lx0:lx0 + lw]
            bot = strong[ly0 + int(0.5 * line_h):ly0 + int(0.88 * line_h), lx0:lx0 + lw]
            top_hit = max(top_hit, float(top.mean()) if top.size else 1.0)
            bottom.append(float(bot.mean()) if bot.size else 0.0)
        effect = max(bottom)
        if top_hit > TOP_HIT_MAX or effect < COVER_MIN:
            continue
        if best is None or min(effect, COVER_MAX) > min(best.cover, COVER_MAX):
            best = BehindPlan(y=y, size=size, lines=lines, cover=round(effect, 2))
    return best


def write_mask_video(masks: list[np.ndarray], path: Path, fps: int = 30) -> Path:
    """Mask → video abu-abu lossless (dipakai ffmpeg alphamerge)."""
    proc = subprocess.Popen([ffmpeg_bin(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
                             "-s", f"{OUT_W}x{OUT_H}", "-r", str(fps), "-i", "-", "-c:v", "ffv1", str(path)],
                            stdin=subprocess.PIPE)
    for m in masks:
        proc.stdin.write(m.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError(f"gagal menulis video mask: {path}")
    return path


def cover_mask(video: Path, at: float, path: Path) -> Path | None:
    """Mask orang untuk satu frame cover (PNG abu-abu)."""
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_MSEC, at * 1000)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return None
    m = cv2.GaussianBlur(np.clip((person_prob(_net(), frame) - 0.35) / 0.3, 0, 1), (9, 9), 0)
    cv2.imwrite(str(path), (m * 255).astype(np.uint8))
    return path
