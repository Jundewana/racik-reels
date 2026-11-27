"""Warna seragam antar klip (render/color.py): hanya pencilan yang dikoreksi."""

from __future__ import annotations

import numpy as np
import pytest

from autoreels.media import run_ffmpeg
from autoreels.render import color


def _stats(rgb, grey=True):
    """Gambar rata satu warna `rgb`; grey=False → seluruhnya hijau jenuh (dedaunan, tanpa piksel abu-abu)."""
    img = np.full((1, 4, 4, 3), rgb, np.uint8)
    if not grey:
        img[:, :, :] = (40, 140, 30)
    return color.stats_from_rgb(img)


def test_only_outliers_are_corrected():
    stats = {"a": _stats((120, 118, 115)), "b": _stats((125, 122, 118)), "c": _stats((100, 100, 98)),
             "dark": _stats((40, 42, 45)), "blue": _stats((110, 118, 128))}   # tembok abu-abu di bawah cahaya kebiruan
    plan = color.plan_corrections(stats)
    assert plan["a"].filter() == "" and plan["b"].filter() == ""     # dalam rentang wajar → tidak disentuh
    assert plan["dark"].gamma > 1.15                                 # terlalu gelap → diterangkan (gamma)
    r, _, b = plan["blue"].gains
    assert r > 1 > b and max(abs(g - 1) for g in plan["blue"].gains) <= 0.06   # rona biru dinetralkan, maks ±5%


def test_foliage_keeps_its_colour_and_saturation_never_drops():
    stats = {"leaf": _stats((0, 0, 0), grey=False), "x": _stats((120, 118, 115)), "y": _stats((118, 120, 117))}
    plan = color.plan_corrections(stats)
    assert stats["leaf"].grey_share < color.GREY_MIN_SHARE
    assert plan["leaf"].gains == (1.0, 1.0, 1.0)                     # tanpa piksel abu-abu → rona tidak digeser
    assert all(c.saturation >= 1.0 for c in plan.values())
    assert color.plan_corrections(stats, strength=0) == {}


@pytest.mark.parametrize("hexcolor,expect_luma", [("0x303848", (35, 75)), ("0xB0A090", (150, 185))])
def test_measure_reads_real_video(tmp_path, hexcolor, expect_luma):
    p = tmp_path / "c.mp4"
    run_ffmpeg(["-f", "lavfi", "-i", f"color=c={hexcolor}:s=160x90:r=30:d=2", "-c:v", "libx264", "-pix_fmt",
                "yuv420p", str(p)])
    st = color.measure(p, 0.0, 2.0)
    assert st is not None and expect_luma[0] <= st.luma <= expect_luma[1]


def test_dark_clip_gets_brighter_after_filter(tmp_path):
    src = tmp_path / "dark.mp4"
    out = tmp_path / "fixed.mp4"
    run_ffmpeg(["-f", "lavfi", "-i", "color=c=0x303030:s=160x90:r=30:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(src)])
    before = color.measure(src, 0, 1)
    stats = {"dark": before, "m1": _stats((120, 120, 120)), "m2": _stats((125, 125, 125))}
    f = color.plan_corrections(stats)["dark"].filter()
    run_ffmpeg(["-i", str(src), "-vf", f, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)])
    assert color.measure(out, 0, 1).luma > before.luma + 15
