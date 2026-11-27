"""Deteksi objek (motor, orang, mobil, …) untuk crop pengikut subjek — NanoDet-Plus via OpenCV DNN (CPU).

Model: assets/models/object_detection_nanodet_2022nov.onnx (opencv_zoo, Apache 2.0, kelas COCO). Port ringkas dari
nanodet.py resmi opencv_zoo: letterbox 416×416, normalisasi, dekode distribusi jarak (GFL), NMS.
Model tidak ada → None (crop kembali ke saliency; analisis tetap jalan).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from autoreels.config import PATHS

MODEL = PATHS["assets"] / "models" / "object_detection_nanodet_2022nov.onnx"
SIZE = 416
REG_MAX = 7
SCORE_MIN = 0.35
IOU = 0.6
MEAN = np.array([103.53, 116.28, 123.675], np.float32)
STD = np.array([57.375, 57.12, 58.395], np.float32)
# kelas COCO yang layak jadi subjek Reel Brand, dengan bobot prioritas (motor paling penting untuk pilar rental)
SUBJECT_WEIGHT = {3: 1.5, 0: 1.0, 1: 1.0, 2: 0.8, 5: 0.7, 7: 0.8}  # motor, orang, sepeda, mobil, bus, truk


@lru_cache(maxsize=1)
def _net():
    import cv2

    if not MODEL.exists():
        return None
    return cv2.dnn.readNet(str(MODEL))


@lru_cache(maxsize=8)
def _anchors(n: int) -> tuple[int, np.ndarray]:
    """(stride, titik pusat) untuk peta fitur n×n."""
    s = SIZE // n
    xv, yv = np.meshgrid(np.arange(n) * s, np.arange(n) * s)
    return s, np.column_stack((xv.ravel() + 0.5 * (s - 1), yv.ravel() + 0.5 * (s - 1)))


def detect(frame_bgr: np.ndarray) -> list[tuple[float, float, float, float, float, int]] | None:
    """[(x1, y1, x2, y2 relatif 0–1, skor, kelas COCO)] atau None bila model tidak tersedia."""
    import cv2

    net = _net()
    if net is None:
        return None
    h, w = frame_bgr.shape[:2]
    k = SIZE / max(h, w)
    img = cv2.resize(frame_bgr, (round(w * k), round(h * k)))
    pad = np.zeros((SIZE, SIZE, 3), np.float32)
    top = (SIZE - img.shape[0]) // 2
    pad[top:top + img.shape[0], :img.shape[1]] = img
    net.setInput(cv2.dnn.blobFromImage((pad - MEAN) / STD))
    outs = [o.reshape(-1, o.shape[-1]) for o in net.forward(net.getUnconnectedOutLayersNames())]
    # urutan keluaran berbeda antar versi OpenCV → pasangkan skor kelas (80) & jarak kotak (32) per jumlah titik
    regs = {len(o): o for o in outs if o.shape[1] == 4 * (REG_MAX + 1)}
    boxes, scores = [], []
    for cls in (o for o in outs if o.shape[1] != 4 * (REG_MAX + 1)):
        reg = regs[len(cls)]
        stride, anc = _anchors(round(len(cls) ** 0.5))
        e = np.exp(reg.reshape(-1, REG_MAX + 1))
        dist = ((e / e.sum(axis=1, keepdims=True)) @ np.arange(REG_MAX + 1)).reshape(-1, 4) * stride
        boxes.append(np.column_stack([anc[:, 0] - dist[:, 0], anc[:, 1] - dist[:, 1],
                                      anc[:, 0] + dist[:, 2], anc[:, 1] + dist[:, 3]]).clip(0, SIZE))
        scores.append(cls)
    boxes, scores = np.concatenate(boxes), np.concatenate(scores)
    cls_id, conf = scores.argmax(axis=1), scores.max(axis=1)
    keep = conf >= SCORE_MIN
    if not keep.any():
        return []
    b, c, s = boxes[keep], cls_id[keep], conf[keep]
    idx = cv2.dnn.NMSBoxes(np.column_stack([b[:, :2], b[:, 2:] - b[:, :2]]).tolist(), s.tolist(), SCORE_MIN, IOU)
    out = []
    for i in np.asarray(idx).ravel():
        x1, y1, x2, y2 = b[i]
        out.append((x1 / k / w, (y1 - top) / k / h, x2 / k / w, (y2 - top) / k / h, float(s[i]), int(c[i])))
    return out


def main_subject(frame_bgr: np.ndarray) -> tuple[float, float] | None:
    """(pusat horizontal 0–1, luas relatif frame) subjek utama: bobot kelas × skor × ukuran terbesar."""
    dets = detect(frame_bgr)
    if not dets:
        return None
    best = max((d for d in dets if d[5] in SUBJECT_WEIGHT),
               key=lambda d: SUBJECT_WEIGHT[d[5]] * d[4] * np.sqrt((d[2] - d[0]) * (d[3] - d[1])), default=None)
    if best is None:
        return None
    return float((best[0] + best[2]) / 2), float(max(0.0, (best[2] - best[0]) * (best[3] - best[1])))


def subject_cx(frame_bgr: np.ndarray) -> float | None:
    """Pusat horizontal (0–1) subjek utama, atau None."""
    found = main_subject(frame_bgr)
    return None if found is None else found[0]
