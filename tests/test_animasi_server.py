import json

import pytest
from fastapi.testclient import TestClient

from autoreels import animasi, server_animasi
from autoreels.musik_sintesis import SR, compose, sfx_track, validate_score


@pytest.fixture()
def tmp_anim(tmp_path, monkeypatch):
    pub = tmp_path / "public"
    work = tmp_path / "work"
    monkeypatch.setattr(animasi, "PUBLIC", pub)
    monkeypatch.setattr(animasi, "work_dir", lambda name: work / "_animasi" / name)
    monkeypatch.setitem(server_animasi.PATHS, "work", work)
    monkeypatch.setitem(server_animasi.PATHS, "output", tmp_path / "output")
    (tmp_path / "output").mkdir()
    d = pub / "uji-a"
    d.mkdir(parents=True)
    data = {"nama": "uji-a", "pilar": "rental", "brief": "", "durasi": 2.0, "fps": 30,
            "kata": [{"start": 0.0, "end": 0.4, "text": "ping"}, {"start": 0.5, "end": 0.9, "text": "motor"}],
            "frasa": [{"start": 0.0, "end": 2.0, "text": "ping motor"}],
            "audio": {"narasi": "uji-a/narasi.wav", "musik": None, "musik_db": -20}, "brand": {}}
    (d / "data.json").write_text(json.dumps(data), encoding="utf-8")
    import autoreels.server as s

    return TestClient(s.app)


def test_transcript_edit_keeps_timing(tmp_anim):
    c = tmp_anim
    assert c.put("/api/animasi/uji-a/transkrip", json={"kata": ["x"]}).status_code == 400
    assert c.put("/api/animasi/uji-a/transkrip", json={"kata": ["pusing", "motor"]}).status_code == 200
    d = animasi.load_data("uji-a")
    assert [w["text"] for w in d["kata"]] == ["pusing", "motor"]
    assert d["kata"][0]["start"] == 0.0 and d["frasa"][0]["text"] == "pusing motor"


def test_detail_while_preparing_and_unknown(tmp_anim):
    c = tmp_anim
    server_animasi._set("uji-b", langkah="siapkan", state="berjalan", pilar="konstruksi", brief="tes")
    r = c.get("/api/animasi/uji-b")
    assert r.status_code == 200 and r.json()["siap"] is False and r.json()["pilar"] == "konstruksi"
    assert c.get("/api/animasi/tidak-ada").status_code == 404
    names = [v["nama"] for v in c.get("/api/animasi").json()["videos"]]
    assert {"uji-a", "uji-b"} <= set(names)


def test_render_needs_code(tmp_anim):
    assert tmp_anim.post("/api/animasi/uji-a/render").status_code == 400  # belum ada Video.tsx


def test_claude_child_env_has_no_api_key(monkeypatch):
    """Claude Code dari web wajib memakai login langganan: ANTHROPIC_API_KEY tidak boleh diteruskan."""
    seen = {}

    class FakeProc:
        stdout = iter(['{"type":"result","is_error":false,"result":"ok","total_cost_usd":0}\n'])
        returncode = 0
        pid = 1

        def wait(self):
            return 0

        def poll(self):
            return 0

    def fake_popen(cmd, **kw):
        seen["env"], seen["cmd"] = kw["env"], cmd
        return FakeProc()

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-rahasia")
    monkeypatch.setattr(server_animasi.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(server_animasi, "_claude_exe", lambda: "claude")
    monkeypatch.setattr(server_animasi, "_set", lambda *a, **k: {})
    monkeypatch.setattr(server_animasi, "_status", lambda n: {"state": "berjalan"})
    monkeypatch.setattr(server_animasi, "_latest_job_from_output", lambda n: None)
    monkeypatch.setattr(animasi, "load_data", lambda n: {"gaya": "kertas"})
    server_animasi._run_claude("uji-a", "")
    assert "'kertas'" in seen["cmd"][2]  # gaya video diteruskan ke Claude
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    assert "WebFetch,WebSearch,PowerShell" in seen["cmd"]


def test_style_api(tmp_anim):
    c = tmp_anim
    assert c.put("/api/animasi/uji-a/gaya", json={"gaya": "neon-malam"}).status_code == 200
    assert animasi.load_data("uji-a")["gaya"] == "neon-malam"
    assert c.put("/api/animasi/uji-a/gaya", json={"gaya": "tidak-ada"}).status_code == 400
    ids = [g["id"] for g in c.get("/api/animasi").json()["styles"]]
    assert "racik-flat" in ids and len(ids) >= 5


def test_music_score_validation_and_length():
    assert validate_score({"bpm": 300}) and validate_score({"progresi": ["IX"]})
    score = {"bpm": 100, "kunci": "D", "skala": "mayor", "progresi": ["I", "V", "vi", "IV"],
             "bagian": [{"mulai": 0, "energi": 2}, {"mulai": 1.5, "energi": 3, "tanpa": ["melodi"]}], "aksen": [1.0]}
    out = compose(score, 3.0)
    assert out.shape == (int(SR * 3.0), 2) and abs(out).max() <= 1.0
    sfx = sfx_track([{"t": 0.5, "jenis": "whoosh"}, {"t": 2.9, "jenis": "ding"}], 3.0)
    assert sfx.shape == (int(SR * 3.0), 2) and abs(sfx).max() > 0


def test_antigravity_agent_dispatch_and_validation(tmp_anim, monkeypatch):
    from autoreels import antigravity_agent

    c = tmp_anim
    assert c.post("/api/animasi/uji-a/claude", json={"instruksi": "tes", "agen": "salah"}).status_code == 400

    called = {}

    def fake_run(nama, prompt, **kw):
        called["nama"] = nama
        called["prompt"] = prompt
        kw["on_text"]("Selesai")
        return {"ok": True, "cancelled": False, "result": "Selesai", "cost": 0.01}

    monkeypatch.setattr(antigravity_agent, "run_remotion_agent", fake_run)
    monkeypatch.setattr(server_animasi, "_latest_job_from_output", lambda n: None)
    server_animasi._run_claude("uji-a", "buat lebih ceria", agen="antigravity")
    assert called["nama"] == "uji-a"
    assert "buat lebih ceria" in called["prompt"]


def test_antigravity_writable_path_guard():
    from autoreels.antigravity_agent import is_writable_path

    assert is_writable_path("uji-a", "animasi/src/videos/uji-a/Video.tsx") is True
    assert is_writable_path("uji-a", "animasi/src/videos/index.ts") is True
    assert is_writable_path("uji-a", "work/_animasi/uji-a/caption.json") is True
    assert is_writable_path("uji-a", "animasi/src/videos/video-lain/Video.tsx") is False
    assert is_writable_path("uji-a", ".env") is False
