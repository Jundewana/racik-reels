"""Varian dari satu proyek: permintaan asli dipakai ulang, hanya durasi/tujuan/ringkas-utuh yang berubah."""

from __future__ import annotations

import json
import shutil

import pytest
from fastapi.testclient import TestClient

from autoreels import server
from autoreels.config import PATHS

client = TestClient(server.app)


@pytest.fixture
def fake_job(monkeypatch):
    made = []

    def make(job_id, meta, request=None):
        out, work = PATHS["output"] / job_id, PATHS["work"] / job_id
        out.mkdir(parents=True, exist_ok=True)
        (out / "job.json").write_text(json.dumps(meta), encoding="utf-8")
        if request is not None:
            work.mkdir(parents=True, exist_ok=True)
            (work / "request.json").write_text(json.dumps(request), encoding="utf-8")
        made.append(job_id)
        return job_id

    submitted = []
    monkeypatch.setattr(server, "create_job", lambda body: submitted.append(body) or {"job_id": f"v{len(submitted)}"})
    yield make, submitted
    for j in made:
        shutil.rmtree(PATHS["output"] / j, ignore_errors=True)
        shutil.rmtree(PATHS["work"] / j, ignore_errors=True)


REQUEST = {"input_path": "footage/rental", "pillar": "rental", "brief": "Promo libur", "style": "rental_energik",
           "duration": 20, "music_file": "upbeat/lagu.mp3", "voice": "Kore", "clips": ["a.mp4", "b.mp4"]}


def test_variants_reuse_original_request(fake_job):
    make, submitted = fake_job
    jid = make("20991231-000001-rental", {"input": "footage/rental", "pillar": "rental", "style": "rental_energik"},
               REQUEST)
    r = client.post(f"/api/jobs/{jid}/variants", json={"variants": [{"duration": 15}, {"purpose": "informasi"}]})
    assert r.status_code == 200 and r.json()["job_ids"] == ["v1", "v2"]
    short, no_cta = submitted
    assert short.duration == 15 and short.music_file == "upbeat/lagu.mp3" and short.clips == ["a.mp4", "b.mp4"]
    assert no_cta.purpose == "informasi" and no_cta.duration == 20 and no_cta.voice == "Kore"


def test_old_narration_job_rebuilt_and_duration_rejected(fake_job):
    make, submitted = fake_job
    narr = str(server.ROOT / "footage" / "rental" / "narasi.m4a")
    jid = make("20991231-000002-rental", {
        "input": "footage/rental", "pillar": "rental", "style": "rental_energik", "brief": "x", "duration": 41.3,
        "flow": "narasi", "narration": narr, "narration_draft": "abc123", "clips": None,
        "options": {"watermark": False, "purpose": None}})
    bad = client.post(f"/api/jobs/{jid}/variants", json={"variants": [{"duration": 15}]})
    assert bad.status_code == 400 and "Video dulu" in bad.json()["error"]
    ok = client.post(f"/api/jobs/{jid}/variants", json={"variants": [{"purpose": "informasi"}]})
    assert ok.status_code == 200
    body = submitted[0]
    assert body.narration_draft == "abc123" and body.narration_path.endswith("narasi.m4a") and body.logo is False


def test_unknown_variant_keys_rejected(fake_job):
    make, _ = fake_job
    jid = make("20991231-000003-rental", {"input": "footage/rental", "pillar": "rental", "style": "rental_energik"},
               REQUEST)
    r = client.post(f"/api/jobs/{jid}/variants", json={"variants": [{"style": "wisata_sinematik"}]})
    assert r.status_code == 400
    assert client.post(f"/api/jobs/{jid}/variants", json={"variants": []}).status_code == 400
