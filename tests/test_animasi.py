import json

import pytest

from autoreels import animasi


def test_check_name():
    assert animasi.check_name("rental-garut") == "rental-garut"
    for bad in ["Rental", "a", "rental garut", "../x", "-x"]:
        with pytest.raises(ValueError):
            animasi.check_name(bad)


def test_load_caption(tmp_path, monkeypatch):
    monkeypatch.setattr(animasi, "work_dir", lambda name: tmp_path / name)
    with pytest.raises(FileNotFoundError):
        animasi.load_caption("uji-a")
    d = tmp_path / "uji-a"
    d.mkdir()
    (d / "caption.json").write_text(json.dumps({"caption": "Halo Kak", "hashtags": []}), encoding="utf-8")
    with pytest.raises(ValueError):  # hashtag wajib
        animasi.load_caption("uji-a")
    (d / "caption.json").write_text(json.dumps({"caption": "Halo Kak", "hashtags": ["#garut"]}), encoding="utf-8")
    assert animasi.load_caption("uji-a")["hashtags"] == ["#garut"]


def test_render_never_calls_llm(tmp_path, monkeypatch):
    """Racik Animasi murni Claude Code: render meneruskan caption dari file sehingga importer tidak memanggil LLM."""
    monkeypatch.setattr(animasi, "work_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(animasi, "load_data", lambda name: {
        "pilar": "rental", "brief": "", "durasi": 1.0,
        "brand": {"whatsapp": "(000) 0000000", "cta_default": "Booking sekarang!"}})
    (tmp_path / "x-y").mkdir()
    (tmp_path / "x-y" / "caption.json").write_text(json.dumps({"caption": "c", "hashtags": ["#g"]}), encoding="utf-8")
    monkeypatch.setattr(animasi, "_run_node", lambda args, log=print: None)
    seen = {}

    def fake_import(**kw):
        seen.update(kw)
        return "ok"

    import autoreels.importer as importer

    monkeypatch.setattr(importer, "import_video", fake_import)
    assert animasi.render("x-y") == "ok"
    assert seen["caption"] == {"caption": "c", "hashtags": ["#g"]}
    assert seen["drawn_cta"] == "Booking sekarang! · WA (000) 0000000"
    assert seen["source"] == "animasi"
