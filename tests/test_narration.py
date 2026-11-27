"""Alur "narasi dulu": pemecahan frasa, segmen ikut frasa, dan endpoint narasi (tanpa LLM/transkripsi)."""

from __future__ import annotations

from autoreels.analyze.transcribe import Word
from autoreels.edl import Narration, NarrationWord
from autoreels.narration import HOOK_MAX, PHRASE_MAX, build_phrases
from autoreels.validate import FPS, validate_edl
from tests.test_validate import BRAND, STYLE, _analysis, _edl


def _words(spec: list[tuple[str, float, float]]) -> list[Word]:
    return [Word(text=t, start=s, end=e) for t, s, e in spec]


def _sentence_words(n_words: int = 40, step: float = 0.4, pause_every: int = 5) -> list[Word]:
    """Kata berjarak rata dengan jeda 0,4 dtk tiap `pause_every` kata (seperti ujaran wajar)."""
    out, t = [], 0.2
    for i in range(n_words):
        out.append(Word(text=f"kata{i}" + ("," if (i + 1) % pause_every == 0 else ""), start=round(t, 3),
                        end=round(t + step * 0.8, 3)))
        t += step + (0.4 if (i + 1) % pause_every == 0 else 0)
    return out


def test_phrases_cover_whole_narration_without_gaps():
    words = _sentence_words()
    total = words[-1].end + 0.3
    ph = build_phrases(words, total)
    assert ph[0].start == 0.0 and abs(ph[-1].end - total) < 1e-6
    for a, b in zip(ph, ph[1:]):
        assert a.end == b.start  # bersambung
    assert ph[0].end <= 3.0 and ph[0].duration <= HOOK_MAX + 0.3
    assert all(p.duration <= PHRASE_MAX + 0.6 for p in ph)
    assert " ".join(p.text for p in ph).split() == [w.text for w in words]  # tidak ada kata hilang


def test_phrase_boundaries_fall_between_words():
    words = _sentence_words()
    ph = build_phrases(words, words[-1].end + 0.3)
    for p in ph[1:]:
        assert not any(w.start < p.start < w.end for w in words), f"batas {p.start} memotong kata"


def test_short_cta_merged_into_previous_phrase():
    words = _words([("Sewa", 0.0, 0.4), ("motor", 0.45, 0.9), ("di", 0.95, 1.1), ("Garut.", 1.15, 1.8),
                    ("Unitnya", 2.3, 2.8), ("bersih", 2.85, 3.3), ("dan", 3.35, 3.5), ("terawat.", 3.55, 4.2),
                    ("Booking", 4.7, 5.0), ("yuk.", 5.05, 5.3)])
    ph = build_phrases(words, 5.5)
    assert ph[-1].duration >= 1.5
    assert ph[-1].text.endswith("yuk.")


def test_empty_words_gives_single_phrase():
    ph = build_phrases([], 4.0)
    assert len(ph) == 1 and ph[0].end == 4.0


def _narration_edl(n_phrases: int = 5, phrase_dur: float = 2.0, n_segments: int | None = None):
    words = [NarrationWord(text=f"k{i}", start=i * phrase_dur + 0.1, end=(i + 1) * phrase_dur - 0.2)
             for i in range(n_phrases)]
    total = n_phrases * phrase_dur
    phrases = build_phrases(words, total)
    narr = Narration(file="narasi.wav", source="tes.mp3", duration=total, words=words, phrases=phrases)
    edl = _edl(target_duration_sec=total)
    keep = n_segments if n_segments is not None else len(phrases)
    segs = edl.segments[: keep - 1] + edl.segments[-1:]
    for i, s in enumerate(segs):
        s.index = i
    edl.segments = segs
    edl.narration = narr
    return edl


def test_segments_follow_phrase_durations_frame_exact():
    edl = _narration_edl()
    r = validate_edl(edl, _analysis(), STYLE, _analysis().music, BRAND)
    assert r.ok, r.errors
    phrases = r.edl.narration.phrases
    assert len(r.edl.segments) == len(phrases)
    total_frames = sum(round(s.output_duration * FPS) for s in r.edl.segments)
    assert total_frames == round(r.edl.narration.duration * FPS)
    for seg, p in zip(r.edl.segments, phrases):
        assert abs(seg.output_duration - p.duration) <= 1.5 / FPS


def test_too_few_segments_is_error_for_director():
    edl = _narration_edl(n_segments=3)
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert any("jumlah frasa" in e for e in r.errors)


def test_extra_segments_trimmed_keeping_cta():
    edl = _narration_edl(n_segments=8)
    last_scene = edl.segments[-1].scene_id
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert len(r.edl.segments) == len(r.edl.narration.phrases)
    assert r.edl.segments[-1].scene_id == last_scene
    assert any("berlebih" in f for f in r.fixes)


def test_narration_endpoints(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from autoreels import server

    narr_dir = tmp_path / "_narasi"
    monkeypatch.setattr(server, "NARRATION_DIR", narr_dir)
    monkeypatch.setattr(server, "NARRATION_SOURCES", [narr_dir])
    monkeypatch.setattr(server, "FOOTAGE", tmp_path)
    monkeypatch.setattr(server, "_rel", lambda p: p.relative_to(tmp_path).as_posix())
    client = TestClient(server.app)

    bad = client.post("/api/narration/upload", files={"file": ("x.txt", b"halo", "text/plain")})
    assert bad.status_code == 400

    ok = client.post("/api/narration/upload", files={"file": ("suara saya.mp3", b"\x00" * 64, "audio/mpeg")})
    assert ok.status_code == 200, ok.text
    first = ok.json()["path"]
    again = client.post("/api/narration/upload", files={"file": ("suara saya.mp3", b"\x00" * 64, "audio/mpeg")})
    assert again.json()["path"] != first  # tidak menimpa

    files = client.get("/api/narration").json()["files"]
    assert len(files) == 2 and all(f["url"].startswith("/media/footage/") for f in files)


def test_job_rejects_narration_outside_footage(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from autoreels import server

    footage = tmp_path / "footage"
    (footage / "rental").mkdir(parents=True)
    (footage / "rental" / "a.mp4").write_bytes(b"\x00")
    monkeypatch.setattr(server, "FOOTAGE", footage)
    monkeypatch.setattr(server, "ROOT", tmp_path)
    outside = tmp_path / "rahasia.mp3"
    outside.write_bytes(b"\x00")
    client = TestClient(server.app)
    res = client.post("/api/jobs", json={"input_path": "footage/rental", "pillar": "rental", "style": "rental_energik",
                                         "brief": "tes narasi", "narration_path": "rahasia.mp3"})
    assert res.status_code == 400, res.text
    assert "narasi" in res.text.lower()
