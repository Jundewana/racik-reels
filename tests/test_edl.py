"""Tes skema EDL (Tahap 0)."""

from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from autoreels.edl import EDL

SAMPLE = {
    "version": "1.0",
    "pillar": "rental",
    "target_duration_sec": 20,
    "aspect": "9:16",
    "style_preset": "rental_energik",
    "hook": {
        "type": "visual_wow",
        "overlay_text": "Liburan ke Garut? Nggak perlu bawa motor!",
        "source_segment_index": 0,
    },
    "segments": [
        {
            "index": 0,
            "source_file": "raw_03.mp4",
            "start": 4.2,
            "end": 6.0,
            "role": "hook",
            "reason": "pemandangan terbaik dengan motor di depan",
            "reframe": "subject_track",
            "speed": 1.0,
            "transition_in": "cut",
            "overlay_text": None,
            "keep_original_audio": False,
        },
        {
            "index": 1,
            "source_file": "raw_01.mp4",
            "start": 0.0,
            "end": 8.0,
            "role": "suasana",
            "speed": 4.0,
        },
    ],
    "subtitles": {"enabled": False, "style": "bold_putih_outline", "language": "id"},
    "music": {"mood": "upbeat", "volume_db": -14, "duck_under_speech": True, "cut_on_beat": True},
    "branding": {"logo": True, "position": "top_right"},
    "privacy": {"blur_faces": False, "blur_plates": False},
    "cta": {"text": "Booking sekarang via WhatsApp!", "at_sec": 17.0},
    "caption_suggestion": "Keliling Garut pakai motor sewaan.",
    "hashtags": ["#rentalmotorgarut", "#wisatagarut", "#garut"],
    "notes_for_human": "",
}


def test_valid_sample_parses():
    edl = EDL.model_validate(SAMPLE)
    assert edl.pillar.value == "rental"
    assert len(edl.segments) == 2
    # 1.8 dtk + 8 dtk / 4x = 3.8 dtk
    assert edl.total_duration == pytest.approx(3.8)


def test_roundtrip_json(tmp_path):
    edl = EDL.model_validate(SAMPLE)
    path = edl.save(tmp_path / "edl.json")
    assert EDL.load(path) == edl


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["segments"][0].update(end=1.0),          # end < start
        lambda d: d.update(pillar="kuliner"),                 # pilar tidak dikenal
        lambda d: d.update(aspect="16:9"),                    # bukan 9:16
        lambda d: d["segments"][1].update(index=5),           # index tidak berurutan
        lambda d: d["hook"].update(source_segment_index=9),   # hook menunjuk segmen kosong
        lambda d: d.update(hashtags=["garut"]),               # hashtag tanpa '#'
        lambda d: d.update(extra_field=1),                    # field tak dikenal
        lambda d: d.update(segments=[]),                      # tanpa segmen
    ],
)
def test_invalid_edl_rejected(mutate):
    data = copy.deepcopy(SAMPLE)
    mutate(data)
    with pytest.raises(ValidationError):
        EDL.model_validate(data)


def test_json_schema_available():
    assert '"segments"' in EDL.json_schema_str()
