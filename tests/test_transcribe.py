"""Tahap 3: kata pengisi, jeda, rentang potong di batas kata, remap waktu, subtitle karaoke (tanpa model Whisper)."""

from __future__ import annotations

import pytest

from autoreels.analyze.transcribe import Transcript, Word, cleanup_stats, is_filler, keep_ranges, remap_words
from autoreels.render.text_ass import build_ass, karaoke_events


@pytest.mark.parametrize("word,expected", [
    ("eee", True), ("Emm,", True), ("anu", True), ("hmm...", True), ("ehm", True), ("uh", True),
    ("motor", False), ("enak", False), ("Garut", False), ("e-ktp", False), ("ya", False),
])
def test_is_filler(word, expected):
    assert is_filler(word) is expected


def _tr() -> Transcript:
    w = [Word(0.0, 0.4, "Halo"), Word(0.45, 0.8, "semua."),
         Word(0.9, 1.2, "eee", filler=True),
         Word(1.3, 1.7, "kami"), Word(1.75, 2.1, "sewa"),
         Word(3.5, 3.9, "motor"), Word(3.95, 4.3, "Garut.")]  # jeda 1,4 dtk sebelum "motor"
    return Transcript("x.wav", "small", "id", 5.0, w)


def test_pauses_and_fillers_detected():
    tr = _tr()
    assert [f.text for f in tr.fillers] == ["eee"]
    assert tr.pauses() == [(2.1, 3.5)]


def test_keep_ranges_cut_at_word_boundaries():
    tr = _tr()
    ranges = keep_ranges(tr)
    assert len(ranges) == 3  # dipisah oleh "eee" dan oleh jeda panjang
    for a, b in ranges:  # tidak ada kata (bukan pengisi) yang terpotong di tengah
        for w in tr.words:
            if not w.filler:
                assert not (a > w.start + 0.01 and a < w.end - 0.01)
                assert not (b > w.start + 0.01 and b < w.end - 0.01)
    filler = tr.fillers[0]
    assert all(b <= filler.start + 0.05 or a >= filler.end - 0.05 for a, b in ranges)  # "eee" dibuang
    st = cleanup_stats(tr, ranges)
    assert st["removed"] > 1.0 and st["fillers"] == 1 and st["long_pauses"] == 1


def test_remap_words_is_continuous_and_drops_fillers():
    tr = _tr()
    words = remap_words(tr, keep_ranges(tr))
    assert [w.text for w in words] == ["Halo", "semua.", "kami", "sewa", "motor", "Garut."]
    assert all(b.start >= a.end - 0.001 for a, b in zip(words, words[1:]))
    assert words[-1].end < 3.5  # jeda panjang & pengisi tidak lagi memakan waktu


def test_karaoke_events_timing_and_tags():
    words = [Word(0.0, 0.3, "Liburan"), Word(0.35, 0.5, "ke"), Word(0.55, 0.9, "Garut."),
             Word(1.0, 1.3, "Sewa"), Word(1.35, 1.7, "motor")]
    events = karaoke_events(words, total=2.0, vocab=frozenset())
    assert len(events) == 2  # potongan baru setelah akhir kalimat
    assert events[0].start == 0.0 and events[1].start == 1.0
    assert "{\\k35}Liburan" in events[0].text and "{\\k45\\EMPH550}Garut.{\\EMPHEND}" in events[0].text  # nama diri
    ass = build_ass(events, {}, "Montserrat")
    assert "Style: Karaoke," in ass and ass.count(",Karaoke,,") == 2


def test_karaoke_emphasis_numbers_and_places():
    from autoreels.render.text_ass import is_emphasis

    assert is_emphasis("75", False, frozenset()) and is_emphasis("ribu.", False, frozenset())
    assert is_emphasis("Rp75.000", True, frozenset()) and is_emphasis("gratis!", True, frozenset())
    assert is_emphasis("Cipanas", True, frozenset({"cipanas"}))       # kosakata brand, walau awal kalimat
    assert is_emphasis("Papandayan", False, frozenset())              # kapital di tengah kalimat
    assert not is_emphasis("Kami", True, frozenset()) and not is_emphasis("Anda", False, frozenset())
    assert not is_emphasis("motor", False, frozenset())

    words = [Word(0.0, 0.3, "Sewa"), Word(0.35, 0.6, "mulai"), Word(0.65, 0.9, "75"), Word(0.95, 1.3, "ribu")]
    ev = karaoke_events(words, total=2.0, vocab=frozenset())[0]
    assert "\\EMPH650}75{\\EMPHEND}" in ev.text and "{\\k35}Sewa" in ev.text
    ass = build_ass([ev], {"colors": {"highlight": "#FFC400", "emphasis": "#FF3B30"}}, "Montserrat")
    assert "EMPH" not in ass
    assert "\\1c&H303BFF&\\2c&H303BFF&\\t(650,770,\\fscx128\\fscy128)" in ass  # warna penekanan + pop
    plain = build_ass([ev], {"subtitle_emphasis": False}, "Montserrat")
    assert "EMPH" not in plain and "fscx128" not in plain and "}75 " in plain


