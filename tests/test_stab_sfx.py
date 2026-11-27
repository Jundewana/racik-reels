"""Stabilisasi footage goyang (vidstab) dan efek suara transisi (render/sfx.py)."""

from __future__ import annotations

import wave

import numpy as np

from autoreels.analyze.models import ClipInfo
from autoreels.edl import Segment, Transition
from autoreels.media import probe, run_ffmpeg
from autoreels.render import sfx
from autoreels.render.cut import render_segment
from tests.test_validate import _edl


def _read(p):
    with wave.open(str(p), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").reshape(-1, 2) / 32767, w.getframerate()


def test_sfx_files_are_generated_and_cues_follow_transitions(tmp_path):
    paths = sfx.ensure_sfx(tmp_path)
    for name, p in paths.items():
        data, sr = _read(p)
        assert sr == sfx.SR and 0.8 * sfx.PEAK < np.abs(data).max() <= sfx.PEAK + 1e-3, name
    edl = _edl()
    edl.segments[1].transition_in = Transition.whip
    edl.segments[2].transition_in = Transition.zoom_punch
    edl.segments[3].transition_in = Transition.fade        # fade = tanpa bunyi
    times = [(i * 1.0, i * 1.0 + 1.0) for i in range(len(edl.segments))]
    cues = sfx.sfx_cues(edl, times)
    assert cues[0] == (0.05, "pop")                         # teks hook muncul
    assert (1.0 - sfx.LEAD["whoosh"], "whoosh") in cues and (2.0 - sfx.LEAD["thump"], "thump") in cues
    assert len(cues) == 3
    out = sfx.render_sfx_track(cues, 5.0, -12, tmp_path, tmp_path / "track.wav")
    track, _ = _read(out)
    assert len(track) == int(sfx.SR * 5.0) + 1
    loud = np.abs(track[int(0.9 * sfx.SR):int(1.1 * sfx.SR)]).max()
    assert 0 < loud <= 10 ** (-12 / 20) * sfx.PEAK + 1e-3   # volume gaya diterapkan
    assert np.abs(track[int(4.0 * sfx.SR):]).max() == 0     # tanpa bunyi di luar titik potong


def _jitter(video):
    """Rata-rata pergeseran gambar antar frame (px) — makin kecil makin stabil."""
    import cv2

    cap, prev, shifts = cv2.VideoCapture(str(video)), None, []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(frame, (108, 192)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None:
            shifts.append(np.hypot(*cv2.phaseCorrelate(prev, g)[0]))
        prev = g
    return float(np.mean(shifts))


def test_shaky_segment_is_stabilised(tmp_path):
    src = tmp_path / "goyang.mp4"
    # gambar diam yang digoyang seperti tangan (beberapa px per frame); testsrc2 bergerak sendiri → tak cocok
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc2=s=480x360:r=30:d=0.04", "-vf",
                "loop=loop=95:size=1,crop=440:330:x='20+9*sin(t*9)+5*sin(t*23)':y='15+7*cos(t*11)+4*sin(t*17)'",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)])
    info = probe(src)
    clip = ClipInfo(name=src.name, path=str(src), hash="x", duration=info.duration, width=info.width,
                    height=info.height, fps=30, has_audio=False)
    seg = Segment(index=0, source_file=src.name, start=0.2, end=2.2, role="isi", reframe="center")
    plain = render_segment(seg, clip, None, tmp_path / "plain.mp4", preview=True)
    stable = render_segment(seg, clip, None, tmp_path / "stable.mp4", preview=True, stabilize=True)
    assert (tmp_path / "stable.trf").exists()
    assert abs(probe(stable).duration - probe(plain).duration) < 0.05          # durasi presisi tetap
    assert _jitter(stable) < _jitter(plain) * 0.7
