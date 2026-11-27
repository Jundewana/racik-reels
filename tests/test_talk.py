"""Tahap 3 video bicara: kalimat, take ulang, pemilihan, frasa sinkron bibir, dan validator (tanpa Whisper/LLM)."""

from __future__ import annotations

import pytest

from autoreels import talk
from autoreels.analyze.transcribe import Word
from autoreels.edl import Narration, NarrationWord, Phrase
from autoreels.validate import FPS, validate_edl
from tests.test_validate import BRAND, STYLE, _analysis, _edl


def _w(spec):
    return [Word(start=s, end=e, text=t) for t, s, e in spec]


def test_split_sentences_on_punctuation_and_pause():
    words = _w([("Selamat", 0, 0.4), ("pagi.", 0.45, 0.9), ("Hari", 1.0, 1.2), ("ini", 1.25, 1.4),
                ("kita", 2.3, 2.5), ("belajar", 2.55, 3.0)])
    s = talk.split_sentences(words)
    assert [x.text for x in s] == ["Selamat pagi.", "Hari ini", "kita belajar"]


def test_long_sentence_split_at_biggest_gap():
    words = [Word(start=i * 0.5, end=i * 0.5 + 0.4, text=f"k{i}") for i in range(30)]  # 15 dtk tanpa titik
    words[14] = Word(start=words[13].end + 0.55, end=words[13].end + 0.9, text="k14")  # jeda 0,55 dtk (< pause)
    for i in range(15, 30):
        words[i] = Word(start=words[i - 1].end + 0.1, end=words[i - 1].end + 0.5, text=f"k{i}")
    s = talk.split_sentences(words)
    assert len(s) == 2 and s[1].words[0].text == "k14"
    assert all(x.duration <= talk.SENTENCE_MAX for x in s)


def test_drop_retakes_keeps_last_complete_take():
    words = _w([("Pendidikan", 0, 0.5), ("adalah", 0.55, 0.8), ("kunci", 0.85, 1.1), ("eh.", 1.15, 1.3),
                ("Pendidikan", 2.0, 2.5), ("adalah", 2.55, 2.8), ("kunci", 2.85, 3.1), ("kemajuan.", 3.15, 3.7),
                ("Kita", 4.5, 4.7), ("harus.", 4.75, 5.0),
                ("Kita", 6.0, 6.2), ("harus", 6.25, 6.5), ("bergerak.", 6.55, 7.0)])
    keep, dropped = talk.drop_retakes(talk.split_sentences(words))
    assert [s.text for s in keep] == ["Pendidikan adalah kunci kemajuan.", "Kita harus bergerak."]
    assert len(dropped) == 2


class FakeLLM:
    def __init__(self, ids=None, error=None):
        self.ids, self.error = ids, error

    def complete_structured(self, messages, schema, **_):
        if self.error:
            raise self.error
        return schema(sentences=self.ids, reason="hook paling tegas")


def _sentences(n=12, dur=4.0):
    words = []
    for i in range(n):
        words.append(Word(start=i * (dur + 1), end=i * (dur + 1) + dur, text=f"kalimat{i}."))
    return talk.split_sentences(words)


def test_select_sentences_returns_body_in_original_order():
    chosen = talk.select_sentences(_sentences(), FakeLLM([7, 1, 2, 3, 4, 5, 9, 99, 1]), "m", brief="", target=40,
                                   log=lambda *_: None)
    assert [s.index for s in chosen] == [1, 2, 3, 4, 5, 7, 9]  # urutan asli; id tak dikenal & duplikat dibuang


def test_select_sentences_reserves_room_for_cold_open():
    chosen = talk.select_sentences(_sentences(), FakeLLM(list(range(12))), "m", brief="", target=45, reserve=5,
                                   log=lambda *_: None)
    assert sum(s.duration for s in chosen) <= talk.TARGET_MAX - 5


