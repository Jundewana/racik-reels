"""Deteksi adegan dengan PySceneDetect (ContentDetector), lalu pecah adegan panjang.

Adegan panjang (mis. satu shot 50 detik) dipecah menjadi potongan ±5 detik agar
Describe & Director punya pilihan momen yang lebih rinci.
"""

from __future__ import annotations

from pathlib import Path

MAX_SCENE_SEC = 8.0
TARGET_PIECE_SEC = 5.0
MIN_SCENE_SEC = 0.5


def detect_scenes(proxy: Path, duration: float, threshold: float = 27.0) -> list[tuple[float, float]]:
    from scenedetect import ContentDetector, SceneManager, open_video

    video = open_video(str(proxy))
    manager = SceneManager()
    manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=12))
    manager.detect_scenes(video, show_progress=False)
    raw = [(s.get_seconds(), e.get_seconds()) for s, e in manager.get_scene_list()]
    if not raw:
        raw = [(0.0, duration)]
    return split_long(raw)


def split_long(scenes: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for start, end in scenes:
        length = end - start
        if length < MIN_SCENE_SEC:
            continue
        if length <= MAX_SCENE_SEC:
            out.append((round(start, 3), round(end, 3)))
            continue
        pieces = max(2, round(length / TARGET_PIECE_SEC))
        step = length / pieces
        for i in range(pieces):
            out.append((round(start + i * step, 3), round(start + (i + 1) * step, 3)))
    return out
