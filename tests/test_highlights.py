"""Cari cuplikan: perapian usulan AI (batas kalimat, durasi, tumpang tindih) dan endpoint web (tanpa Whisper/LLM)."""

from __future__ import annotations

import json

from autoreels.analyze.transcribe import Word
from autoreels.highlights import MAX_SEC, MIN_SEC, Candidate, _Pick, save_candidates, tidy, transcript_lines
from autoreels.talk import Sentence


def _sentences(n=120, dur=4.0, gap=0.5):
    """n kalimat 4 dtk; tiap kalimat ke-3 berakhir tanpa titik (potongan napas) agar batas kalimat teruji."""
    out, t = [], 0.0
    for i in range(n):
        end_punct = "" if i % 3 == 1 else "."
        first = "jadi" if i % 3 == 2 else f"Topik{i}"
        out.append(Sentence(i, [Word(t, t + dur / 2, first), Word(t + dur / 2, t + dur, f"isi{i}{end_punct}")]))
        t += dur + gap
    return out


def test_tidy_snaps_to_sentence_bounds_and_duration():
    s = _sentences()
    c = tidy([_Pick(start=10, end=12, title="Pendek", score=5)], s, 5)[0]
    assert MIN_SEC * 0.75 <= c.duration <= MAX_SEC + 1
    assert not s[c.first].words[0].text.startswith("jadi")           # tidak mulai dengan kata sambung
    assert c.first == 0 or s[c.first - 1].text.endswith(".")          # mulai di awal kalimat sungguhan
    assert s[c.last].text.endswith(".")                               # berakhir di akhir kalimat


def test_tidy_drops_overlaps_and_ranks_by_score():
    s = _sentences()
    picks = [_Pick(start=20, end=40, title="A", score=4), _Pick(start=22, end=42, title="B", score=5),
             _Pick(start=80, end=100, title="C", score=3)]
    out = tidy(picks, s, 5)
    assert [c.title for c in out] == ["B", "C"] and [c.rank for c in out] == [1, 2]


def test_tidy_caps_long_ranges_and_count():
    s = _sentences()
    out = tidy([_Pick(start=0, end=110, title="Kepanjangan", score=5)], s, 5)
    assert out and out[0].duration <= MAX_SEC + 1
    many = [_Pick(start=k * 15, end=k * 15 + 14, title=str(k), score=5) for k in range(8)]
    assert len(tidy(many, s, 3)) == 3


def test_transcript_lines_mark_weak_openers():
    lines = transcript_lines(_sentences(3))
    assert lines[0].startswith("S0 [0:00]") and lines[2].startswith("~S2")


