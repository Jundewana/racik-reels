"""Tes utilitas importer (tanpa render/LLM)."""

from __future__ import annotations

from autoreels.importer import _normalize_hashtags, find_transcript


def test_find_transcript_from_master_srt(tmp_path):
    edit = tmp_path / "edit"
    edit.mkdir()
    (edit / "final.mp4").write_bytes(b"")
    (edit / "master.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nHalo dari Brand.\n\n2\n00:00:02,000 --> 00:00:04,000\nKami di Garut.\n",
        encoding="utf-8")
    assert find_transcript(edit / "final.mp4") == "Halo dari Brand. Kami di Garut."


def test_find_transcript_from_takes_packed(tmp_path):
    (tmp_path / "takes_packed.md").write_text("## C01\n  [002.52-005.36] S0 Sewa motor gampang.\n", encoding="utf-8")
    text = find_transcript(tmp_path / "final.mp4")
    assert "Sewa motor gampang." in text and "S0" not in text


def test_no_transcript(tmp_path):
    assert find_transcript(tmp_path / "x.mp4") == ""


def test_hashtags_merge_and_clean():
    tags = _normalize_hashtags(["Garut", "#Konstruksi Desa", "#garut"], ["#contohbrand"])
    assert tags[0] == "#contohbrand"
    assert "#garut" in tags and tags.count("#garut") == 1
    assert "#konstruksidesa" in tags
