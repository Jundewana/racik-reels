"""Periksa transkrip narasi: koreksi AI, edit manusia (waktu tetap), draf, dan endpoint web (tanpa Whisper/LLM asli)."""

from __future__ import annotations

import pytest

from autoreels import narration as nar
from autoreels.edl import Narration, NarrationWord, Phrase


def _narration() -> Narration:
    words = [NarrationWord(text=t, start=s, end=e) for t, s, e in [
        ("Liburan", 0.0, 0.5), ("ke", 0.55, 0.7), ("Garut,", 0.75, 1.2),
        ("helm", 1.6, 1.9), ("dan", 1.95, 2.1), ("jasujan", 2.15, 2.7), ("gratis.", 2.75, 3.3)]]
    phrases = [Phrase(start=0.0, end=1.4, text="Liburan ke Garut,"), Phrase(start=1.4, end=3.5, text="helm dan jasujan gratis.")]
    return Narration(file="narasi.wav", source="x.m4a", duration=3.5, words=words, phrases=phrases)


def test_apply_texts_same_word_count_keeps_timings():
    n = nar.apply_texts(_narration(), ["Liburan ke Garut,", "helm dan hujan gratis."])
    assert [w.text for w in n.words][3:] == ["helm", "dan", "hujan", "gratis."]
    assert [(w.start, w.end) for w in n.words] == [(w.start, w.end) for w in _narration().words]


def test_apply_texts_more_words_redistributed_inside_phrase():
    n = nar.apply_texts(_narration(), ["Liburan ke Garut,", "helm dan jas hujan gratis."])
    second = [w for w in n.words if w.start >= 1.4]
    assert [w.text for w in second] == ["helm", "dan", "jas", "hujan", "gratis."]
    assert second[0].start == pytest.approx(1.6) and second[-1].end <= 3.3 + 1e-6
    assert all(a.end <= b.start for a, b in zip(second, second[1:]))
    assert n.phrases[1].text == "helm dan jas hujan gratis." and n.phrases[1].start == 1.4


def test_apply_texts_empty_keeps_original_and_count_checked():
    n = nar.apply_texts(_narration(), ["", "helm dan jasujan gratis."])
    assert n.phrases[0].text == "Liburan ke Garut,"
    with pytest.raises(ValueError):
        nar.apply_texts(_narration(), ["satu"])


class FakeLLM:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.messages = result, error, None

    def complete_structured(self, messages, schema, **_):
        self.messages = messages
        if self.error:
            raise self.error
        return schema(phrases=self.result)


def test_proofread_accepts_small_fixes_and_rejects_rewrites():
    llm = FakeLLM(["Pokoknya liburan paling seru se-Indonesia!", "helm dan jas hujan gratis."])
    n, fixes = nar.proofread(_narration(), llm, "m", log=lambda *_: None)
    assert [f["index"] for f in fixes] == [1]
    assert n.phrases[0].text == "Liburan ke Garut," and n.phrases[1].text == "helm dan jas hujan gratis."
    assert "Papandayan" in llm.messages[1]["content"]  # kosakata brand ikut dikirim


@pytest.mark.parametrize("llm", [FakeLLM(["hanya satu"]), FakeLLM(error=RuntimeError("limit"))])
def test_proofread_falls_back_to_original(llm):
    n, fixes = nar.proofread(_narration(), llm, "m", log=lambda *_: None)
    assert fixes == [] and [p.text for p in n.phrases] == [p.text for p in _narration().phrases]


@pytest.fixture()
def drafts(tmp_path, monkeypatch):
    from autoreels.config import PATHS

    monkeypatch.setitem(PATHS, "work", tmp_path / "work")

    def fake_prepare(source, out_dir, log=print):
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "narasi.wav").write_bytes(b"RIFF....WAVE")
        return _narration().model_copy(update={"source": str(source)})

    monkeypatch.setattr(nar, "prepare_narration", fake_prepare)
    src = tmp_path / "Suara Saya (1).m4a"
    src.write_bytes(b"x")
    return src


def test_draft_lifecycle(drafts, tmp_path):
    d = nar.create_draft(drafts, llm=FakeLLM(["Liburan ke Garut,", "helm dan jas hujan gratis."]), model="m",
                         log=lambda *_: None)
    assert d["id"].endswith("suara-saya-1") and not d["reviewed"] and d["ai_fixes"][0]["index"] == 1
    upd = nar.update_draft(d["id"], ["Liburan ke Garut!", "helm dan jas hujan gratis."])
    assert upd["reviewed"] and upd["narration"]["phrases"][0]["text"] == "Liburan ke Garut!"
    narration, src = nar.use_draft(d["id"], tmp_path / "job")
    assert (tmp_path / "job" / "narasi.wav").exists() and src == str(drafts)
    assert narration.phrases[0].text == "Liburan ke Garut!"
    with pytest.raises(ValueError):
        nar.load_draft("../rahasia")