def test_join_hyphen_tokens_for_reduplication():
    from autoreels.analyze.transcribe import Word, join_hyphen_tokens

    words = [Word(0.0, 0.4, "anak"), Word(0.4, 0.8, "-anak"), Word(0.9, 1.2, "masih"), Word(1.3, 1.5, "-"),
             Word(1.6, 2.0, "kecil"), Word(2.0, 2.4, "-kecil")]
    out = join_hyphen_tokens(words)
    assert [w.text for w in out] == ["anak-anak", "masih", "-", "kecil-kecil"]
    assert out[0].end == 0.8 and out[-1].start == 1.6


def test_subtitles_hidden_while_hook_shows():
    from autoreels.render.overlays import clear_hook_zone
    from autoreels.render.text_ass import TextEvent

    words = [Word(0.0, 0.4, "Stamina"), Word(0.45, 0.9, "turun."), Word(1.0, 1.5, "Maksimal"),
             Word(1.6, 2.0, "tiga"), Word(2.1, 2.6, "game"), Word(2.7, 3.4, "exhausted.")]
    evs = karaoke_events(words, total=5.0, vocab=frozenset())
    hook = TextEvent(0.0, 2.2, "hook", "Stamina gamer makin turun?")
    out = clear_hook_zone([hook, *evs], 2.2)
    kar = [e for e in out if e.kind == "karaoke"]
    assert len(kar) == 1 and kar[0].start == 1.0 and kar[0].reveal == 1.2   # potongan 1 dibuang, 2 muncul di 2,2
    ass = build_ass(out, {}, "Montserrat")
    assert r"\alpha&HFF&\t(1200,1280,\alpha&H00&)" in ass
    sub = clear_hook_zone([TextEvent(0.5, 3.0, "sub", "halo"), TextEvent(0.0, 2.0, "sub", "x")], 2.2)
    assert [(e.start, e.text) for e in sub] == [(2.2, "halo")]


def test_karaoke_unordered_words_never_make_negative_events():
    words = [Word(30.0, 30.4, "Kita"), Word(30.5, 31.0, "tahu."), Word(32.07, 32.1, "Oh,"),
             Word(31.06, 31.16, "baru"), Word(31.2, 31.5, "tau.")]
    evs = karaoke_events(words, total=34.0, vocab=frozenset())
    assert all(e.end > e.start for e in evs)
    from autoreels.render.text_ass import TextEvent

    ass = build_ass([TextEvent(0, 2, "hook", "Halo"), TextEvent(5.0, 4.9, "sub", "rusak")], {}, "Montserrat")
    assert "rusak" not in ass and ",Hook," in ass


def test_remap_words_sorted_when_cold_open_words_come_first():
    """Kata cold open (detik 25) ada di depan daftar dan juga di dalam blok isi 0–30 dtk → hasil harus urut waktu."""
    from autoreels.analyze.transcribe import Transcript, remap_words

    teaser = [Word(25.3, 25.8, "Harganya"), Word(25.9, 26.4, "545.000.")]
    body = [Word(float(t), t + 0.4, f"kata{t}") for t in range(0, 25, 2)]
    tr = Transcript(path="x", model="m", language="id", duration=31.0, words=teaser + body)
    out = remap_words(tr, [(25.2, 26.5), (0.0, 30.0)])
    assert all(b.start >= a.start for a, b in zip(out, out[1:]))
    assert out[2].text == "kata0" and abs(out[2].start - 1.3) < 0.01      # isi mulai tepat setelah teaser 1,3 dtk


def test_join_number_tokens():
    from autoreels.analyze.transcribe import join_hyphen_tokens

    out = join_hyphen_tokens([Word(0, 0.4, "545"), Word(0.4, 0.8, ".000,"), Word(1, 1.2, "4"), Word(1.2, 1.4, "-4")])
    assert [w.text for w in out] == ["545.000,", "4-4"]