def test_highlight_endpoints(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from autoreels import highlights, server
    from autoreels.config import PATHS

    footage = tmp_path / "footage"
    (footage / "umum").mkdir(parents=True)
    video = footage / "umum" / "podcast.mp4"
    video.write_bytes(b"\x00")
    monkeypatch.setattr(server, "FOOTAGE", footage)
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setitem(PATHS, "work", tmp_path / "work")
    cands = [Candidate(rank=1, title="Tips konsisten", reason="r", score=5, start=10.0, end=100.0, first=1, last=9,
                       hook="h", preview="p"),
             Candidate(rank=2, title="Kesehatan", reason="r", score=4, start=200.0, end=320.0, first=20, last=30,
                       hook="h", preview="p")]
    monkeypatch.setattr(highlights, "find_highlights", lambda *a, **k: cands)
    cut_calls = []

    def fake_cut(v, c, out_dir, **_):
        out_dir.mkdir(parents=True, exist_ok=True)
        f = out_dir / f"cuplikan-{c.rank}.mp4"
        f.write_bytes(b"\x00")
        cut_calls.append(c.rank)
        return f

    monkeypatch.setattr(highlights, "cut_candidate", fake_cut)

    class SyncThread:  # jalankan tugas latar langsung agar tes deterministik
        def __init__(self, target, **_):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(server.threading, "Thread", SyncThread)
    import contextlib

    from autoreels import joblock

    monkeypatch.setattr(joblock, "job_lock", lambda *a, **k: contextlib.nullcontext())  # jangan tunggu job lain
    jobs = []
    monkeypatch.setattr(server, "create_job", lambda body: jobs.append(body) or {"job_id": f"job-{len(jobs)}"})
    client = TestClient(server.app)

    assert client.post("/api/highlights", json={"video_path": "../rahasia.mp4"}).status_code == 400
    res = client.post("/api/highlights", json={"video_path": "footage/umum/podcast.mp4", "count": 5})
    assert res.status_code == 200, res.text
    task = res.json()["task_id"]
    st = client.get(f"/api/highlights/{task}").json()
    assert st["state"] == "selesai" and [c["rank"] for c in st["candidates"]] == [1, 2]
    assert st["video_url"].startswith("/media/footage/")

    base = {"input_path": "footage/umum", "pillar": "umum", "style": "klip_informatif", "brief": "Podcast"}
    assert client.post(f"/api/highlights/{task}/jobs", json={**base, "ranks": []}).status_code == 400
    made = client.post(f"/api/highlights/{task}/jobs", json={**base, "ranks": [2]})
    assert made.status_code == 200, made.text
    assert made.json()["job_ids"] == ["job-1"] and cut_calls == [2]
    job = jobs[0]
    assert job.talk_clip == "cuplikan-2.mp4" and job.clips == ["cuplikan-2.mp4"] and "Kesehatan" in job.brief
    assert job.input_path.endswith("umum/cuplikan")


def test_candidates_roundtrip(tmp_path):
    from autoreels.highlights import load_candidates

    c = Candidate(rank=1, title="t", reason="r", score=5, start=1.0, end=70.0, first=0, last=3, hook="h", preview="p")
    f = tmp_path / "c.json"
    save_candidates(f, tmp_path / "v.mp4", [c])
    video, back = load_candidates(f)
    assert video.name == "v.mp4" and back[0].duration == 69.0
    assert json.loads(f.read_text(encoding="utf-8"))["candidates"][0]["title"] == "t"


def test_cover_topic_fills_skipped_parts_in_order():
    """Topik panjang (mis. 4 YouTuber, ±8 menit): AI hanya memilih 2 bagian → sisanya ditambah, urut waktu."""
    from autoreels.highlights import _Span, cover_topic

    s = _sentences(n=150)                     # ±675 dtk
    picks = [_Pick(start=30, end=55, title="Windah", score=5), _Pick(start=57, end=80, title="Miawaug", score=5)]
    cands = cover_topic(tidy(picks, s, 8), _Span(start=30, end=135, title="Intro YouTuber"), s)
    topic = [c for c in cands if "(bagian " in c.title]
    assert len(topic) >= 3 and topic == sorted(topic, key=lambda c: c.start)
    assert all(c.duration <= MAX_SEC + 1 for c in topic)
    assert topic[0].first <= 30 and topic[-1].last >= 132           # seluruh topik tercakup
    for a, b in zip(topic, topic[1:]):                               # tanpa celah berarti di antaranya
        assert s[b.first].start - s[a.last].end < 20


def test_keep_ranges_keeps_voiced_gap():
    """Jeda 1 dtk berisi suara (mis. "yee" yang tidak ditulis Whisper) tidak dipotong; jeda hening dipotong."""
    import numpy as np

    from autoreels.analyze.transcribe import AudioEnvelope, Transcript, keep_ranges

    words = [Word(0.0, 0.5, "halo"), Word(1.5, 2.0, "semua"), Word(3.0, 3.5, "oke")]
    rms = np.full(200, 0.001, dtype=np.float32)       # 4 dtk @ 20 ms
    for a, b in [(0.0, 0.5), (1.5, 2.0), (3.0, 3.5), (0.7, 1.3)]:   # kata + "yee" di 0,7–1,3
        rms[int(a / 0.02):int(b / 0.02)] = 0.2
    tr = Transcript(path="x", model="m", language="id", duration=4.0, words=words)
    assert len(keep_ranges(tr)) == 3                                  # tanpa envelope: dua jeda dipotong
    ranges = keep_ranges(tr, envelope=AudioEnvelope(rms))
    assert len(ranges) == 2 and ranges[0][1] > 2.0                    # "yee" ikut, jeda hening 2,0–3,0 dipotong


def test_drop_seen_removes_already_shown_candidates():
    from autoreels.highlights import drop_seen

    s = _sentences()
    picks = [_Pick(start=10, end=30, title="Lama", score=5), _Pick(start=80, end=100, title="Baru", score=4)]
    cands = tidy(picks, s, 5)
    seen = [(cands[0].start + 5, cands[0].end, "Lama")]
    out = drop_seen(cands, seen)
    assert [c.title for c in out] == ["Baru"] and out[0].rank == 1
