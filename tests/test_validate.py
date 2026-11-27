"""Tes aturan keras validator (tanpa video/LLM)."""

from __future__ import annotations

from autoreels.analyze.models import Analysis, ClipInfo, MusicInfo, Scene
from autoreels.edl import EDL
from autoreels.validate import validate_edl

STYLE = {
    "cut_pace_sec": [0.6, 1.2],
    "transitions": ["cut", "zoom_punch"],
    "music_mood_default": "upbeat",
    "speed_range": [1.0, 1.5],
}
BRAND = {"default_cta": {"rental": "Booking via WhatsApp!"}, "whatsapp": {"display": "(000) 0000000"}}


def _analysis() -> Analysis:
    clips = [ClipInfo(name="a.mp4", path="a.mp4", hash="x", duration=60, width=1280, height=720, fps=30,
                      has_audio=False)]
    scenes = [Scene(scene_id=f"K1-{i + 1}", source_file="a.mp4", start=i * 5.0, end=(i + 1) * 5.0)
              for i in range(12)]
    scenes[3] = scenes[3].model_copy(update={"usable": False, "reasons": ["blur"]})
    music = MusicInfo(path="m.mp3", mood="upbeat", tempo=120, duration=100, start_offset=0,
                      beats=[round(0.5 * i, 3) for i in range(1, 80)])
    return Analysis(clips=clips, scenes=scenes, music=music)


def _edl(**over) -> EDL:
    segs = [{"index": 0, "source_file": "a.mp4", "scene_id": "K1-1", "start": 0.0, "end": 4.0, "role": "hook"}]
    t = 1
    for k in range(12):
        sc = [0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11][k % 11]
        segs.append({"index": t, "source_file": "a.mp4", "scene_id": f"K1-{sc + 1}",
                     "start": sc * 5.0 + 1.0, "end": sc * 5.0 + 2.03, "role": "isi"})
        t += 1
    segs.append({"index": t, "source_file": "a.mp4", "scene_id": "K1-12", "start": 55.0, "end": 58.0,
                 "role": "cta"})
    data = {
        "pillar": "rental", "target_duration_sec": 18, "style_preset": "rental_energik",
        "hook": {"type": "visual_wow", "overlay_text": "Keliling Garut pakai motor", "source_segment_index": 0},
        "segments": segs,
        "cta": {"text": "Booking sekarang!", "at_sec": 15},
        "caption_suggestion": "Keliling Garut makin seru pakai motor sewaan. Booking lewat WhatsApp ya!",
        "hashtags": ["#garut"],
    }
    data.update(over)
    return EDL.model_validate(data)


def test_hook_trimmed_and_cuts_on_beat():
    r = validate_edl(_edl(), _analysis(), STYLE, _analysis().music, BRAND, ["#rentalmotorgarut"])
    assert r.edl.segments[0].output_duration <= 3.0
    assert r.stats["beat_accuracy"] >= 0.9
    assert r.edl.hashtags[0] == "#rentalmotorgarut"
    assert r.ok, r.errors


def test_unusable_scene_rejected():
    edl = _edl()
    edl.segments[1].scene_id = "K1-4"
    edl.segments[1].start, edl.segments[1].end = 16.0, 17.0
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert any("tidak layak" in e for e in r.errors)


def test_placeholder_is_error():
    edl = _edl(hook={"type": "harga", "overlay_text": "Sewa motor mulai [HARGA]/hari", "source_segment_index": 0})
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert any("placeholder" in e for e in r.errors)


def test_style_transition_and_mood_enforced():
    edl = _edl(music={"mood": "santai"})
    edl.segments[2].transition_in = "whip"
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert r.edl.music.mood.value == "upbeat"
    assert r.edl.segments[2].transition_in.value == "cut"


def test_too_short_is_filled_automatically():
    edl = _edl(target_duration_sec=24)
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert abs(r.stats["total_duration"] - 24) <= 2.4, r.stats
    assert any("ditambahkan otomatis" in f for f in r.fixes)


