"""Blur privasi: wajah (YuNet) dan pelat nomor kendaraan (LPD-YuNet) — CPU, OpenCV, tanpa dependensi baru.

Model ONNX di assets/models/ (sumber & lisensi: assets/models/README.md). Dijalankan pada video gabungan 1080×1920
SEBELUM teks/logo ditempel, jadi teks tidak ikut buram. Deteksi bersifat bantuan: hasil tetap perlu ditinjau
(pelat model dilatih pada pelat Tiongkok; pelat Indonesia bisa terlewat).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np

from autoreels.config import PATHS
from autoreels.media import ffmpeg_bin

FACE_MODEL = PATHS["assets"] / "models" / "face_detection_yunet_2023mar.onnx"
PLATE_MODEL = PATHS["assets"] / "models" / "license_plate_detection_lpd_yunet_2023mar.onnx"

DETECT_EVERY = 3      # deteksi tiap n frame (kotak dipakai juga di frame antaranya)
HOLD_FRAMES = 9       # kotak tetap diblur sekian frame setelah terakhir terdeteksi (anti-kedip)
PAD = 0.25            # perbesar kotak 25% agar tepi wajah/pelat ikut tertutup
FACE_SCORE = 0.8      # teruji 2026-11-20: skor 0,6–0,76 = salah deteksi (pengendara jauh dari belakang)
PLATE_SCORE = 0.6


@dataclass
class PrivacyStats:
    frames: int = 0
    face_frames: int = 0
    plate_frames: int = 0


class PlateDetector:
    """LPD-YuNet (opencv_zoo) — port ringkas dari lpd_yunet.py resmi."""

    MIN_SIZES = [[10, 16, 24], [32, 48], [64, 96], [128, 192, 256]]
    STEPS = [8, 16, 32, 64]
    VARIANCE = 0.1

    def __init__(self, model: Path, size: tuple[int, int] = (432, 768)):
        import cv2

        self.cv2 = cv2
        from autoreels.render.speaker import quiet_opencv

        quiet_opencv()
        self.net = cv2.dnn.readNet(str(model))
        self.w, self.h = size
        self.priors = self._priors()

    def _priors(self) -> np.ndarray:
        w, h = self.w, self.h
        f2 = [int(int((h + 1) / 2) / 2), int(int((w + 1) / 2) / 2)]
        maps = []
        f = f2
        for _ in range(4):
            f = [int(f[0] / 2), int(f[1] / 2)]
            maps.append(f)
        pri = []
        for k, (fh, fw) in enumerate(maps):
            for i, j in product(range(fh), range(fw)):
                for ms in self.MIN_SIZES[k]:
                    pri.append([(j + 0.5) * self.STEPS[k] / w, (i + 0.5) * self.STEPS[k] / h, ms / w, ms / h])
        return np.array(pri, dtype=np.float32)

    def detect(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        cv2 = self.cv2
        fh, fw = frame.shape[:2]
        img = cv2.resize(frame, (self.w, self.h))
        self.net.setInput(cv2.dnn.blobFromImage(img))
        loc, conf, iou = self.net.forward(["loc", "conf", "iou"])
        scores = np.sqrt(conf[:, 1] * np.clip(iou[:, 0], 0, 1))
        keep = scores >= PLATE_SCORE
        if not keep.any():
            return []
        p, l, sc = self.priors[keep], loc[keep], scores[keep]
        scale = np.array([self.w, self.h], dtype=np.float32)
        pts = [(p[:, 0:2] + l[:, a:a + 2] * self.VARIANCE * p[:, 2:4]) * scale for a in (4, 6, 10, 12)]
        corners = np.stack(pts, axis=1)  # N × 4 titik × (x, y)
        x0, y0 = corners[..., 0].min(1), corners[..., 1].min(1)
        x1, y1 = corners[..., 0].max(1), corners[..., 1].max(1)
        rects = [[float(a), float(b), float(c - a), float(d - b)] for a, b, c, d in zip(x0, y0, x1, y1)]
        idx = cv2.dnn.NMSBoxes(rects, sc.tolist(), PLATE_SCORE, 0.3)
        sx, sy = fw / self.w, fh / self.h
        return [(int(rects[i][0] * sx), int(rects[i][1] * sy), int(rects[i][2] * sx), int(rects[i][3] * sy))
                for i in np.array(idx).flatten()]


class FaceDetector:
    def __init__(self, model: Path, size: tuple[int, int] = (540, 960)):
        import cv2

        self.cv2 = cv2
        self.size = size
        self.det = cv2.FaceDetectorYN.create(str(model), "", size, FACE_SCORE, 0.3, 50)

    def detect(self, frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        fh, fw = frame.shape[:2]
        img = self.cv2.resize(frame, self.size)
        _, faces = self.det.detect(img)
        if faces is None:
            return []
        sx, sy = fw / self.size[0], fh / self.size[1]
        return [(int(f[0] * sx), int(f[1] * sy), int(f[2] * sx), int(f[3] * sy)) for f in faces]


def _blur_box(frame: np.ndarray, box: tuple[int, int, int, int], cv2) -> None:
    x, y, w, h = box
    px, py = int(w * PAD), int(h * PAD)
    x0, y0 = max(0, x - px), max(0, y - py)
    x1, y1 = min(frame.shape[1], x + w + px), min(frame.shape[0], y + h + py)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return
    roi = frame[y0:y1, x0:x1]
    # piksel besar + gaussian: tidak bisa dibaca/dikenali lagi
    small = cv2.resize(roi, (max(1, (x1 - x0) // 16), max(1, (y1 - y0) // 16)), interpolation=cv2.INTER_LINEAR)
    roi[:] = cv2.GaussianBlur(cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST), (0, 0), 6)


def blur_video(src: Path, dst: Path, *, faces: bool, plates: bool, preview: bool = False, log=print) -> PrivacyStats:
    """Baca `src`, samarkan wajah/pelat per frame, tulis `dst` (H.264, tanpa audio, fps sama)."""
    import cv2

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise RuntimeError(f"Video tidak bisa dibaca untuk blur privasi: {src}")
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    face_det = FaceDetector(FACE_MODEL) if faces and FACE_MODEL.exists() else None
    plate_det = PlateDetector(PLATE_MODEL) if plates and PLATE_MODEL.exists() else None
    if faces and face_det is None:
        log(f"  [peringatan] model wajah tidak ada: {FACE_MODEL}")
    if plates and plate_det is None:
        log(f"  [peringatan] model pelat tidak ada: {PLATE_MODEL}")

    enc = subprocess.Popen(
        [ffmpeg_bin(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
         "-r", f"{fps:g}", "-i", "-", "-c:v", "libx264", "-preset", "ultrafast" if preview else "veryfast",
         "-crf", "17", "-pix_fmt", "yuv420p", str(dst)],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    stats = PrivacyStats()
    held: dict[str, list[tuple[tuple[int, int, int, int], int]]] = {"face": [], "plate": []}
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            i = stats.frames
            for kind, det in (("face", face_det), ("plate", plate_det)):
                if det is None:
                    continue
                if i % DETECT_EVERY == 0:
                    found = det.detect(frame)
                    held[kind] = [(b, i) for b in found] + [(b, t) for b, t in held[kind] if i - t <= HOLD_FRAMES]
                held[kind] = [(b, t) for b, t in held[kind] if i - t <= HOLD_FRAMES]
                if held[kind]:
                    if kind == "face":
                        stats.face_frames += 1
                    else:
                        stats.plate_frames += 1
                for box, _ in held[kind]:
                    _blur_box(frame, box, cv2)
            enc.stdin.write(frame.tobytes())
            stats.frames += 1
    finally:
        cap.release()
        enc.stdin.close()
        err = enc.stderr.read().decode("utf-8", "replace")
        enc.wait()
    if enc.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal menulis video blur privasi:\n{err}")
    return stats
