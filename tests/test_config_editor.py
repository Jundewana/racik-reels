"""Tes pengubah config (dijalankan pada salinan file, bukan config asli)."""

from __future__ import annotations

import shutil

import pytest
import yaml

from autoreels import config_editor as ce
from autoreels.config import PATHS


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    for name in ("hooks.yaml", "pillars.yaml", "brand.yaml"):
        shutil.copy(PATHS["config"] / name, tmp_path / name)
    monkeypatch.setattr(ce, "HOOKS_FILE", tmp_path / "hooks.yaml")
    monkeypatch.setattr(ce, "PILLARS_FILE", tmp_path / "pillars.yaml")
    monkeypatch.setattr(ce, "BRAND_FILE", tmp_path / "brand.yaml")
    monkeypatch.setattr(ce, "TREND_FILE", tmp_path / "brief.md")
    monkeypatch.setattr(ce, "CAPTION_GUIDE_FILE", tmp_path / "caption_guide.md")
    return tmp_path


def test_add_and_remove_hook(sandbox):
    before = len(ce.load_hooks()["rental"])
    ce.add_hook("rental", "pertanyaan", 'Motor "ready" di Garut?')
    hooks = ce.load_hooks()
    assert hooks["rental"][-1]["text"] == 'Motor "ready" di Garut?'
    ce.remove_hook("rental", len(hooks["rental"]) - 1)
    assert len(ce.load_hooks()["rental"]) == before
    assert "MAKS 5 kata" in (sandbox / "hooks.yaml").read_text(encoding="utf-8")


def test_hook_problems():
    assert ce.hook_problems("Liburan ke Garut?") == []
    assert ce.hook_problems("Garut seindah ini kalau dijelajahi pakai motor")


def test_set_hashtags_and_keywords_keeps_other_lines(sandbox):
    ce.set_pillar_list("rental", "hashtags", ce.normalize_hashtags("#SewaMotor garut, #explore_garut"))
    ce.set_pillar_list("rental", "keywords", ce.normalize_keywords("Sewa Motor Garut, rental motor garut"))
    data = yaml.safe_load((sandbox / "pillars.yaml").read_text(encoding="utf-8"))
    assert data["rental"]["hashtags"] == ["#sewamotor", "#garut", "#explore_garut"]
    assert data["rental"]["keywords"] == ["sewa motor garut", "rental motor garut"]
    assert data["rental"]["default_style"] == "rental_energik"
    assert data["konstruksi"]["hashtags"]  # pilar lain tidak tersentuh


def test_set_brand_value_keeps_comment(sandbox):
    ig_rental_before = yaml.safe_load((sandbox / "brand.yaml").read_text(encoding="utf-8"))["instagram"]["rental"]
    ce.set_brand_value("pricing", "rental_per_day", "Rp100.000")
    text = (sandbox / "brand.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["pricing"]["rental_per_day"] == "Rp100.000"
    assert "jangan dikarang" in text  # komentar baris tetap ada
    ce.set_brand_value("default_cta", "rental", "Hayu booking via WA!")
    data = yaml.safe_load((sandbox / "brand.yaml").read_text(encoding="utf-8"))
    assert data["default_cta"]["rental"] == "Hayu booking via WA!"
    assert data["instagram"]["rental"] == ig_rental_before  # kunci 'rental' di blok lain tidak tersentuh


def test_trend_brief_roundtrip(sandbox):
    ce.write_trend_brief(formats=["POV naik motor"], hooks=[], audio=["Lagu X"], moments=[], notes=[])
    items = ce.read_trend_items()
    assert items["Format yang sedang ramai"] == ["POV naik motor"]
    assert items["Gaya hook yang naik"] == []  # placeholder [ISI] diabaikan


def test_caption_guide_roundtrip(sandbox):
    ce.write_caption_guide({"Sapaan": "kak", "Emoji": "secukupnya"}, ["Contoh caption."])
    assert ce.load_caption_guide()["Sapaan"] == "kak"