@pytest.mark.parametrize("llm", [FakeLLM(error=RuntimeError("limit")), FakeLLM([0])])
def test_select_sentences_fallback_when_llm_fails_or_too_short(llm):
    chosen = talk.select_sentences(_sentences(), llm, "m", brief="", target=40, log=lambda *_: None)
    total = sum(s.duration for s in chosen)
    assert talk.TARGET_MIN * 0.8 <= total <= talk.TARGET_MAX and chosen[0].index == 0


def test_phrases_never_cross_cut_and_map_to_source():
    ranges = [(100.0, 103.0), (10.0, 14.0)]  # hook dari menit belakang, lalu kalimat awal
    words_tl = [NarrationWord(start=0.1, end=0.9, text="Pendidikan"), NarrationWord(start=1.0, end=2.8, text="kunci."),
                NarrationWord(start=3.2, end=4.0, text="Kita"), NarrationWord(start=4.1, end=6.8, text="bergerak.")]
    ph = talk._phrases_in_ranges(words_tl, ranges)
    assert ph[0].start == 0 and ph[0].src_start == 100.0
    cut = next(p for p in ph if p.start >= 3.0 - 1e-6)
    assert cut.start == pytest.approx(3.0) and cut.src_start == pytest.approx(10.0)
    assert not any(p.start < 3.0 < p.end for p in ph)


def test_validator_locks_speaker_segments_for_lip_sync():
    phrases = [Phrase(start=0.0, end=2.5, text="Hook", src_start=20.3),
               Phrase(start=2.5, end=6.0, text="isi", src_start=31.0),
               Phrase(start=6.0, end=9.0, text="b-roll", src_start=40.0),
               Phrase(start=9.0, end=12.0, text="tutup", src_start=45.2)]
    narr = Narration(file="narasi.wav", duration=12.0, phrases=phrases, speaker_clip="a.mp4",
                     words=[NarrationWord(start=p.start + 0.1, end=p.end - 0.1, text=p.text) for p in phrases])
    edl = _edl()
    edl.segments = edl.segments[:3] + edl.segments[-1:]
    for i, s in enumerate(edl.segments):
        s.index = i
    edl.segments[0].scene_id, edl.segments[0].start, edl.segments[0].end = "K1-1", 0.0, 2.0
    edl.narration = narr
    edl.target_duration_sec = narr.duration
    a = _analysis()
    a.scenes[3] = a.scenes[3].model_copy(update={"usable": True, "reasons": []})
    # klip b-roll terpisah untuk segmen 2
    from autoreels.analyze.models import ClipInfo, Scene

    a.clips.append(ClipInfo(name="b.mp4", path="b.mp4", hash="y", duration=20, width=1280, height=720, fps=30,
                            has_audio=False))
    a.scenes.append(Scene(scene_id="K2-1", source_file="b.mp4", start=0.0, end=10.0))
    edl.segments[2].source_file, edl.segments[2].scene_id = "b.mp4", "K2-1"
    edl.segments[2].start, edl.segments[2].end = 1.0, 2.0
    r = validate_edl(edl, a, STYLE, a.music, BRAND)
    assert r.ok, r.errors
    s = r.edl.segments
    assert (s[0].start, s[1].start, s[3].start) == (20.3, 31.0, 45.2)  # pembicara: tepat di waktu aslinya
    assert s[0].scene_id == "K1-5" and s[3].scene_id == "K1-10"
    assert s[2].source_file == "b.mp4" and s[2].start == 1.0           # b-roll: tidak dikunci
    assert round(s[1].output_duration * FPS) == round(3.5 * FPS)


def test_pick_speaker_prefers_isolated_face_over_crowd():
    from autoreels.render.speaker import crop_for_face, pick_speaker

    speaker = (300, 250, 14, 16)                                   # sendirian di panel kiri (galeri Zoom)
    crowd = [(800 + dx * 30, 300 + dy * 25, 14, 16) for dx in range(5) for dy in range(3)]  # penonton
    assert pick_speaker([speaker, *crowd], 720) == speaker
    assert pick_speaker(crowd, 720) is None                       # hanya kerumunan → tidak ada pembicara
    box = crop_for_face((307, 258, 16), 1280, 720)
    assert box.h == 288 and box.w == 162 and box.x <= 307 <= box.x + box.w   # zoom maks 40% tinggi frame
    assert box.w % 2 == 0 and box.h % 2 == 0


