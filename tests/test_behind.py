"""Teks hook di belakang orang: aturan penempatan (mask sintetis, tanpa model)."""

from __future__ import annotations

import numpy as np

from autoreels.render import behind
from autoreels.render.reframe import OUT_H, OUT_W


def _head_mask(top: int) -> list[np.ndarray]:
    m = np.zeros((OUT_H, OUT_W), np.uint8)
    m[top:, 300:780] = 255           # kepala+badan selebar 480 px mulai y=top
    return [m] * 10


def test_plan_keeps_upper_half_of_letters_clear():
    p = behind.plan_behind(_head_mask(700), "Kerja atau hobi?")
    assert p is not None and p.cover >= behind.COVER_MIN
    line_h = int(p.size * 1.12)
    y0 = p.y - len(p.lines) * line_h // 2
    for i in range(len(p.lines)):                       # separuh atas tiap baris di atas kepala
        assert y0 + i * line_h + int(0.5 * line_h) <= 700 + 2


def test_no_plan_without_person_or_when_person_fills_top():
    assert behind.plan_behind([np.zeros((OUT_H, OUT_W), np.uint8)] * 5, "Halo semua") is None
    assert behind.plan_behind(_head_mask(0), "Halo semua") is None    # orang memenuhi layar dari atas
