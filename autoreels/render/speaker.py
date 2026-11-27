"""Fokus ke pembicara (video bicara): crop 9:16 yang di-zoom ke wajah orang yang sedang bicara.

Video bicara sering punya beberapa tata letak (layar penuh di podium, galeri Zoom berdampingan dengan penonton,
sorotan ke hadirin). Crop geser kiri–kanan biasa memotong di tengah dua panel. Di sini, untuk tiap segmen pembicara:
wajah dideteksi (YuNet, CPU) pada beberapa frame; pembicara = wajah yang menonjol dan TERPISAH dari kerumunan
(penonton bergerombol, pembicara sendirian di panel/podium). Crop dipusatkan ke wajah itu dengan bingkai
setengah badan. Tidak ada wajah pembicara (mis. kamera menyorot hadirin) → None, crop biasa dipakai.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from autoreels.render.privacy import FACE_MODEL, FACE_SCORE

DETECT_SCALE = 2.0        # perbesar frame sebelum deteksi: wajah di panel galeri kecil (±12 px di 720p)
SAMPLES = 5               # frame yang diperiksa per segmen
MIN_HIT_RATIO = 0.4       # wajah pembicara harus terlihat di ≥ 40% sampel
NEIGHBOR_RADIUS = 3.0     # wajah lain dalam radius (× ukuran wajah) = kerumunan
FACE_TO_CROP = 6.5        # tinggi crop = 6,5 × tinggi wajah (setengah badan)
MIN_CROP_H = 0.40         # zoom maksimal: crop setinggi ≥ 40% frame (lebih kecil terlalu pecah)
FACE_Y = 0.32             # posisi wajah dari atas crop


@dataclass
class CropBox:
    x: int
    y: int
    w: int
    h: int
    face: tuple[float, float] | None = field(default=None, compare=False)  # (pusat y, tinggi) wajah di sumber

    def face_out(self, out_h: int) -> tuple[int, int] | None:
        """Rentang vertikal kepala (rambut–dagu) di video jadi, piksel; None bila tidak diketahui."""
        if self.face is None:
            return None
        cy, fh = self.face
        k = out_h / self.h
        return int((cy - 0.8 * fh - self.y) * k), int((cy + 0.55 * fh - self.y) * k)  # rambut, dagu


_DETECTORS: dict[tuple[int, int], object] = {}


def quiet_opencv() -> None:
    """Sembunyikan peringatan OpenCV yang tidak berbahaya ("setPreferableTarget ... not supported") — error tetap tampil."""
    import cv2

    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    except AttributeError:  # build OpenCV tanpa modul logging
        pass


def _detector(size: tuple[int, int]):
    """Detektor wajah YuNet dipakai ulang per ukuran input (dulu dibuat ulang tiap potongan: lambat & berisik)."""
    import cv2

    det = _DETECTORS.get(size)
    if det is None:
        quiet_opencv()
        det = cv2.FaceDetectorYN.create(str(FACE_MODEL), "", size, FACE_SCORE, 0.3, 200)
        _DETECTORS[size] = det
    return det


def pick_speaker(faces: list[tuple[int, int, int, int]], frame_h: int) -> tuple[int, int, int, int] | None:
    """Pilih wajah pembicara: besar dan sendirian (skor = luas / (1 + jumlah tetangga dekat))."""
    cand = [f for f in faces if f[3] >= frame_h * 0.012]
    if not cand:
        return None
    best, best_score = None, 0.0
    for f in cand:
        cx, cy, size = f[0] + f[2] / 2, f[1] + f[3] / 2, max(f[2], f[3])
        neighbors = sum(1 for g in cand if g is not f
                        and np.hypot(g[0] + g[2] / 2 - cx, g[1] + g[3] / 2 - cy) < NEIGHBOR_RADIUS * size)
        score = f[2] * f[3] / (1 + neighbors) ** 2
        if score > best_score:
            best, best_score = f, score
    if best is None:
        return None
    # di tengah kerumunan (≥ 3 tetangga) = penonton, bukan pembicara
    size = max(best[2], best[3])
    cx, cy = best[0] + best[2] / 2, best[1] + best[3] / 2
    crowd = sum(1 for g in cand if g is not best
                and np.hypot(g[0] + g[2] / 2 - cx, g[1] + g[3] / 2 - cy) < NEIGHBOR_RADIUS * size)
    return None if crowd >= 3 else best


def crop_for_face(face: tuple[float, float, float], width: int, height: int, out_aspect: float = 9 / 16) -> CropBox:
    """face = (cx, cy, tinggi wajah) → kotak crop 9:16 setengah badan, di dalam frame, ukuran genap."""
    cx, cy, fh = face
    ch = min(height, max(height * MIN_CROP_H, fh * FACE_TO_CROP))
    cw = ch * out_aspect
    if cw > width:
        cw, ch = width, width / out_aspect
    x = min(max(0.0, cx - cw / 2), width - cw)
    y = min(max(0.0, cy - ch * FACE_Y), height - ch)
    even = lambda v: int(v) // 2 * 2  # noqa: E731
    return CropBox(even(x), even(y), even(cw), even(ch), face=(cy, fh))


ACTIVE_MAX_FACES = 4      # 2–4 wajah (podcast/wawancara) → pilih dari gerak bibir; lebih banyak = kerumunan
ACTIVE_RATIO = 1.3        # gerak mulut pembicara harus ≥ 1,3× wajah lain agar dianggap jelas
FRAME_STEP = 2            # bandingkan frame ke-0, ke-2, ke-4 (±67 ms per langkah di 30 fps)


def mouth_motion(frames: list, face) -> float:
    """Gerak area mulut di antara frame berurutan, dikurangi gerak area mata (gerak kepala/kamera).
    face = baris YuNet: x, y, w, h, 5 landmark (mata kanan, mata kiri, hidung, mulut kanan, mulut kiri), skor."""
    x, y, w, h = (float(v) for v in face[:4])
    nose_y = float(face[9])
    mouth_y = (float(face[11]) + float(face[13])) / 2
    mx0, mx1 = float(face[10]) - 0.15 * w, float(face[12]) + 0.15 * w
    my0, my1 = (nose_y + mouth_y) / 2, mouth_y + 0.25 * h
    ey0, ey1 = y + 0.15 * h, nose_y - 0.05 * h

    def region(img, x0, x1, y0, y1):
        H, W = img.shape[:2]
        x0, x1 = int(max(0, min(W, x0))), int(max(0, min(W, x1)))
        y0, y1 = int(max(0, min(H, y0))), int(max(0, min(H, y1)))
        return img[y0:y1, x0:x1].astype(np.float32) if x1 - x0 >= 3 and y1 - y0 >= 3 else None

    total = 0.0
    for a, b in zip(frames, frames[1:]):
        ma, mb = region(a, mx0, mx1, my0, my1), region(b, mx0, mx1, my0, my1)
        ea, eb = region(a, x + 0.1 * w, x + 0.9 * w, ey0, ey1), region(b, x + 0.1 * w, x + 0.9 * w, ey0, ey1)
        if ma is None or mb is None:
            continue
        head = float(np.abs(ea - eb).mean()) if ea is not None and eb is not None else 0.0
        total += max(0.0, float(np.abs(ma - mb).mean()) - head)
    return total / max(1, len(frames) - 1)


def pick_active(samples: list[list[tuple]], frame_h: int) -> tuple[float, float, float] | None:
    """samples: per waktu sampel, daftar (cx, cy, tinggi_wajah, gerak_mulut). Kelompokkan wajah yang sama
    (posisi berdekatan) lintas sampel, pilih yang gerak mulutnya jelas paling besar. Tidak jelas → None."""
    clusters: list[dict] = []
    for faces in samples:
        for cx, cy, fh, motion in faces:
            c = next((c for c in clusters if np.hypot(c["cx"] - cx, c["cy"] - cy) < fh), None)
            if c is None:
                clusters.append({"cx": cx, "cy": cy, "fh": fh, "motion": [motion], "pos": [(cx, cy, fh)]})
            else:
                c["motion"].append(motion)
                c["pos"].append((cx, cy, fh))
    clusters = [c for c in clusters if len(c["motion"]) >= max(1, MIN_HIT_RATIO * len(samples))]
    if not clusters:
        return None
    if len(clusters) == 1:
        c = clusters[0]
        return tuple(np.median(np.asarray(c["pos"]), axis=0))
    ranked = sorted(clusters, key=lambda c: -float(np.mean(c["motion"])))
    best, second = float(np.mean(ranked[0]["motion"])), float(np.mean(ranked[1]["motion"]))
    if best <= 0.5 or best < ACTIVE_RATIO * second:
        return None
    return tuple(np.median(np.asarray(ranked[0]["pos"]), axis=0))


def speaker_crop(video: Path, start: float, end: float, width: int, height: int) -> CropBox | None:
    """Kotak crop ke pembicara untuk rentang [start, end] video sumber, atau None bila pembicara tidak tampak.
    2–4 wajah → pembicara aktif dari gerak bibir; kerumunan → wajah yang terpisah (panel/podium)."""
    import cv2

    if not FACE_MODEL.exists():
        return None
    size = (int(width * DETECT_SCALE), int(height * DETECT_SCALE))
    det = _detector(size)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    isolated, active, crowded = [], [], 0
    times = np.linspace(start + 0.05, max(start + 0.06, end - 0.3), SAMPLES)
    try:
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000)
            frames = []
            for k in range(2 * FRAME_STEP + 1):
                ok, frame = cap.read()
                if not ok:
                    break
                if k % FRAME_STEP == 0:
                    frames.append(frame)
            if not frames:
                continue
            _, found = det.detect(cv2.resize(frames[0], size))
            rows = [] if found is None else [f / np.array([DETECT_SCALE] * 14 + [1.0]) for f in found]
            boxes = [(int(f[0]), int(f[1]), int(f[2]), int(f[3])) for f in rows]
            sp = pick_speaker(boxes, height)
            if sp is not None:
                isolated.append((sp[0] + sp[2] / 2, sp[1] + sp[3] / 2, sp[3]))
            big = [f for f in rows if f[3] >= height * 0.03]
            if 2 <= len(big) <= ACTIVE_MAX_FACES and len(frames) >= 2:
                grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
                active.append([(f[0] + f[2] / 2, f[1] + f[3] / 2, f[3], mouth_motion(grays, f)) for f in big])
            elif len(big) > ACTIVE_MAX_FACES:
                crowded += 1
    finally:
        cap.release()
    if len(active) >= max(1, MIN_HIT_RATIO * SAMPLES) and crowded < len(active):
        face = pick_active(active, height)
        if face is not None:
            return crop_for_face(face, width, height)
    if len(isolated) < max(1, MIN_HIT_RATIO * SAMPLES):
        return None
    return crop_for_face(tuple(np.median(np.asarray(isolated), axis=0)), width, height)


SAME_SHOT_SHIFT = 0.15   # pergeseran pusat < 15% lebar crop & ukuran beda < 15% = shot yang sama


def stable_box(prev: CropBox | None, new: CropBox | None) -> CropBox | None:
    """Pakai crop sebelumnya bila crop baru hampir sama (shot kamera yang sama) — mencegah gambar goyang
    di antara potongan pembicara yang berurutan."""
    if prev is None or new is None:
        return new
    dx = abs((prev.x + prev.w / 2) - (new.x + new.w / 2))
    dy = abs((prev.y + prev.h / 2) - (new.y + new.h / 2))
    size = abs(prev.h - new.h) / max(prev.h, 1)
    if dx < SAME_SHOT_SHIFT * prev.w and dy < SAME_SHOT_SHIFT * prev.h and size < SAME_SHOT_SHIFT:
        return prev
    return new


MIN_SHOT_SEC = 0.3   # potongan shot lebih pendek dari ini digabung ke tetangganya


def _resize_box(box: CropBox, h: int, width: int, height: int) -> CropBox:
    """Kotak berukuran tinggi `h` (9:16) dengan pusat sama, dijaga di dalam frame."""
    cx, cy = box.x + box.w / 2, box.y + box.h / 2
    w = int(h * 9 / 16) // 2 * 2
    x = int(min(max(0, cx - w / 2), width - w)) // 2 * 2
    y = int(min(max(0, cy - h / 2), height - h)) // 2 * 2
    return CropBox(x, y, w, h, face=box.face)


def speaker_crops(video: Path, start: float, end: float, width: int, height: int,
                  cuts: list[float]) -> list[tuple[float, CropBox]] | None:
    """Crop per shot kamera di dalam [start, end] (cuts = waktu ganti shot di video sumber).
    Kembalikan [(detik relatif awal shot, kotak)], semua kotak berukuran sama (crop ffmpeg butuh ukuran tetap);
    None bila pembicara tidak tampak di shot mana pun."""
    bounds = [start] + [c for c in sorted(cuts) if start + MIN_SHOT_SEC < c < end - MIN_SHOT_SEC] + [end]
    pieces = [(a, b) for a, b in zip(bounds, bounds[1:])]
    boxes = [speaker_crop(video, a, b, width, height) for a, b in pieces]
    if not any(boxes):
        return None
    for i, b in enumerate(boxes):  # shot tanpa wajah → ikut shot terdekat yang ada wajahnya
        if b is None:
            boxes[i] = next((boxes[j] for j in sorted(range(len(boxes)), key=lambda j: abs(j - i)) if boxes[j]), None)
    h = max(b.h for b in boxes)
    boxes = [b if b.h == h else _resize_box(b, h, width, height) for b in boxes]
    out: list[tuple[float, CropBox]] = []
    for (a, _), b in zip(pieces, boxes):
        if out and out[-1][1] == b:
            continue
        out.append((round(a - start, 3), b))
    return out