def test_hook_candidates_split_clauses_and_skip_weak_starts():
    words = _w([("Dan", 0.0, 0.3), ("ini", 0.35, 0.6), ("penting,", 0.65, 1.2),
                ("motor", 1.3, 1.7), ("kami", 1.75, 2.0), ("dicek", 2.05, 2.5), ("setiap", 2.55, 2.9), ("hari,", 2.95, 3.4),
                ("tanpa", 3.5, 3.8), ("kecuali", 3.85, 4.3), ("sama", 4.35, 4.6), ("sekali", 4.65, 5.1),
                ("bahkan", 5.2, 5.6), ("saat", 5.65, 5.9), ("libur", 5.95, 6.3), ("panjang", 6.35, 6.8),
                ("juga.", 6.85, 7.2)])
    cands = talk.hook_candidates(talk.split_sentences(words))
    texts = [c.text for c in cands]
    assert "motor kami dicek setiap hari," in texts                  # klausa di tengah kalimat panjang
    assert not any(t.startswith("Dan") for t in texts)              # diawali kata sambung → bukan kandidat
    assert all(talk.COLD_MIN <= c.duration <= talk.COLD_MAX for c in cands)


class ColdLLM:
    """Pemilih kalimat memilih semua; pemilih cold open memilih kandidat `pick`."""
    def __init__(self, pick):
        self.pick, self.purposes = pick, []

    def complete_structured(self, messages, schema, purpose="", **_):
        self.purposes.append(purpose)
        if schema is talk._ColdOpen:
            self.offered = messages[-1]["content"]
            return schema(candidate=self.pick, reason="klaim tegas")
        return schema(sentences=list(range(100)), reason="")


def _talk_transcript(tr_mod, n=12):
    words, t = [], 0.0
    for i in range(n):  # tiap kalimat: 2 klausa ±1,8 dtk dipisah koma
        words += [Word(t, t + 0.6, f"Satu{i}"), Word(t + 0.65, t + 1.2, "dua"), Word(t + 1.25, t + 1.8, "tiga,"),
                  Word(t + 1.9, t + 2.5, f"Empat{i}"), Word(t + 2.55, t + 3.1, "lima"), Word(t + 3.15, t + 3.8, "enam.")]
        t += 4.3
    return tr_mod.Transcript(path="v.mp4", model="small", language="id", duration=t, words=words)


@pytest.mark.parametrize("full", [False, True])
def test_prepare_talk_puts_cold_open_first_then_original_order(tmp_path, monkeypatch, full):
    from autoreels.analyze import transcribe as tr_mod
    from autoreels.render import audio_mix

    tr = _talk_transcript(tr_mod)
    monkeypatch.setattr(tr_mod, "transcribe", lambda *a, **k: tr)
    monkeypatch.setattr(audio_mix, "cut_audio", lambda src, ranges, out: out)
    llm = ColdLLM(pick=9)
    narr = talk.prepare_talk(tmp_path / "v.mp4", tmp_path, speaker_clip="v.mp4", llm=llm, model="m", full=full,
                             log=lambda *_: None)
    import re as _re
    offered = _re.findall(r"K(\d+) \| ([\d.]+) dtk \| (.+)", llm.offered)
    k, dur, text = next(o for o in offered if o[0] == "9")
    assert narr.words[0].text == text.split()[0]                                     # teaser di detik 0
    assert narr.cold_open_sec == pytest.approx(float(dur), abs=0.25)
    n = sum(1 for p in narr.phrases if p.start < narr.cold_open_sec - 0.01)
    rest = [p.src_start for p in narr.phrases[n:]]
    assert rest == sorted(rest) and rest[0] < narr.phrases[0].src_start              # lalu isi dari awal, urutan asli
    assert not any(o[2].startswith("Satu0 ") for o in offered)                      # 8 dtk pertama isi tidak ditawarkan
    assert ("talk_select" in llm.purposes) is (not full)


