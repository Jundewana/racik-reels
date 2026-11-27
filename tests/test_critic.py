"""Tahap 4: Critic + loop revisi Director, butir checklist Critic, dan evaluasi (LLM tiruan, tanpa biaya API)."""

from __future__ import annotations

import json

import pytest

from autoreels import evaluate
from autoreels.checklist import Checklist, add_critic_checks
from autoreels.critic import CriticOutput, CriticReview, build_critic_messages, markdown
from autoreels.director import DirectorResult, direct
from autoreels.edl import EDL
from tests.test_validate import STYLE, _analysis, _edl


def _review(hook=4, rest=4, notes=None) -> CriticOutput:
    return CriticOutput(
        scores={"hook": hook, "instruction_fit": rest, "flow": rest, "pace": rest, "text_readability": rest,
                "cta": rest, "brand": rest},
        hook_comment="hook cukup", revision_notes=notes or [], summary="ringkas")


class FakeLLM:
    """Mengembalikan EDL / penilaian Critic berurutan dan mencatat semua panggilan."""

    def __init__(self, edls: list[EDL], reviews: list, fail_critic: bool = False) -> None:
        self.edls, self.reviews, self.fail_critic = list(edls), list(reviews), fail_critic
        self.calls: list[tuple[str, list[dict]]] = []

    def complete_structured(self, messages, schema, *, model=None, purpose="llm", **_):
        self.calls.append((purpose, messages))
        if schema is EDL:
            return self.edls.pop(0).model_copy(deep=True)
        if self.fail_critic:
            raise RuntimeError("API sedang sibuk")
        return self.reviews.pop(0)


def _run(llm: FakeLLM, rounds: int = 2) -> DirectorResult:
    a = _analysis()
    return direct(llm=llm, model="tes/model", analysis=a, descriptions={}, music=a.music,
                  brief="Promo sewa motor", pillar="rental", style_name="rental_energik", style=STYLE,
                  duration=18, log=lambda *_: None, critic_rounds=rounds)


def _purposes(llm: FakeLLM) -> list[str]:
    return [p for p, _ in llm.calls]


def test_critic_passes_first_round_no_revision():
    llm = FakeLLM([_edl()], [_review(5, 4)])
    res = _run(llm)
    assert res.validation.ok, res.validation.errors
    assert _purposes(llm) == ["director#1", "critic#1"]
    assert res.chosen_round == 0 and res.critic_revisions == 0
    assert res.review.passed and res.critic_dict()["final"]["hook"] == 5


def test_low_score_triggers_revision_with_notes():
    better = _edl(hook={"type": "pertanyaan", "overlay_text": "Ke Garut tanpa motor?", "source_segment_index": 0})
    llm = FakeLLM([_edl(), better], [_review(2, 3, ["Segmen #0: teks hook terlalu umum, pakai pola pertanyaan."]),
                                     _review(5, 4)])
    res = _run(llm)
    assert _purposes(llm) == ["director#1", "critic#1", "director_critic1#1", "critic#2"]
    revision_prompt = llm.calls[2][1][-1]["content"]
    assert "terlalu umum" in revision_prompt and "rata-rata" in revision_prompt
    assert res.chosen_round == 1 and res.critic_revisions == 1
    assert res.validation.edl.hook.overlay_text == "Ke Garut tanpa motor?"


def test_max_two_revisions_then_best_version_kept():
    llm = FakeLLM([_edl(), _edl(), _edl()], [_review(3, 4, ["a"]), _review(2, 3, ["b"]), _review(3, 3, ["c"])])
    res = _run(llm)
    assert res.critic_revisions == 2
    assert len(res.reviews) == 3
    assert _purposes(llm).count("critic#3") == 1 and len([p for p in _purposes(llm) if p.startswith("critic")]) == 3
    assert res.chosen_round == 0  # skor hook 3 & rata-rata tertinggi ada di putaran 1


def test_invalid_revision_keeps_previous_version():
    bad = _edl()
    bad.segments[1].scene_id = "K1-4"  # adegan unusable → validasi gagal
    bad.segments[1].start, bad.segments[1].end = 16.0, 17.0
    llm = FakeLLM([_edl(), bad, bad], [_review(3, 3, ["ganti hook"])])
    res = _run(llm)
    assert res.validation.ok
    assert res.chosen_round == 0 and res.critic_revisions == 1


