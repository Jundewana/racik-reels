"""Tes voice over: naskah, penjadwalan suara, pemotongan TTS, subtitle, mixing (tanpa API)."""

from __future__ import annotations

import pytest

from autoreels.edl import VoiceLine
from autoreels.media import probe, run_ffmpeg
from autoreels.render.overlays import subtitle_chunks
from autoreels.voiceover import clean_script, schedule_lines, speakable, split_by_pauses


def test_clean_script_sorts_clamps_and_warns():
    lines, warns = clean_script([VoiceLine(at_sec=5, text="Baris dua"), VoiceLine(at_sec=0, text="Baris  satu"),
                                 VoiceLine(at_sec=99, text="kata " * 30)], total=20)
    assert [ln.text for ln in lines][:2] == ["Baris satu", "Baris dua"]
    assert lines[-1].at_sec <= 19.2
    assert warns  # baris 30 kata tidak muat di slot ±1 dtk


def test_schedule_moves_late_line_earlier():
    starts, tempo = schedule_lines([0.0, 5.0, 17.5], [2.0, 3.0, 3.6], total=20.3)
    assert tempo == 1.0
    assert starts[2] + 3.6 <= 20.3 - 0.15 + 1e-6  # baris CTA digeser lebih awal agar selesai sebelum video habis
    assert starts[1] + 3.0 <= starts[2]


def test_schedule_speeds_up_when_needed():
    starts, tempo = schedule_lines([0.0, 4.0, 8.0], [4.5, 4.5, 4.5], total=12)
    assert 1.0 < tempo <= 1.25
    assert starts[-1] + 4.5 / tempo <= 12


def test_speakable_replaces_symbols():
    assert speakable("2 helm & jas hujan") == "2 helm dan jas hujan"


def test_subtitle_chunks_split_six_words():
    ev = subtitle_chunks([(0.0, 4.0, "satu dua tiga empat lima enam tujuh delapan")], total=10)
    assert [e.text for e in ev] == ["satu dua tiga empat lima enam", "tujuh delapan"]
    assert ev[0].start == 0.0 and ev[-1].end == pytest.approx(4.0, abs=0.02)


def test_split_by_pauses_on_synthetic_speech(tmp_path):
    # tiga "kalimat" nada 1,0 dtk / 1,5 dtk / 0,8 dtk dipisah jeda 0,4 dtk
    wav = tmp_path / "full.wav"
    run_ffmpeg(["-f", "lavfi", "-i", "sine=frequency=300:duration=1.0", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-f", "lavfi", "-i", "sine=frequency=300:duration=1.5", "-f", "lavfi", "-i", "sine=frequency=300:duration=0.8",
                "-filter_complex",
                "[0]aresample=24000[a];[1]atrim=0:0.4[s1];[1]atrim=0:0.4[s2];[2]aresample=24000[b];[3]aresample=24000[c];"
                "[a][s1][b][s2][c]concat=n=5:v=0:a=1[o]", "-map", "[o]", "-ac", "1", str(wav)])
    pieces = split_by_pauses(wav, ["satu dua", "tiga empat lima", "enam"], tmp_path)
    durs = [probe(p).duration for p in pieces]
    assert durs == pytest.approx([1.0, 1.5, 0.8], abs=0.15)