def test_prepare_talk_skips_cold_open_when_ai_declines(tmp_path, monkeypatch):
    from autoreels.analyze import transcribe as tr_mod
    from autoreels.render import audio_mix

    tr = _talk_transcript(tr_mod)
    monkeypatch.setattr(tr_mod, "transcribe", lambda *a, **k: tr)
    monkeypatch.setattr(audio_mix, "cut_audio", lambda src, ranges, out: out)
    narr = talk.prepare_talk(tmp_path / "v.mp4", tmp_path, speaker_clip="v.mp4", llm=ColdLLM(pick=-1), model="m",
                             full=True, log=lambda *_: None)
    starts = [p.src_start for p in narr.phrases]
    assert starts == sorted(starts) and narr.words[0].text == "Satu0" and narr.cold_open_sec == 0


def test_promo_signal_detects_service_mentions_only():
    from autoreels.pipeline import promo_signal

    brand = {"short_name": "Brand", "company_name": "Contoh Brand"}
    lecture = Narration(file="n.wav", duration=5, phrases=[Phrase(start=0, end=5, text="Air adalah persenyawaan.")])
    staff = Narration(file="n.wav", duration=5, phrases=[Phrase(start=0, end=5, text="Sewa motor bisa diantar.")])
    assert not promo_signal("Potongan kuliah umum tentang bahasa", lecture, brand)
    assert promo_signal("", staff, brand)
    assert promo_signal("Profil singkat Brand", None, brand)


def test_stable_box_reuses_similar_crop_and_switches_on_new_shot():
    from autoreels.render.speaker import CropBox, stable_box

    a = CropBox(466, 0, 332, 590)
    assert stable_box(a, CropBox(472, 4, 328, 584)) is a          # shot sama, geser sedikit → crop tetap
    gallery = CropBox(238, 174, 162, 288)
    assert stable_box(a, gallery) is gallery                      # pindah ke galeri → crop baru
    assert stable_box(None, gallery) is gallery and stable_box(a, None) is None


def test_speaker_to_speaker_transition_forced_to_cut():
    phrases = [Phrase(start=0.0, end=2.5, text="a", src_start=20.3), Phrase(start=2.5, end=6.0, text="b", src_start=31.0),
               Phrase(start=6.0, end=9.0, text="c", src_start=40.0), Phrase(start=9.0, end=12.0, text="d", src_start=45.2)]
    narr = Narration(file="narasi.wav", duration=12.0, phrases=phrases, speaker_clip="a.mp4",
                     words=[NarrationWord(start=p.start + 0.1, end=p.end - 0.1, text=p.text) for p in phrases])
    edl = _edl()
    edl.segments = edl.segments[:3] + edl.segments[-1:]
    for i, s in enumerate(edl.segments):
        s.index, s.transition_in = i, "zoom_punch"
    edl.narration, edl.target_duration_sec = narr, 12.0
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert [s.transition_in.value for s in r.edl.segments[1:]] == ["cut", "cut", "cut"]


def test_job_endpoint_validates_talk_clip_and_purpose(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from autoreels import server

    footage = tmp_path / "footage"
    (footage / "podcast").mkdir(parents=True)
    (footage / "podcast" / "a.mp4").write_bytes(b"\x00")
    monkeypatch.setattr(server, "FOOTAGE", footage)
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "_videos_in", lambda folder: sorted(folder.glob("*.mp4")))
    monkeypatch.setattr(server, "_probe_cached", lambda p: type("Info", (), {"duration": 90.0})())
    submitted = []
    monkeypatch.setattr(server.RUNNER, "submit", lambda job_id, fn, label="": submitted.append(job_id))
    client = TestClient(server.app)
    base = {"input_path": "footage/podcast", "pillar": "profil", "style": "info_lowongan", "brief": "uji"}
    assert client.post("/api/jobs", json={**base, "talk_clip": "lain.mp4"}).status_code == 400
    assert client.post("/api/jobs", json={**base, "talk_clip": "a.mp4", "purpose": "jualan"}).status_code == 400
    ok = client.post("/api/jobs", json={**base, "talk_clip": "a.mp4", "purpose": "informasi"})
    assert ok.status_code == 200, ok.text and submitted


