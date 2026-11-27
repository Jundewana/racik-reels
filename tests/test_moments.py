"""Skor momen di dalam adegan (analyze/moments.py) dan pergeseran b-roll ke momen terbaik di validasi."""

from autoreels.analyze.moments import best_window, sample_scores, top_moments, window_score
from autoreels.analyze.quality import FrameSample


def _s(t, tracked, x=0.5, area=0.08, sharp=100.0):
    return FrameSample(t, sharp, 120, 0, 0, x, tracked, x, area)


def test_subject_in_frame_scores_higher_than_empty_or_edge():
    samples = [_s(i * 0.2, False) for i in range(5)] + [_s(1 + i * 0.2, True, x=0.95) for i in range(5)] + \
              [_s(2 + i * 0.2, True, x=0.5) for i in range(5)]
    sc = sample_scores(samples)
    assert sc[12] > sc[7] > sc[2]                      # utuh di tengah > di tepi > tanpa subjek
    curve = [[s.t, v] for s, v in zip(samples, sc)]
    start, score = best_window(curve, 0, 2.8, 0.8)
    assert start >= 1.8 and score == window_score(curve, start, start + 0.8)
    assert top_moments(curve, 0, 2.8, length=0.8)[:2] in ("1.", "2.")
    assert best_window(curve, 0, 2.8, 0.8, avoid=[(1.9, 2.9)])[0] < 1.9   # tidak menimpa segmen lain


def test_validate_moves_broll_to_best_moment():
    from tests.test_validate import BRAND, STYLE, _analysis, _edl
    from autoreels.validate import validate_edl

    an = _analysis()
    sc = next(s for s in an.scenes if s.scene_id == "K1-2")
    sc.moment_curve = [[round(sc.start + k * 0.2, 2), 0.9 if k >= 15 else 0.3] for k in range(int((sc.end - sc.start) / 0.2) + 1)]
    edl = _edl()
    seg = next(s for s in edl.segments if s.scene_id == "K1-2")
    r = validate_edl(edl, an, STYLE, an.music, BRAND, ["#garut"])
    moved = next(s for s in r.edl.segments if s.scene_id == "K1-2")
    assert moved.start >= sc.start + 2.8 and any("momen terbaik" in f for f in r.fixes)