def test_critic_failure_does_not_fail_job():
    llm = FakeLLM([_edl()], [], fail_critic=True)
    res = _run(llm)
    assert res.validation.ok and res.reviews == [] and res.critic_dict() is None


def test_critic_disabled():
    llm = FakeLLM([_edl()], [])
    res = _run(llm, rounds=-1)
    assert _purposes(llm) == ["director#1"] and res.critic_dict() is None


def test_critic_judge_only_never_revises():
    llm = FakeLLM([_edl()], [_review(2, 3, ["ganti hook"])])
    res = _run(llm, rounds=0)
    assert _purposes(llm) == ["director#1", "critic#1"]
    assert res.critic_revisions == 0 and res.review.hook == 2  # baseline evaluasi: dinilai, tidak direvisi


def test_critic_prompt_contains_segments_and_facts():
    edl = _edl()
    msgs = build_critic_messages(edl=edl, descriptions={}, stats={"hook_duration": 2.0, "total_duration": 18.1},
                                 brief="Promo", pillar="rental", style_name="rental_energik", style=STYLE,
                                 brand={"company_name": "PT Brand"})
    user = msgs[1]["content"]
    assert "#0 hook" in user and "fakta_otomatis" in user and "hook_duration: 2.0" in user
    assert "Rubrik" in msgs[0]["content"]


def test_review_roundtrip_and_markdown():
    r = CriticReview(round=1, output=_review(3, 5, ["x"]), model="m")
    d = r.to_dict()
    back = CriticReview.from_dict(d)
    assert back.average == r.average and back.hook == 3 and not back.passed
    md = markdown([CriticReview(round=0, output=_review(2, 3)), back], chosen=1)
    assert "Putaran 2 ✔" in md and "Kekuatan hook" in md


@pytest.mark.parametrize("hook,required_fail", [(3, True), (4, False)])
def test_checklist_critic_hook_is_required(hook, required_fail):
    c = Checklist()
    review = CriticReview(round=0, output=_review(hook, 4))
    add_critic_checks(c, {"final": review.to_dict()})
    assert (c.status == "perlu_tinjau") is required_fail


def test_checklist_without_critic_is_only_a_note():
    c = Checklist()
    add_critic_checks(c, None)
    assert c.status == "siap_unggah" and not c.items[0].passed and not c.items[0].required


def _fake_job(root, job_id, *, engine="api", critic=True, status="siap_unggah", hook=4, avg=4.3):
    d = root / job_id
    d.mkdir(parents=True)
    (d / "reel.mp4").write_bytes(b"")
    (d / "job.json").write_text(json.dumps({"job_id": job_id, "created": "2026-11-20 10:00:00", "pillar": "rental",
                                            "style": "rental_energik", "engine": engine, "critic": critic,
                                            "duration": 20}), encoding="utf-8")
    final = {"average": avg, "hook": hook, "scores": {"hook": hook, "flow": 4, "cta": 5}} if critic else None
    (d / "result.json").write_text(json.dumps({
        "status": status,
        "stats": {"total_duration": 20.5, "hook_duration": 2.1, "beat_accuracy": 0.95, "cost_usd": 0.012,
                  "process_sec": 120, "revisions": 1, "target_duration": 20},
        "checklist": [{"group": "Hook benar", "name": "Skor hook dari Critic ≥ 4", "passed": hook >= 4,
                       "required": True, "detail": ""}],
        "critic": {"final": final, "critic_revisions": 1, "rounds": []} if critic else None,
    }), encoding="utf-8")