def test_pick_active_chooses_moving_mouth_and_abstains_when_unclear():
    from autoreels.render.speaker import pick_active

    # dua tamu berdampingan: kanan bicara (gerak mulut besar), kiri diam
    samples = [[(700, 400, 170, 1.0), (1300, 420, 170, 6.0)] for _ in range(5)]
    cx, cy, fh = pick_active(samples, 1080)
    assert cx == 1300 and fh == 170
    unclear = [[(700, 400, 170, 3.0), (1300, 420, 170, 3.2)] for _ in range(5)]
    assert pick_active(unclear, 1080) is None                   # tidak jelas siapa yang bicara → serahkan ke cara lain


def test_piecewise_crop_switches_at_camera_cut():
    from autoreels.edl import Reframe
    from autoreels.render.cut import _source_chain
    from autoreels.render.speaker import CropBox

    class Clip:
        width, height = 1920, 1080

    shots = [(0.0, CropBox(1094, 0, 606, 1080)), (1.733, CropBox(604, 0, 606, 1080))]
    g = _source_chain(0, 49.0, 53.0, 1.0, Reframe.subject_track, Clip, None, 4.0, "v", box=shots)
    assert "crop=606:1080:x='if(lt(t,1.733),1094,604)'" in g


def test_prepare_talk_full_keeps_all_sentences_in_order(tmp_path, monkeypatch):
    from autoreels.analyze import transcribe as tr_mod
    from autoreels.render import audio_mix

    words = []
    t = 0.0
    for i in range(12):  # 12 kalimat ±4 dtk
        words += [Word(t, t + 1.8, f"Kalimat{i}"), Word(t + 1.9, t + 3.8, f"isi{i}.")]
        t += 4.3
    tr = tr_mod.Transcript(path="v.mp4", model="small", language="id", duration=t, words=words)
    monkeypatch.setattr(tr_mod, "transcribe", lambda *a, **k: tr)
    monkeypatch.setattr(audio_mix, "cut_audio", lambda src, ranges, out: out)

    class NoLLM:
        def complete_structured(self, *a, **k):
            raise AssertionError("mode utuh tidak boleh memanggil AI pemilih kalimat")

    narr = talk.prepare_talk(tmp_path / "v.mp4", tmp_path, speaker_clip="v.mp4", llm=NoLLM(), model="m", full=True,
                             cold_open=False, log=lambda *_: None)
    assert narr.words[0].text == "Kalimat0" and narr.words[-1].text == "isi11."
    assert narr.duration > 45  # tidak diringkas ke 30–45 dtk
    assert [p.src_start for p in narr.phrases] == sorted(p.src_start for p in narr.phrases)  # urutan asli


def test_edl_allows_reels_up_to_three_minutes():
    edl = _edl(target_duration_sec=170)
    assert edl.target_duration_sec == 170
    with pytest.raises(Exception):
        _edl(target_duration_sec=200)


def test_talk_hook_never_gets_auto_before_after_on_speaker():
    phrases = [Phrase(start=0.0, end=2.5, text="a", src_start=20.3), Phrase(start=2.5, end=6.0, text="b", src_start=31.0),
               Phrase(start=6.0, end=9.0, text="c", src_start=40.0), Phrase(start=9.0, end=12.0, text="d", src_start=45.2)]
    narr = Narration(file="narasi.wav", duration=12.0, phrases=phrases, speaker_clip="a.mp4",
                     words=[NarrationWord(start=p.start + 0.1, end=p.end - 0.1, text=p.text) for p in phrases])
    edl = _edl(hook={"type": "before_after", "overlay_text": "Sebelum sesudah", "source_segment_index": 0})
    edl.segments = edl.segments[:3] + edl.segments[-1:]
    for i, s in enumerate(edl.segments):
        s.index = i
    edl.narration, edl.target_duration_sec = narr, 12.0
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND, descriptions={})
    assert r.edl.segments[0].compare is None


