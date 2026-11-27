"""Perbaikan risiko R1 (job tertinggal), R3 (kunci job CLI/web), R4 (batas PIN), dan speed-up otomatis."""

from __future__ import annotations

import json
import os

import pytest

from autoreels import joblock
from autoreels.describe import SceneDescription
from autoreels.validate import validate_edl
from tests.test_validate import BRAND, _analysis, _edl


# ---------- R3: kunci job ----------
def test_lock_acquire_release(tmp_path):
    lf = tmp_path / ".job.lock"
    with joblock.job_lock("tes", "job1", lock_file=lf):
        holder = json.loads(lf.read_text(encoding="utf-8"))
        assert holder["pid"] == os.getpid() and holder["job_id"] == "job1"
    assert not lf.exists()


def test_lock_busy_when_other_live_process_holds_it(tmp_path, monkeypatch):
    lf = tmp_path / ".job.lock"
    lf.write_text(json.dumps({"pid": 4242, "label": "terminal: autoreels run"}), encoding="utf-8")
    monkeypatch.setattr(joblock, "pid_alive", lambda pid: pid == 4242)
    with pytest.raises(joblock.JobBusyError, match="terminal: autoreels run"):
        with joblock.job_lock("web", lock_file=lf):
            pass
    assert lf.exists()  # kunci milik proses lain tidak boleh dihapus


def test_stale_lock_from_dead_process_is_taken_over(tmp_path, monkeypatch):
    lf = tmp_path / ".job.lock"
    lf.write_text(json.dumps({"pid": 4242, "label": "lama"}), encoding="utf-8")
    monkeypatch.setattr(joblock, "pid_alive", lambda pid: pid == os.getpid())
    with joblock.job_lock("baru", lock_file=lf):
        assert json.loads(lf.read_text(encoding="utf-8"))["label"] == "baru"


def test_pid_alive_for_current_process():
    assert joblock.pid_alive(os.getpid())
    assert not joblock.pid_alive(0)


# ---------- R1: job tertinggal ----------
def test_mark_stale_jobs(tmp_path, monkeypatch):
    from autoreels import server
    from autoreels.config import PATHS

    monkeypatch.setitem(PATHS, "work", tmp_path)
    monkeypatch.setattr(joblock, "read_holder", lambda *a, **k: None)
    for job_id, state in [("20261120-100000-rental", "berjalan"), ("20261120-100001-rental", "selesai")]:
        (tmp_path / job_id).mkdir()
        (tmp_path / job_id / "progress.json").write_text(json.dumps({"job_id": job_id, "state": state}))
    marked = server.mark_stale_jobs()
    assert marked == ["20261120-100000-rental"]
    assert json.loads((tmp_path / marked[0] / "progress.json").read_text())["state"] == "gagal"
    assert "Terhenti" in (tmp_path / marked[0] / "error.txt").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "20261120-100001-rental" / "progress.json").read_text())["state"] == "selesai"


def test_mark_stale_jobs_skips_when_cli_holds_lock(tmp_path, monkeypatch):
    from autoreels import server
    from autoreels.config import PATHS

    monkeypatch.setitem(PATHS, "work", tmp_path)
    monkeypatch.setattr(joblock, "read_holder", lambda *a, **k: {"pid": 1, "label": "terminal"})
    (tmp_path / "j").mkdir()
    (tmp_path / "j" / "progress.json").write_text(json.dumps({"state": "berjalan"}))
    assert server.mark_stale_jobs() == []


# ---------- R4: batas PIN ----------
def test_pin_lockout_after_failed_attempts(monkeypatch):
    from fastapi.testclient import TestClient

    from autoreels import server

    monkeypatch.setattr(server.app.state, "pin", "123456", raising=False)
    server._pin_fails.clear()
    client = TestClient(server.app)  # host "testclient" = bukan laptop → wajib PIN
    try:
        for _ in range(server.PIN_MAX_FAILS):
            assert client.get("/?pin=000000", follow_redirects=False).status_code == 401
        r = client.get("/?pin=123456", follow_redirects=False)  # PIN benar pun ditolak selama dikunci
        assert r.status_code == 429 and "Terlalu banyak PIN salah" in r.text
        server._pin_fails.clear()
        assert client.get("/?pin=123456", follow_redirects=False).status_code == 303
    finally:
        server._pin_fails.clear()
        server.app.state.pin = None


# ---------- speed-up otomatis ----------
def test_auto_speed_for_slow_progress_scenes():
    style = {"cut_pace_sec": [0.6, 1.2], "transitions": ["cut", "zoom_punch"], "music_mood_default": "upbeat",
             "speed_range": [1.0, 8.0], "default_speed_progress": 6.0}
    desc = {f"K1-{i}": SceneDescription(scene_id=f"K1-{i}", stage="proses") for i in range(1, 13)}
    r = validate_edl(_edl(), _analysis(), style, _analysis().music, BRAND, [], desc)
    sped = [s for s in r.edl.segments if s.speed > 1.01]
    assert sped, r.fixes
    for s in sped:
        assert s.role.value in ("isi", "bukti") and s.speed >= 2.0
    assert r.edl.segments[0].speed == 1.0 and r.edl.segments[-1].speed == 1.0  # hook & CTA tidak dipercepat
    assert any("speed-up adegan proses" in f for f in r.fixes)


def test_no_auto_speed_without_style_default():
    desc = {f"K1-{i}": SceneDescription(scene_id=f"K1-{i}", stage="proses") for i in range(1, 13)}
    style = {"cut_pace_sec": [0.6, 1.2], "transitions": ["cut"], "music_mood_default": "upbeat",
             "speed_range": [1.0, 1.5]}
    r = validate_edl(_edl(), _analysis(), style, _analysis().music, BRAND, [], desc)
    assert all(s.speed <= 1.5 for s in r.edl.segments)
    assert not any("speed-up adegan proses" in f for f in r.fixes)