def test_evaluate_collect_and_report(tmp_path, monkeypatch):
    from autoreels.config import PATHS

    out, work = tmp_path / "output", tmp_path / "work"
    monkeypatch.setitem(PATHS, "output", out)
    monkeypatch.setitem(PATHS, "work", work)
    _fake_job(out, "20261120-100000-rental")
    _fake_job(out, "20261120-110000-rental", engine="local", hook=3, avg=3.4, status="perlu_tinjau")
    _fake_job(out, "20261119-090000-rental", critic=False)
    (work / "20261120-120000-rental").mkdir(parents=True)
    (work / "20261120-120000-rental" / "progress.json").write_text(json.dumps({"state": "gagal"}))
    (work / "20261120-120000-rental" / "error.txt").write_text("RuntimeError: kuota API habis\n")

    jobs, failed = evaluate.collect(since="2026-11-20")
    assert [j.job_id for j in jobs] == ["20261120-100000-rental", "20261120-110000-rental"]
    assert failed[0].reason.startswith("RuntimeError")
    assert jobs[0].duration_ok and jobs[0].hook_ok and jobs[1].failed_checks

    report, csv_path = evaluate.write_outputs(jobs, failed, "tes", out_dir=tmp_path / "eval")
    text = report.read_text(encoding="utf-8")
    assert "mesin api, Critic + revisi" in text and "mesin local, Critic + revisi" in text
    assert "Skor rubrik Critic per aspek" in text and "kuota API habis" in text
    assert "50% (1/2)" in text  # siap unggah
    assert csv_path.read_text(encoding="utf-8").count("\n") == 3


def test_read_manifest_skips_comments(tmp_path):
    m = tmp_path / "manifest.csv"
    m.write_text("set_id,pillar,folder\n# contoh,rental,x\nr1,rental,footage/rental\n,,\n", encoding="utf-8")
    assert [r["set_id"] for r in evaluate.read_manifest(m)] == ["r1"]


def test_critic_context_hides_price_placeholder():
    msgs = build_critic_messages(edl=_edl(), descriptions={}, stats={}, brief="Promo", pillar="rental",
                                 style_name="rental_energik", style=STYLE,
                                 brand={"pricing": {"rental_per_day": "[HARGA]"},
                                        "rental_services": ["Motor bisa diantar ke Stasiun Garut"]})
    user = msgs[1]["content"]
    assert "[HARGA]" not in user and "belum diisi" in user and "Stasiun Garut" in user
    assert "placeholder" in msgs[0]["content"]


def test_critic_sees_before_after_and_narration_limits():
    from autoreels.edl import Compare, Narration, Phrase
    from autoreels.describe import SceneDescription

    edl = _edl()
    edl.segments[0].compare = Compare(source_file="a.mp4", scene_id="K1-3", start=10.0, end=11.0)
    edl.narration = Narration(file="narasi.wav", duration=18.0,
                              phrases=[Phrase(start=0, end=2, text="Mau bangun rumah?")])
    desc = {"K1-3": SceneDescription(scene_id="K1-3", subject="lahan kosong", hook_potential=2, stage="awal")}
    msgs = build_critic_messages(edl=edl, descriptions=desc, stats={"pace_ratio": 0.3, "beat_accuracy": 0.5},
                                 brief="Promo", pillar="konstruksi", style_name="proyek_profesional",
                                 style={"cut_pace_sec": [1.2, 2.5], "transitions": ["cut"]}, brand={})
    user = msgs[1]["content"]
    assert "before–after: sebelum = adegan K1-3: lahan kosong" in user
    assert "cut_pace_sec" not in user and "pace_ratio" not in user and "TETAP" in user


def test_report_pairs_judge_only_vs_revision(tmp_path, monkeypatch):
    from autoreels.config import PATHS

    out = tmp_path / "output"
    monkeypatch.setitem(PATHS, "output", out)
    monkeypatch.setitem(PATHS, "work", tmp_path / "work")
    _fake_job(out, "20261124-100000-rental", critic="nilai", hook=3, avg=3.6, status="perlu_tinjau")
    _fake_job(out, "20261124-110000-rental", critic="revisi", hook=5, avg=4.6)
    for jid in ("20261124-100000-rental", "20261124-110000-rental"):
        f = out / jid / "job.json"
        d = json.loads(f.read_text()); d["eval_set"] = "rental-01"; f.write_text(json.dumps(d))
    jobs, failed = evaluate.collect()
    assert {j.critic_mode for j in jobs} == {"nilai", "revisi"}
    text = evaluate.build_report(jobs, failed)
    assert "Efek revisi Critic per set uji" in text and "| rental-01 | perlu_tinjau | siap_unggah |" in text
    assert "0/1 tanpa revisi → 1/1 dengan revisi" in text and "+1.00" in text