def test_hook_text_moves_below_speaker_head():
    from autoreels.render.speaker import crop_for_face
    from autoreels.render.text_ass import HOOK_Y, KARAOKE_TOP, SAFE_TOP, hook_position

    box = crop_for_face((960, 400, 120), 1920, 1080)       # wajah di 32% tinggi crop (setengah badan)
    head = box.face_out(1920)
    assert head[0] < HOOK_Y < head[1]                        # posisi bawaan tepat menutupi kepala
    y, size = hook_position(2, 118, [head])
    half = 2 * size * 1.12 / 2
    assert y - half >= head[1] and y + half <= KARAOKE_TOP   # di bawah dagu, di atas subtitle karaoke
    huge = [(SAFE_TOP + 20, KARAOKE_TOP - 250)]              # wajah besar, ruang sempit → font mengecil, tetap tak menutupi
    y2, size2 = hook_position(2, 118, huge)
    assert size2 < 118 and (y2 + 2 * size2 * 1.12 / 2 <= huge[0][0] or y2 - 2 * size2 * 1.12 / 2 >= huge[0][1])
    assert hook_position(2, 118, None) == (HOOK_Y, 118)


def _talk_edl(sources, cold=0.0):
    phrases = [Phrase(start=i * 2.0, end=i * 2.0 + 2.0, text=f"p{i}", src_start=10.0 + i * 2) for i in range(len(sources))]
    edl = _edl()
    edl.segments = edl.segments[:len(sources)]
    for i, (s, src) in enumerate(zip(edl.segments, sources)):
        s.index, s.source_file = i, src
    edl.narration = Narration(file="narasi.wav", duration=len(sources) * 2.0, phrases=phrases, speaker_clip="a.mp4",
                              cold_open_sec=cold)
    return edl


def test_talk_layout_keeps_speaker_on_hook_end_and_majority():
    from autoreels.validate import _enforce_talk_layout

    edl = _talk_edl(["b.mp4"] * 10, cold=4.0)
    fixes = []
    _enforce_talk_layout(edl, fixes.append)
    src = [s.source_file for s in edl.segments]
    assert src[0] == src[1] == src[-1] == "a.mp4"                        # hook + cold open (P1–P2) + penutup
    runs = "".join("b" if x == "b.mp4" else "a" for x in src)
    assert "bbb" not in runs                                             # maks 2 b-roll berurutan
    assert runs.count("a") / len(runs) >= 0.6 and fixes


def test_talk_layout_leaves_valid_broll_alone():
    from autoreels.validate import _enforce_talk_layout

    edl = _talk_edl(["a.mp4", "a.mp4", "b.mp4", "a.mp4", "a.mp4", "b.mp4", "a.mp4", "a.mp4", "a.mp4", "a.mp4"])
    fixes = []
    _enforce_talk_layout(edl, fixes.append)
    assert [s.source_file for s in edl.segments].count("b.mp4") == 2 and not fixes


def test_broll_suggestions_match_spoken_words_to_scenes():
    from types import SimpleNamespace as NS

    from autoreels.describe import SceneDescription

    phrases = [Phrase(start=0, end=2, text="Halo semua"), Phrase(start=2, end=4.5, text="motornya kami cek setiap pagi"),
               Phrase(start=4.5, end=7, text="pelayanannya ramah sekali"), Phrase(start=7, end=9, text="motor terakhir")]
    scenes = [NS(scene_id="K1-1", source_file="a.mp4", duration=30), NS(scene_id="K2-1", source_file="b.mp4", duration=5),
              NS(scene_id="K2-2", source_file="b.mp4", duration=1)]
    desc = {"K1-1": SceneDescription(scene_id="K1-1", subject="motor pembicara"),
            "K2-1": SceneDescription(scene_id="K2-1", subject="motor matic berjajar", setting="garasi"),
            "K2-2": SceneDescription(scene_id="K2-2", subject="motor", setting="jalan")}
    out = talk.broll_suggestions(phrases, scenes, desc, "a.mp4")
    assert out == ["P2 → K2-1 (cocok: motor)"]   # bukan klip pembicara, adegan cukup panjang, bukan hook/penutup
