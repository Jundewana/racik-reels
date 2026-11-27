"""Tes konfigurasi & CLI (Tahap 0)."""

from __future__ import annotations

from typer.testing import CliRunner

from autoreels.cli import app
from autoreels.config import list_styles, load_brand, load_pillars, load_style
from autoreels.llm import strip_code_fence

runner = CliRunner()


def test_styles_present():
    assert {"rental_energik", "wisata_sinematik", "proyek_profesional", "info_lowongan"} <= set(list_styles())
    assert load_style("rental_energik")["music_mood_default"] == "upbeat"


def test_brand_and_pillars_load():
    assert load_brand()["instagram"]["main"] == "@contohbrand"
    pillars = load_pillars()
    assert set(pillars) == {"rental", "konstruksi", "profil", "lowongan", "umum"}
    for p in pillars.values():
        assert all(tag.startswith("#") and " " not in tag for tag in p["hashtags"])


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AutoReels" in result.output


def test_strip_code_fence():
    assert strip_code_fence('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert strip_code_fence('{"a": 1}') == '{"a": 1}'


def test_every_pillar_is_fully_configured():
    """Pilar baru wajib punya: entri pillars.yaml, prompt pilar, gaya bawaan yang ada, label & brief bawaan."""
    from autoreels import config_editor as ce
    from autoreels.config import PATHS, list_styles, load_pillars
    from autoreels.edl import Pillar

    cfg = load_pillars()
    assert [p.value for p in Pillar] == ce.PILLARS
    for p in ce.PILLARS:
        assert p in cfg, p
        assert (PATHS["prompts"] / "pillars" / f"{p}.md").exists(), p
        assert cfg[p].get("default_style", ce.DEFAULT_STYLE[p]) in list_styles(), p
        assert ce.PILLAR_LABELS[p] and ce.DEFAULT_BRIEF[p]
    assert cfg["umum"]["default_purpose"] == "informasi" and cfg["umum"]["hashtags"] == []
