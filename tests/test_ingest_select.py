"""Pilih sebagian klip footage untuk diproses."""

import pytest

from autoreels.ingest import list_inputs


def _make(tmp_path):
    for n in ("a.mp4", "b.mp4", "c.mov", "catatan.txt"):
        (tmp_path / n).write_bytes(b"x")
    return tmp_path


def test_all_clips_by_default(tmp_path):
    assert [f.name for f in list_inputs(_make(tmp_path))] == ["a.mp4", "b.mp4", "c.mov"]


def test_only_selected_clips(tmp_path):
    assert [f.name for f in list_inputs(_make(tmp_path), only=["c.mov", "a.mp4"])] == ["a.mp4", "c.mov"]


def test_missing_selected_clip_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="tidak ada"):
        list_inputs(_make(tmp_path), only=["x.mp4"])