def test_too_long_segments_trimmed_to_pace():
    edl = _edl()
    edl.segments[1].end = edl.segments[1].start + 3.5
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert r.edl.segments[1].output_duration <= 1.2 + 1e-6


def test_impossible_duration_is_error():
    edl = _edl(target_duration_sec=90)
    r = validate_edl(edl, _analysis(), STYLE, None, BRAND)
    assert any("terlalu pendek" in e for e in r.errors)


def test_beat_snap_does_not_drift_with_many_short_segments():
    """136 BPM (beat 0,441 dtk ≠ kelipatan frame): pembulatan frame per segmen tidak boleh menumpuk."""
    a = _analysis()
    a.music = a.music.model_copy(update={"tempo": 136, "beats": [round(0.441 * i, 3) for i in range(1, 120)]})
    segs = [{"index": 0, "source_file": "a.mp4", "scene_id": "K1-1", "start": 0.0, "end": 2.2, "role": "hook"}]
    for k in range(1, 16):
        sc = [0, 1, 2, 4, 5, 6, 7, 8, 9, 10][k % 10]
        segs.append({"index": k, "source_file": "a.mp4", "scene_id": f"K1-{sc + 1}",
                     "start": sc * 5.0 + 0.5, "end": sc * 5.0 + 1.38, "role": "isi"})
    segs.append({"index": 16, "source_file": "a.mp4", "scene_id": "K1-12", "start": 55.0, "end": 58.5, "role": "cta"})
    r = validate_edl(_edl(segments=segs, target_duration_sec=20), a, STYLE, a.music, BRAND)
    assert r.stats["beat_accuracy"] >= 0.95, r.stats


def test_zoom_punch_added_when_style_requires_it():
    style = {**STYLE, "zoom_punch_on_emphasis": True}
    edl = _edl()
    for s in edl.segments:
        s.transition_in = "cut"
    r = validate_edl(edl, _analysis(), style, _analysis().music, BRAND)
    zp = [s.index for s in r.edl.segments if s.transition_in.value == "zoom_punch"]
    assert 1 <= len(zp) <= 3 and 0 not in zp and r.edl.segments[-1].index not in zp
    assert any("zoom-punch ditambahkan" in f for f in r.fixes)


def test_hook_slightly_long_but_big_is_warning_not_error():
    ok = validate_edl(_edl(hook={"type": "visual_wow", "overlay_text": "Indonesia: Sebuah Persenyawaan",
                                 "source_segment_index": 0}), _analysis(), STYLE, None, BRAND)
    assert not any("hook.overlay_text" in e for e in ok.errors)
    assert any("masih tampil besar" in w for w in ok.warnings)
    bad = validate_edl(_edl(hook={"type": "visual_wow", "overlay_text": "Indonesia sebagai sebuah persenyawaan",
                                  "source_segment_index": 0}), _analysis(), STYLE, None, BRAND)
    assert any("terlalu panjang" in e for e in bad.errors)


def test_informational_video_has_no_cta():
    r = validate_edl(_edl(purpose="informasi"), _analysis(), STYLE, None, BRAND)
    assert r.ok, r.errors
    assert r.edl.cta is None and r.edl.segments[-1].role.value != "cta"
    promo = validate_edl(_edl(cta=None), _analysis(), STYLE, None, BRAND)
    assert promo.edl.cta is not None  # promosi tanpa CTA → CTA default brand


def test_no_music_choice_is_kept():
    r = validate_edl(_edl(music={"mood": "none"}), _analysis(), STYLE, None, BRAND)
    assert r.edl.music.mood.value == "none" and not r.edl.music.cut_on_beat
    forced = validate_edl(_edl(music={"mood": "santai"}), _analysis(), STYLE, None, BRAND)
    assert forced.edl.music.mood.value == "upbeat"  # pilihan mood lain tetap diselaraskan ke gaya

