"""Tes utilitas render: teks .ass, warna, font, reframe."""

from __future__ import annotations

from autoreels.config import PATHS
from autoreels.render.reframe import crop_filter
from autoreels.render.text_ass import ass_color, fit_text, font_full_name, wrap_text


def test_wrap_max_two_lines():
    lines, size = fit_text("Liburan ke Garut nggak perlu bawa motor sendiri lho", 96, 16)
    assert len(lines) <= 2
    assert size <= 96
    assert all(len(line.split()) <= 5 for line in wrap_text("a b c d e f g h", 99))


def test_ass_color():
    assert ass_color("#FFC400") == "&H0000C4FF"
    assert ass_color("#000000CC") == "&H33000000"


def test_font_name_from_file():
    f = PATHS["fonts"] / "Montserrat" / "Montserrat-ExtraBold.ttf"
    if f.exists():
        assert "Montserrat" in font_full_name(f)


def test_crop_landscape_stays_inside():
    flt = crop_filter(1280, 720, 0.99, 0.01, 2.0)
    crop_w = int(flt.split("=")[1].split(":")[0])
    assert crop_w % 2 == 0 and 400 <= crop_w <= 406  # 720 × 9/16 ≈ 405
    # pusat ekstrem dibatasi: x tetap di dalam frame (0 … 1280−crop_w)
    x0 = float(flt.split(":")[2].strip("'").split("+")[0])
    assert 0 <= x0 <= 1280 - crop_w
    assert "scale=1080:1920" in flt
