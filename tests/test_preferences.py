"""Tes belajar dari editan manusia (tanpa LLM sungguhan)."""

from __future__ import annotations

import json

from autoreels import preferences as pf
from tests.test_validate import _edl


class FakeLLM:
    def __init__(self) -> None:
        self.messages = None

    def complete(self, messages, **_):
        self.messages = messages
        return "```\n- Teks hook maks 5 kata dan sebut harga.\n- [rental] CTA pendek.\n```"


def test_diff_edl_lists_human_changes():
    ai = _edl()
    human = ai.model_copy(deep=True)
    human.hook.overlay_text = "Sewa motor mulai 75 ribu"
    human.cta.text = "Chat WA sekarang"
    human.segments[2].overlay_text = "Helm gratis"
    human.segments = [s for s in human.segments if s.index != 3]
    human.hashtags = ["#garut", "#sewamotorgarut"]
    changes = pf.diff_edl(ai, human)
    text = "\n".join(changes)
    assert "teks hook diubah: “Keliling Garut pakai motor” → “Sewa motor mulai 75 ribu”" in text
    assert "teks CTA diubah" in text and "Helm gratis" in text
    assert "segmen 3 (isi) dibuang" in text and "#sewamotorgarut" in text
    assert pf.diff_edl(ai, ai.model_copy(deep=True)) == []


def test_snapshot_record_and_summarize(tmp_path, monkeypatch):
    monkeypatch.setitem(pf.PATHS, "output", tmp_path / "output")
    monkeypatch.setitem(pf.PATHS, "config", tmp_path / "config")
    (tmp_path / "config").mkdir()
    out = tmp_path / "output" / "job1"
    out.mkdir(parents=True)
    ai = _edl()
    pf.snapshot_ai(out, ai)
    human = ai.model_copy(deep=True)
    human.hook.overlay_text = "Mulai 75 ribu/hari"
    pf.snapshot_ai(out, human)  # tidak menimpa versi AI
    assert pf.record_edits(out, human)
    data = json.loads((out / "edits.json").read_text(encoding="utf-8"))
    assert data["pillar"] == "rental" and "Mulai 75 ribu/hari" in data["changes"][0]
    assert pf.record_edits(out, ai) == [] and not (out / "edits.json").exists()  # dikembalikan ke versi AI
    pf.record_edits(out, human)

    # catatan manual pemilik bertahan setelah dirangkum
    pf.pref_path().write_text(pf.compose("- lama", "- Jangan pakai emoji", "2026-01-01 00:00:00"), encoding="utf-8")
    assert pf.status()["new_since_summary"] == 1
    llm = FakeLLM()
    text = pf.summarize(llm=llm, log=lambda *_: None)
    assert "Mulai 75 ribu/hari" in llm.messages[1]["content"] and "- lama" in llm.messages[1]["content"]
    assert "- Teks hook maks 5 kata" in text and "- Jangan pakai emoji" in text and "```" not in text
    assert pf.status()["new_since_summary"] == 0
    ctx = pf.for_director()
    assert "Teks hook maks 5 kata" in ctx and "Jangan pakai emoji" in ctx and "Dibuat AI" not in ctx

    # edit manual lewat web tetap menyimpan penanda waktu
    pf.write_text(text.replace("- Jangan pakai emoji", "- Tanpa emoji"))
    assert pf.last_summarized() and "Tanpa emoji" in pf.for_director()


def test_job_without_ai_snapshot_is_ignored(tmp_path):
    assert pf.record_edits(tmp_path, _edl()) == []
