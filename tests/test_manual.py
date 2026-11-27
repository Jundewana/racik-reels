"""Mode Claude sebagai sutradara: konteks, deskripsi manual, validasi EDL tulisan Claude (tanpa video/render)."""

from __future__ import annotations

import json

import pytest

from autoreels import manual
from tests.test_validate import _analysis, _edl

JOB = "20261124-100000-rental"


@pytest.fixture()
def job(tmp_path, monkeypatch):
    from autoreels.config import PATHS

    monkeypatch.setitem(PATHS, "work", tmp_path / "work")
    monkeypatch.setitem(PATHS, "output", tmp_path / "output")
    d = manual.manual_dir(JOB)
    d.mkdir(parents=True)
    (tmp_path / "work" / JOB / "analysis.json").write_text(_analysis().model_dump_json(), encoding="utf-8")
    state = {"job": {"job_id": JOB, "pillar": "rental", "brief": "Promo sewa motor", "style": "rental_energik",
                     "duration": 18, "hook_text": None, "cta_text": "Chat WhatsApp sekarang!"},
             "describe": "claude", "blur_faces": True, "blur_plates": False}
    (d / "prep.json").write_text(json.dumps(state), encoding="utf-8")
    rows = [{"scene_id": f"K1-{i}", "durasi": 5.0, "subject": "motor di jalan" if i < 6 else "", "action": "",
             "setting": "jalan", "mood": "ceria", "hook_potential": 4 if i == 1 else 2, "relevance_rental": 4,
             "suggested_text": None, "stage": None} for i in range(1, 13)]
    (d / "deskripsi.json").write_text(json.dumps(rows), encoding="utf-8")
    return d


def test_load_descriptions_skips_unfilled_rows(job):
    desc = manual.load_descriptions(JOB)
    assert sorted(desc) == ["K1-1", "K1-2", "K1-3", "K1-4", "K1-5"]
    assert desc["K1-1"].hook_potential == 4


def test_build_context_has_prompt_data_and_missing_list(job):
    text = manual.build_context(JOB).read_text(encoding="utf-8")
    assert "## Prompt sistem" in text and "## Data" in text and "Promo sewa motor" in text
    assert "belum punya deskripsi" in text and "K1-6" in text
    assert "Teks CTA WAJIB persis" in text


def test_check_applies_forced_text_and_privacy(job):
    (job / "edl.json").write_text(_edl().model_dump_json(), encoding="utf-8")
    r = manual.check(JOB)
    assert r.ok, r.errors
    assert r.edl.cta.text == "Chat WhatsApp sekarang!" and r.edl.privacy.blur_faces is True


def test_finish_refuses_invalid_edl(job):
    bad = _edl()
    bad.segments[1].scene_id = "K1-4"  # adegan unusable
    bad.segments[1].start, bad.segments[1].end = 16.0, 17.0
    (job / "edl.json").write_text(bad.model_dump_json(), encoding="utf-8")
    with pytest.raises(manual.ManualEdlError) as e:
        manual.finish(JOB, log=lambda *_: None)
    assert any("tidak layak" in err for err in e.value.errors)


def test_critic_file_becomes_checklist_ready_dict(tmp_path):
    f = tmp_path / "critic.json"
    f.write_text(json.dumps({"scores": {"hook": 5, "instruction_fit": 4, "flow": 4, "pace": 4,
                                        "text_readability": 5, "cta": 5, "brand": 4},
                             "hook_comment": "kuat", "revision_notes": [], "summary": "ok"}), encoding="utf-8")
    d = manual._critic_dict(f)
    assert d["final"]["hook"] == 5 and d["final"]["passed"] and d["final"]["model"] == manual.CLAUDE_MODEL_LABEL
    assert manual._critic_dict(None) is None


def test_missing_job_has_clear_message(tmp_path, monkeypatch):
    from autoreels.config import PATHS

    monkeypatch.setitem(PATHS, "work", tmp_path)
    with pytest.raises(FileNotFoundError, match="autoreels prepare"):
        manual.load_state("20261124-000000-rental")
