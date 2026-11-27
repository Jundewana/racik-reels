"""Catatan keputusan AI di layar proses (Progress.note)."""

from __future__ import annotations

import json

from autoreels.pipeline import _note_director
from autoreels.progress import Progress
from tests.test_validate import _edl


def test_director_notes_written_to_progress_file(tmp_path):
    f = tmp_path / "progress.json"
    pr = Progress("job", f)
    critic = {"critic_revisions": 1, "chosen_round": 1,
              "rounds": [{"round": 0, "average": 3.6, "hook": 3, "passed": False, "summary": "Hook lemah",
                          "revision_notes": ["Sebut harga di hook"]},
                         {"round": 1, "average": 4.4, "hook": 5, "passed": True, "revision_notes": []}]}
    _note_director(pr, _edl(), critic, ["segmen 3 digeser ke momen terbaik"])
    notes = json.loads(f.read_text(encoding="utf-8"))["notes"]
    titles = [n["title"] for n in notes]
    assert titles == ["Director menyusun urutan edit", "Critic menilai (putaran 1)", "Critic menilai (putaran 2)",
                      "Director merevisi atas catatan Critic", "Aturan otomatis merapikan edit"]
    assert notes[0]["lines"][0].startswith("Hook (visual_wow): “Keliling Garut")
    assert "Catatan: Sebut harga di hook" in notes[1]["lines"]


def test_visual_note_accepts_dict_and_never_raises(tmp_path):
    from autoreels.pipeline import _note_visual

    pr = Progress("job", tmp_path / "p.json")
    _note_visual(pr, {"score": 3, "summary": "teks terpotong",
                      "issues": [{"frame": 3, "severity": "berat", "problem": "subtitle terpotong", "fix": ""}]})
    _note_visual(pr, {"error": "API mati"})
    _note_visual(pr, object())          # bentuk tak terduga → dilewati, tidak error
    assert [n["title"] for n in pr.notes] == ["AI mengecek video jadi", "AI mengecek video jadi"]
    assert pr.notes[0]["lines"][1] == "[berat] subtitle terpotong"


def test_screen_texts_matches_rendered_schedule():
    from autoreels.render.text_ass import TextEvent
    from autoreels.review import screen_texts

    ev = [TextEvent(0.0, 2.0, "hook", "Dilema Gamer?"),
          TextEvent(1.0, 4.0, "karaoke", r"{\k30}Dia {\k40}kayak\N{\k20}regen", reveal=1.0),
          TextEvent(5.0, 8.0, "cta", "Follow ya")]
    edl = _edl()
    assert screen_texts(edl, 1.5, ev) == 'teks hook: "Dilema Gamer?"'           # subtitle masih disembunyikan
    assert screen_texts(edl, 2.5, ev) == 'subtitle karaoke: "Dia kayak regen"'
    assert screen_texts(edl, 4.5, ev) == "tidak ada teks"
