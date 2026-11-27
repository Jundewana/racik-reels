"""Crop pengikut subjek: jejak dari deteksi objek, ekspresi crop sepotong-sepotong, pendeteksi NanoDet."""

from __future__ import annotations

import numpy as np
import pytest

from autoreels.analyze import objects
from autoreels.analyze.models import ClipInfo, Scene
from autoreels.analyze.quality import FrameSample, crop_track
from autoreels.edl import Segment
from autoreels.media import probe, run_ffmpeg
from autoreels.render.cut import render_segment
from autoreels.render.reframe import crop_filter, path_expr


def _s(t, cx, tracked):
    return FrameSample(t, 50, 120, 0, 0, cx, tracked)


def test_track_interpolates_between_detections_not_saliency():
    # motor masuk dari kanan (0,9) ke tengah; 2 sampel tanpa deteksi (saliency 0,5) termasuk sampel pertama
    samples = [_s(0.0, 0.5, False), _s(0.2, 0.9, True), _s(0.4, 0.85, True), _s(0.6, 0.5, False),
               _s(0.8, 0.75, True), _s(1.0, 0.7, True), _s(1.2, 0.65, True), _s(1.4, 0.6, True)]
    xs = crop_track(samples)
    assert xs[0] > 0.8                                    # tepi adegan = deteksi terdekat, bukan saliency 0,5
    assert xs[3] > 0.7                                    # celah diisi interpolasi
    assert all(a >= b - 0.01 for a, b in zip(xs, xs[1:]))  # jalur mulus mengikuti arah gerak


def test_track_pan_speed_is_limited():
    samples = [_s(i * 0.2, 0.2, True) for i in range(5)] + [_s(1.0 + i * 0.2, 0.8, True) for i in range(5)]
    xs = crop_track(samples)
    assert max(abs(b - a) for a, b in zip(xs, xs[1:])) <= 0.4 * 0.2 + 1e-6   # objek "melompat" → crop menggeser halus


def test_track_without_objects_uses_saliency():
    samples = [_s(i * 0.2, 0.4, False) for i in range(8)]
    assert crop_track(samples) == pytest.approx([0.4] * 8)


def test_path_expr_is_piecewise_linear():
    expr = path_expr([(0.0, 100.0), (1.0, 300.0), (2.0, 300.0)])
    evaluate = lambda t: eval(expr.replace("if(", "_if(").replace("lt(", "_lt("),  # noqa: E731
                              {"_if": lambda c, a, b: a if c else b, "_lt": lambda a, b: a < b, "t": t})
    assert evaluate(0.0) == pytest.approx(100) and evaluate(0.5) == pytest.approx(200)
    assert evaluate(1.5) == pytest.approx(300) and evaluate(5) == pytest.approx(300)
    many = path_expr([(i * 0.1, float(i)) for i in range(100)])
    assert many.count("if(") <= 26                        # dibatasi MAX_KNOTS


def test_crop_follows_path_in_render(tmp_path):
    src = tmp_path / "lebar.mp4"
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)])
    info = probe(src)
    clip = ClipInfo(name=src.name, path=str(src), hash="x", duration=info.duration, width=640, height=360, fps=30,
                    has_audio=False)
    scene = Scene(scene_id="a", source_file=src.name, start=0, end=3,
                  crop_path=[[t / 5, 0.2 + 0.6 * t / 15] for t in range(16)])
    vf = crop_filter(640, 360, 0.5, 0.5, 2.0, scene.crop_path, start=0.5, speed=1.0)
    assert "x='if(lt(t," in vf
    seg = Segment(index=0, source_file=src.name, start=0.5, end=2.5, role="isi")
    out = render_segment(seg, clip, scene, tmp_path / "ikut.mp4", preview=True)
    assert probe(out).width == 1080 and probe(out).duration == pytest.approx(2.0, abs=0.05)


def test_detector_on_empty_frame_and_without_model(monkeypatch, tmp_path):
    assert objects.detect(np.zeros((360, 640, 3), np.uint8)) == []
    assert objects.subject_cx(np.zeros((360, 640, 3), np.uint8)) is None
    monkeypatch.setattr(objects, "MODEL", tmp_path / "tidak_ada.onnx")
    objects._net.cache_clear()
    try:
        assert objects.detect(np.zeros((360, 640, 3), np.uint8)) is None   # tanpa model → kembali ke saliency
    finally:
        objects._net.cache_clear()