def test_draft_endpoints(drafts, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from autoreels import server

    monkeypatch.setattr(server, "FOOTAGE", tmp_path)
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "_rel", lambda p: p.name)
    monkeypatch.setattr(nar, "proofread", lambda n, *a, **k: (n, []))
    client = TestClient(server.app)

    res = client.post("/api/narration/transcribe", json={"narration_path": drafts.name})
    assert res.status_code == 200, res.text
    draft = res.json()
    assert len(draft["phrases"]) == 2 and draft["phrases"][1]["original"] == "helm dan jasujan gratis."
    assert client.get(draft["audio_url"]).status_code == 200

    bad = client.put(f"/api/narration/drafts/{draft['id']}", json={"texts": ["satu"]})
    assert bad.status_code == 400
    ok = client.put(f"/api/narration/drafts/{draft['id']}", json={"texts": ["Liburan ke Garut,", "helm dan jas hujan"]})
    assert ok.json()["reviewed"] and ok.json()["phrases"][1]["text"] == "helm dan jas hujan"
    assert client.get("/api/narration/drafts/tidak-ada-123").status_code == 404
    assert client.post("/api/narration/transcribe", json={"narration_path": "../luar.m4a"}).status_code == 400


@pytest.mark.parametrize("before,after,want", [
    ("di rental garut nomor satu,", "di Rental Motor Garut nomor satu,", "di Rental Garut nomor satu,"),
    ("stasiun atau pengenapan.", "Stasiun Garut atau penginapan.", "Stasiun atau penginapan."),
    ("halam dan jasujan gratis", "helm dan jas hujan gratis", "helm dan jas hujan gratis"),
    ("mugepapandayan, Darajat,", "Papandayan, Darajat,", "Papandayan, Darajat,"),
    ("ada metic dan manual", "ada matic manual", "ada matic dan manual"),
    ("pusing transportasi", "repot banget soal kendaraan umum", "pusing transportasi"),
    ("sebuah persenyawaan.", "sebuah senyawa.", "sebuah persenyawaan."),
    ("Rab jelas dari awal", "RAB jelas dari awal", "RAB jelas dari awal"),
])
def test_guard_spoken_keeps_only_mishearing_fixes(before, after, want):
    assert nar.guard_spoken(before, after) == want


def test_talk_draft_endpoint_and_subtitle_rerender(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from autoreels import narration as nar_mod
    from autoreels import server
    from autoreels.config import PATHS

    footage = tmp_path / "footage"
    (footage / "umum").mkdir(parents=True)
    (footage / "umum" / "bicara.mp4").write_bytes(b"\x00")
    monkeypatch.setattr(server, "FOOTAGE", footage)
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setitem(PATHS, "work", tmp_path / "work")
    monkeypatch.setitem(PATHS, "output", tmp_path / "output")
    monkeypatch.setattr(server, "_probe_cached", lambda p: type("I", (), {"duration": 120.0})())
    seen = {}

    def fake_talk(source, out_dir, *, speaker_clip, full, **_):
        seen.update(speaker=speaker_clip, full=full)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "narasi.wav").write_bytes(b"RIFF")
        return _narration().model_copy(update={"speaker_clip": speaker_clip})

    import autoreels.talk as talk_mod

    monkeypatch.setattr(talk_mod, "prepare_talk", fake_talk)
    monkeypatch.setattr(nar_mod, "proofread", lambda n, *a, **k: (n, []))
    client = TestClient(server.app)
    res = client.post("/api/talk/transcribe", json={"input_path": "footage/umum", "talk_clip": "bicara.mp4",
                                                    "talk_full": True})
    assert res.status_code == 200, res.text
    d = res.json()
    assert d["kind"] == "bicara" and d["speaker_clip"] == "bicara.mp4" and d["talk_full"] is True
    assert seen == {"speaker": "bicara.mp4", "full": True}
    assert client.post("/api/talk/transcribe", json={"input_path": "footage/umum", "talk_clip": "x.mp4"}).status_code == 400

    # halaman Hasil: subtitle dibetulkan lalu render ulang (waktu suara tetap)
    from autoreels.edl import EDL
    from tests.test_validate import _edl

    job_id = "20261125-100000-umum"
    out = tmp_path / "output" / job_id
    out.mkdir(parents=True)
    edl = _edl()
    edl.narration = _narration()
    edl.save(out / "edl.json")
    (out / "reel.mp4").write_bytes(b"\x00")
    detail_texts = server._edl_texts(out, {})
    assert [p["text"] for p in detail_texts["subtitles"]] == ["Liburan ke Garut,", "helm dan jasujan gratis."]
    rendered = []
    import autoreels.pipeline as pipe

    monkeypatch.setattr(pipe, "render_from_edl", lambda f, log=print: rendered.append(f))
    monkeypatch.setattr(server.RUNNER, "submit", lambda job_id, fn, label="", kind="create": fn(lambda *_: None))
    bad = client.post(f"/api/jobs/{job_id}/rerender", json={"subtitle_texts": ["satu"]})
    assert bad.status_code == 400
    ok = client.post(f"/api/jobs/{job_id}/rerender",
                     json={"subtitle_texts": ["Liburan ke Garut,", "helm dan jas hujan gratis."]})
    assert ok.status_code == 200, ok.text and rendered
    saved = EDL.load(out / "edl.json")
    assert saved.narration.phrases[1].text == "helm dan jas hujan gratis."
    assert [w.text for w in saved.narration.words][3:6] == ["helm", "dan", "jas"]
    assert saved.narration.phrases[1].start == 1.4  # waktu frasa tidak bergeser
