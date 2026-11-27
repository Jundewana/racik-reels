"""Tes API AutoReels Studio (tanpa menjalankan pipeline/LLM)."""

from __future__ import annotations

import shutil

import pytest
from fastapi.testclient import TestClient

from autoreels import config_editor as ce
from autoreels.config import PATHS
from autoreels.server import app

client = TestClient(app)


def test_options_contract():
    r = client.get("/api/options")
    assert r.status_code == 200
    data = r.json()
    assert [p["id"] for p in data["pillars"]] == ["rental", "konstruksi", "profil", "lowongan", "umum"]
    assert {"id", "description", "cut_pace_sec", "music_mood_default"} <= set(data["styles"][0])
    assert data["hook_limits"] == {"max_words": 5, "max_chars": 28}
    assert any(f["path"] == "footage/rental" for f in data["footage_folders"])


def test_footage_path_traversal_rejected():
    r = client.get("/api/footage", params={"folder": "../config"})
    assert r.status_code == 400
    assert "footage" in r.json()["error"]


def test_unknown_job_returns_error_json():
    r = client.get("/api/jobs/tidak-ada-123/progress")
    assert r.status_code == 404
    assert "error" in r.json()
    assert client.get("/api/jobs/..%2F..%2Fetc").status_code in (400, 404)


def test_jobs_list_and_detail_shape():
    jobs = client.get("/api/jobs").json()["jobs"]
    if not jobs:
        pytest.skip("belum ada hasil di output/")
    detail = client.get(f"/api/jobs/{jobs[0]['job_id']}").json()
    for key in ("status", "reel_url", "caption", "stats", "checklist", "edl", "report_md"):
        assert key in detail
    assert detail["reel_url"].startswith("/media/output/")


def test_create_job_validates_input():
    r = client.post("/api/jobs", json={"input_path": "footage/rental", "pillar": "kuliner",
                                       "style": "rental_energik"})
    assert r.status_code == 400 and "Pilar" in r.json()["error"]


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


def test_config_roundtrip(sandbox):
    hooks = client.get("/api/config/hooks").json()
    hooks["rental"].append({"type": "pertanyaan", "text": "Mau ke Garut?"})
    assert client.put("/api/config/hooks", json=hooks).json() == {"ok": True}
    assert client.get("/api/config/hooks").json()["rental"][-1]["text"] == "Mau ke Garut?"

    assert client.put("/api/config/pillars/rental",
                      json={"hashtags": ["#Garut", "sewa motor"], "keywords": ["Sewa Motor Garut"]}).json()["ok"]
    seo = client.get("/api/config/pillars/rental").json()
    assert seo["hashtags"] == ["#garut", "#sewa", "#motor"] or "#garut" in seo["hashtags"]
    assert seo["keywords"] == ["sewa motor garut"]

    client.put("/api/config/trends", json={"formats": ["POV naik motor"], "hooks": [], "audio": [],
                                           "moments": [], "notes": []})
    trends = client.get("/api/config/trends").json()
    assert trends["formats"] == ["POV naik motor"] and trends["updated"]

    client.put("/api/config/brand", json={"price_per_day": "Rp100.000", "default_cta": {"rental": "Hayu booking!"}})
    brand = client.get("/api/config/brand").json()
    assert brand["price_per_day"] == "Rp100.000" and brand["default_cta"]["rental"] == "Hayu booking!"

    client.put("/api/config/caption-guide", json={"fields": {"Sapaan": "kak"}, "examples": ["Contoh satu."]})
    guide = client.get("/api/config/caption-guide").json()
    assert guide["fields"]["Sapaan"] == "kak" and guide["examples"] == ["Contoh satu."]


def test_active_jobs_lists_running_job_until_done():
    """Job yang berjalan harus bisa ditemukan lagi oleh web (pindah halaman / refresh)."""
    import shutil
    import threading

    from fastapi.testclient import TestClient

    from autoreels.config import PATHS
    from autoreels.server import RUNNER, app

    client = TestClient(app)
    release = threading.Event()
    job_id = RUNNER.new_id("rental")
    try:
        RUNNER.submit(job_id, lambda log: release.wait(5), label="tes", kind="import")
        for _ in range(50):
            jobs = client.get("/api/jobs/active").json()["jobs"]
            if any(j["job_id"] == job_id and j["state"] == "berjalan" for j in jobs):
                break
            threading.Event().wait(0.05)
        match = [j for j in jobs if j["job_id"] == job_id]
        assert match and match[0]["kind"] == "import"
        release.set()
        for _ in range(50):
            if not any(j["job_id"] == job_id for j in client.get("/api/jobs/active").json()["jobs"]):
                break
            threading.Event().wait(0.05)
        assert not any(j["job_id"] == job_id for j in client.get("/api/jobs/active").json()["jobs"])
    finally:
        release.set()
        shutil.rmtree(PATHS["work"] / job_id, ignore_errors=True)
