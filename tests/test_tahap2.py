"""Tahap 2: transisi xfade, before–after, tahap proyek, blur privasi."""

from __future__ import annotations

import pytest

from autoreels.describe import SceneDescription
from autoreels.edl import Transition
from autoreels.render.cut import compare_split
from autoreels.render.transitions import join_graph, xfade_frames
from autoreels.validate import validate_edl
from tests.test_validate import BRAND, STYLE, _analysis, _edl


# ---------- transisi ----------
def test_xfade_offsets_keep_cut_points():
    frames = [60, 30, 30, 45]
    trans = [Transition.cut, Transition.fade, Transition.cut, Transition.slide_left]
    graph, last = join_graph(frames, trans)
    # fade masuk ke segmen 1 tepat di detik 2,0 (60 frame); slide masuk ke segmen 3 di detik 4,0 (120 frame)
    assert "xfade=transition=fade" in graph and "offset=2.0000" in graph
    assert "xfade=transition=slideleft" in graph and "offset=4.0000" in graph
    assert "concat=n=2" in graph  # batas cut tetap concat biasa
    assert last == "j3"


def test_xfade_never_eats_too_much_of_short_segment():
    assert xfade_frames(Transition.cut, 30) == 0
    assert xfade_frames(Transition.zoom_punch, 30) == 0
    assert xfade_frames(Transition.fade, 10) <= 4  # ≤ 45% dari segmen 10 frame


def test_compare_split_fits_inside_slot():
    for slot in (30, 60, 90):
        before, wipe = compare_split(slot)
        assert 0 < before < slot and before + wipe <= slot


# ---------- tahap proyek ----------
@pytest.mark.parametrize("raw,expected", [("awal", "awal"), ("Kondisi sebelum", "awal"), ("PROSES", "proses"),
                                          ("hasil akhir", "hasil"), ("selesai", "hasil"), (None, None), ("motor", None)])
def test_stage_normalized(raw, expected):
    assert SceneDescription(scene_id="K1-1", stage=raw).stage == expected


# ---------- before–after di validator ----------
def _desc(stages: dict[str, str]) -> dict:
    return {sid: SceneDescription(scene_id=sid, stage=st, hook_potential=4) for sid, st in stages.items()}


def test_before_after_hook_gets_compare_automatically():
    edl = _edl(hook={"type": "before_after", "overlay_text": "Lihat bedanya", "source_segment_index": 0})
    r = validate_edl(edl, _analysis(), STYLE, _analysis().music, BRAND, [], _desc({"K1-3": "awal", "K1-1": "hasil"}))
    cmp = r.edl.segments[0].compare
    assert cmp is not None and cmp.scene_id == "K1-3" and cmp.source_file == "a.mp4"
    assert cmp.end - cmp.start >= 1.0


def test_compare_on_unusable_scene_is_dropped():
    edl = _edl()
    edl.segments[0].compare = edl.segments[0].compare or None
    data = edl.model_dump(mode="json")
    data["segments"][0]["compare"] = {"source_file": "a.mp4", "scene_id": "K1-4", "start": 15.0, "end": 17.0}
    r = validate_edl(type(edl).model_validate(data), _analysis(), STYLE, _analysis().music, BRAND, [])
    assert r.edl.segments[0].compare is None  # K1-4 tidak layak (blur)
    assert any("before–after dibatalkan" in f for f in r.fixes)


def test_compare_with_clip_code_is_resolved():
    data = _edl().model_dump(mode="json")
    data["segments"][0]["compare"] = {"source_file": "K1", "scene_id": "K1-6", "start": 25.5, "end": 27.0}
    r = validate_edl(type(_edl()).model_validate(data), _analysis(), STYLE, _analysis().music, BRAND, [])
    assert r.edl.segments[0].compare.source_file == "a.mp4"


# ---------- blur privasi ----------
def _has_ffmpeg() -> bool:
    try:
        from autoreels.media import ffmpeg_bin

        return bool(ffmpeg_bin())
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _has_ffmpeg(), reason="ffmpeg tidak tersedia")
def test_blur_video_keeps_frame_count(tmp_path):
    from autoreels.media import probe, run_ffmpeg
    from autoreels.render.privacy import blur_video

    src = tmp_path / "in.mp4"
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=1", "-c:v", "libx264",
                "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(src)])
    stats = blur_video(src, tmp_path / "out.mp4", faces=True, plates=True, preview=True, log=lambda *_: None)
    assert stats.frames == 30
    info = probe(tmp_path / "out.mp4")
    assert (info.width, info.height) == (1080, 1920) and abs(info.duration - 1.0) < 0.1
