"""AutoReels Studio — backend API lokal (FastAPI) + penyaji web UI (folder ui/).

Jalankan:  python main.py --web   (atau: autoreels studio)  → http://127.0.0.1:8000
Kontrak API mengikuti docs/gemini_ui_brief.md bagian 5 (+ endpoint impor video).

Job dijalankan satu per satu (antrean) di thread latar agar laptop tidak kewalahan.
Default hanya 127.0.0.1 (lokal). Mode --lan: bisa dibuka dari HP di Wi-Fi yang sama, wajib PIN acak.
"""

from __future__ import annotations

import json
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote
from typing import Any, Callable

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from autoreels import config_editor as ce
from autoreels.config import ENGINES, PATHS, ROOT, get_settings, list_styles, load_brand, load_pillars, load_style
from autoreels.ingest import make_job_id
from autoreels.media import AUDIO_EXTS, VIDEO_EXTS, file_hash, probe, run_ffmpeg
from autoreels.progress import STEPS
from autoreels.voiceover import VOICES

FOOTAGE = ROOT / "footage"
# Frontend: hasil build React (frontend/dist) bila ada; cadangan: versi Alpine.js tanpa build (ui/).
REACT_DIST = ROOT / "frontend" / "dist"
UI_DIR = REACT_DIST if (REACT_DIST / "index.html").exists() else ROOT / "ui"
THUMBS = PATHS["work"] / "_cache" / "thumbs"
JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,80}$")
TREND_KEYS = {
    "formats": "Format yang sedang ramai",
    "hooks": "Gaya hook yang naik",
    "audio": "Audio trending (judul saja)",
    "moments": "Momen musiman / event Garut",
    "notes": "Catatan lain",
}
CAPTION_FIELDS = ["Sapaan", "Emoji", "Bahasa Sunda", "Kata dihindari", "Panjang"]
EXTRA_FOOTAGE_DIRS = ["impor"]  # folder unggahan video jadi
SKIP_DIRS = {"edit", "clips_graded", "verify", "animations", "transcripts", "downloads", "_narasi", "_uji"}
NARRATION_DIR = FOOTAGE / "_narasi"  # rekaman narasi alur "narasi dulu" (tidak di-commit)
NARRATION_SOURCES = [NARRATION_DIR, FOOTAGE / "_uji"]

app = FastAPI(title="AutoReels Studio", docs_url="/api/docs", redoc_url=None)


# ======================================================================================
# Error → {"error": "..."} sesuai kontrak
# ======================================================================================
@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def _any_error(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"error": f"Terjadi kesalahan di server: {exc}"}, status_code=500)


def bad(msg: str, code: int = 400) -> HTTPException:
    return HTTPException(status_code=code, detail=msg)


# ======================================================================================
# Mode LAN (akses dari HP di Wi-Fi yang sama): wajib PIN, kecuali dari laptop sendiri
# ======================================================================================
PIN_COOKIE = "autoreels_pin"
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
_PIN_PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>AutoReels Studio — PIN</title>
<style>body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
font-family:system-ui,sans-serif;background:#1B0E47;color:#fff}}form{{background:#24135C;padding:28px;
border-radius:20px;width:min(320px,86vw);text-align:center}}h1{{font-size:20px;margin:0 0 6px}}
p{{color:#c9bdf2;font-size:13px;margin:0 0 18px}}input{{width:100%;box-sizing:border-box;font-size:28px;
letter-spacing:8px;text-align:center;padding:10px;border-radius:12px;border:0;margin-bottom:14px}}
button{{width:100%;padding:12px;border:0;border-radius:12px;background:#00953F;color:#fff;font-weight:700;
font-size:16px}}.err{{color:#ffb4ae}}</style></head><body><form method="get" action="/">
<h1>AutoReels Studio</h1><p>Masukkan PIN yang tampil di terminal laptop.</p>{error}
<input name="pin" inputmode="numeric" autocomplete="one-time-code" maxlength="6" autofocus>
<button type="submit">Masuk</button></form></body></html>"""


PIN_MAX_FAILS = 5        # salah PIN sebanyak ini dari satu perangkat …
PIN_LOCK_SEC = 60        # … → dikunci sekian detik
_pin_fails: dict[str, list[float]] = {}  # ip → waktu percobaan salah (dalam jendela kunci)


def _pin_locked(client: str) -> float:
    """Sisa detik kunci untuk perangkat ini (0 = boleh mencoba)."""
    now = time.time()
    fails = [t for t in _pin_fails.get(client, []) if now - t < PIN_LOCK_SEC]
    _pin_fails[client] = fails
    return PIN_LOCK_SEC - (now - fails[-PIN_MAX_FAILS]) if len(fails) >= PIN_MAX_FAILS else 0.0


@app.middleware("http")
async def _no_cache_html(request: Request, call_next):
    """index.html selalu diperiksa ulang (setelah `npm run build` menu/halaman baru langsung tampil tanpa Ctrl+F5).
    File di /assets/ bernama ber-hash, jadi tetap boleh di-cache browser."""
    response = await call_next(request)
    path = request.url.path
    if not path.startswith(("/api/", "/media/", "/assets/")) and "text/html" in response.headers.get("content-type", ""):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.middleware("http")
async def _lan_pin_guard(request: Request, call_next):
    pin = getattr(app.state, "pin", None)
    client = request.client.host if request.client else ""
    if not pin or client in LOCAL_HOSTS:
        return await call_next(request)
    given = request.query_params.get("pin")
    if request.cookies.get(PIN_COOKIE) == pin:
        return await call_next(request)
    wait = _pin_locked(client) if given else 0.0
    if wait > 0:  # terlalu banyak salah: tolak tanpa memeriksa PIN
        from fastapi.responses import HTMLResponse

        msg = f'<p class="err">Terlalu banyak PIN salah. Coba lagi dalam {int(wait) + 1} detik.</p>'
        return HTMLResponse(_PIN_PAGE.format(error=msg), status_code=429)
    if given and given != pin:
        _pin_fails.setdefault(client, []).append(time.time())
    if given == pin:  # PIN benar → simpan cookie lalu buka aplikasi
        _pin_fails.pop(client, None)
        from fastapi.responses import RedirectResponse

        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(PIN_COOKIE, pin, httponly=True, samesite="strict", max_age=12 * 3600)
        return resp
    if request.url.path.startswith(("/api/", "/media/")):
        return JSONResponse({"error": "PIN diperlukan. Buka halaman utama dan masukkan PIN."}, status_code=401)
    from fastapi.responses import HTMLResponse

    error = '<p class="err">PIN salah, coba lagi.</p>' if given else ""
    return HTMLResponse(_PIN_PAGE.format(error=error), status_code=401)


def _lan_ip() -> str:
    """IP laptop di jaringan Wi-Fi (tanpa mengirim data keluar)."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


# ======================================================================================
# Antrean job
# ======================================================================================
class JobRunner:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.jobs: dict[str, dict[str, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="autoreels-job")

    def new_id(self, pillar: str) -> str:
        base = make_job_id(pillar)
        job_id, n = base, 2
        with self.lock:
            while job_id in self.jobs or (PATHS["work"] / job_id).exists() or (PATHS["output"] / job_id).exists():
                job_id = f"{base}-{n}"
                n += 1
            self.jobs[job_id] = {"state": "antri", "log": [], "error": None}
        return job_id

    def submit(self, job_id: str, task: Callable[[Callable[[str], None]], Any], label: str,
               kind: str = "create") -> None:
        """kind: create | import — menentukan daftar langkah proses yang ditampilkan web."""
        with self.lock:
            entry = self.jobs.setdefault(job_id, {})
            entry.update({"state": "antri", "log": [], "error": None, "label": label, "kind": kind,
                          "submitted": time.time()})
        work = PATHS["work"] / job_id
        work.mkdir(parents=True, exist_ok=True)
        (work / "log.txt").write_text("", encoding="utf-8")
        busy = sum(1 for j in self.jobs.values() if j.get("state") in ("antri", "berjalan")) - 1
        _write_progress(job_id, {
            "job_id": job_id, "percent": 0, "step": "ingest", "step_label": "Menunggu antrean",
            "step_index": 1, "steps_total": len(STEPS),
            "detail": f"{busy} job di depan" if busy > 0 else "memulai…",
            "elapsed_sec": 0, "state": "berjalan",
        })

        def log(msg: str) -> None:
            line = str(msg)
            entry["log"].append(line)
            with open(work / "log.txt", "a", encoding="utf-8") as f:
                f.write(line + "\n")

        def run() -> None:
            from autoreels.joblock import describe, job_lock

            entry["state"] = "berjalan"
            log(f"▶ {label}")
            waited = []

            def on_wait(holder: dict) -> None:
                if not waited:  # cukup sekali di log
                    log(f"  [antre] {describe(holder)} Menunggu sampai selesai …")
                waited.append(1)
                prog = _read_progress(job_id) or {}
                prog.update({"state": "berjalan", "step_label": "Menunggu antrean",
                             "detail": f"menunggu job lain selesai: {holder.get('label', '?')}"})
                _write_progress(job_id, prog)

            try:
                with job_lock(label, job_id, wait=True, on_wait=on_wait):
                    task(log)
                entry["state"] = "selesai"
            except Exception as e:  # noqa: BLE001 — semua error dilaporkan ke UI
                entry["state"] = "gagal"
                first = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
                entry["error"] = first[:400]
                log(f"[error] {e}")
                (work / "error.txt").write_text(str(e), encoding="utf-8")
                prog = _read_progress(job_id) or {}
                prog.update({"state": "gagal"})
                _write_progress(job_id, prog)

        self.executor.submit(run)

    def get(self, job_id: str) -> dict[str, Any] | None:
        return self.jobs.get(job_id)

    def active(self) -> list[tuple[str, dict[str, Any]]]:
        """Job yang sedang antri/berjalan, urut dari yang paling awal dikirim."""
        with self.lock:
            items = [(k, dict(v)) for k, v in self.jobs.items() if v.get("state") in ("antri", "berjalan")]
        return sorted(items, key=lambda kv: kv[1].get("submitted", 0))


RUNNER = JobRunner()


def _progress_file(job_id: str) -> Path:
    return PATHS["work"] / job_id / "progress.json"


def _read_progress(job_id: str) -> dict | None:
    f = _progress_file(job_id)
    for _ in range(3):  # file bisa sedang ditulis
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, OSError):
            time.sleep(0.05)
    return None


def _write_progress(job_id: str, data: dict) -> None:
    f = _progress_file(job_id)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


STALE_ERROR = "Terhenti: server atau terminal ditutup saat job berjalan. Buat ulang video ini."


def mark_stale_jobs() -> list[str]:
    """Saat server mulai: job yang tercatat "berjalan" tetapi tidak ada proses yang mengerjakannya → "gagal".
    Bila proses lain (mis. CLI) sedang memegang kunci job, tidak ada yang diubah (bisa jadi job itu masih jalan)."""
    from autoreels.joblock import read_holder

    if read_holder() is not None:
        return []
    active = {job_id for job_id, _ in RUNNER.active()}
    marked = []
    for f in PATHS["work"].glob("*/progress.json"):
        job_id = f.parent.name
        data = _read_progress(job_id)
        if not data or data.get("state") != "berjalan" or job_id in active:
            continue
        data.update({"state": "gagal"})
        _write_progress(job_id, data)
        err = f.parent / "error.txt"
        if not err.exists():
            err.write_text(STALE_ERROR, encoding="utf-8")
        marked.append(job_id)
    return marked


def _check_job_id(job_id: str) -> str:
    if not JOB_ID_RE.match(job_id):
        raise bad("ID job tidak valid.")
    return job_id


# ======================================================================================
# Helper path & media
# ======================================================================================
def _rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT).as_posix()


def _safe_footage_dir(folder: str) -> Path:
    p = (ROOT / folder).resolve()
    if FOOTAGE.resolve() not in (p, *p.parents):
        raise bad("Folder harus berada di dalam footage/.")
    if not p.is_dir():
        raise bad(f"Folder tidak ditemukan: {folder}", 404)
    return p


def _videos_in(folder: Path) -> list[Path]:
    return sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTS)


_probe_cache: dict[tuple[str, float], Any] = {}


def _duration_or_zero(p: Path) -> float:
    """Durasi video; 0 bila file tidak terbaca (dilaporkan jelas nanti saat ingest, bukan error 500 di sini)."""
    try:
        return float(_probe_cached(p).duration)
    except Exception:  # noqa: BLE001
        return 0.0


def _probe_cached(p: Path):
    key = (str(p), p.stat().st_mtime)
    if key not in _probe_cache:
        _probe_cache[key] = probe(p)
    return _probe_cache[key]


def _thumb_url(p: Path, duration: float) -> str:
    THUMBS.mkdir(parents=True, exist_ok=True)
    name = f"{file_hash(p)}.jpg"
    out = THUMBS / name
    if not out.exists():
        try:
            run_ffmpeg(["-ss", f"{min(1.0, max(0.0, duration / 2)):.2f}", "-i", str(p), "-frames:v", "1",
                        "-vf", "scale=360:-2", "-q:v", "5", str(out)])
        except Exception:  # noqa: BLE001 — thumbnail gagal tidak fatal
            return ""
    return f"/media/thumbs/{name}"


def _media_url(p: Path) -> str:
    """URL /media/output/... dengan penanda versi agar browser memuat ulang setelah render ulang."""
    return f"/media/output/{p.parent.name}/{p.name}?v={int(p.stat().st_mtime)}"


def _footage_folders() -> list[dict]:
    out: dict[str, int] = {}
    for name in [*ce.PILLARS, *EXTRA_FOOTAGE_DIRS]:
        d = FOOTAGE / name
        out[_rel(d) if d.exists() else f"footage/{name}"] = len(_videos_in(d)) if d.is_dir() else 0
    if FOOTAGE.is_dir():
        for d in sorted(FOOTAGE.rglob("*")):
            if d.is_dir() and not (SKIP_DIRS & set(d.relative_to(FOOTAGE).parts)):
                n = len(_videos_in(d))
                if n:
                    out[_rel(d)] = n
    return [{"path": k, "count": v} for k, v in out.items()]


def _music_tracks() -> list[dict]:
    root = PATHS["music"]
    tracks = sorted(f for f in root.rglob("*") if f.is_file() and f.suffix.lower() in AUDIO_EXTS)
    return [{"path": t.relative_to(root).as_posix(), "mood": t.parent.name, "name": t.stem,
             "url": f"/media/music/{t.relative_to(root).as_posix()}"} for t in tracks]


# ======================================================================================
# Options & footage
# ======================================================================================
@app.get("/api/options")
def get_options() -> dict:
    pillars_cfg = load_pillars()
    brand = load_brand()
    styles = []
    for sid in list_styles():
        st = load_style(sid)
        styles.append({"id": sid, "description": st.get("description", ""),
                       "cut_pace_sec": st.get("cut_pace_sec", [1, 2]),
                       "music_mood_default": st.get("music_mood_default", "upbeat")})
    return {
        "pillars": [{"id": p, "label": ce.PILLAR_LABELS[p],
                     "default_style": pillars_cfg.get(p, {}).get("default_style", ce.DEFAULT_STYLE[p]),
                     "default_brief": ce.DEFAULT_BRIEF[p]} for p in ce.PILLARS],
        "styles": styles,
        "music": _music_tracks(),
        "footage_folders": _footage_folders(),
        "default_cta": brand.get("default_cta", {}),
        "hook_limits": {"max_words": ce.HOOK_MAX_WORDS, "max_chars": ce.HOOK_MAX_CHARS},
        "voices": [{"id": k, "description": v} for k, v in VOICES.items()],
        "engines": _engines(),
    }


def _engines() -> list[dict]:
    """Pilihan mesin AI: API (default) atau model lokal Ollama (uji coba; tersedia bila Ollama jalan)."""
    from autoreels.llm import ollama_status

    s = get_settings()
    local = ollama_status()
    short = lambda m: m.split("/", 1)[-1]  # noqa: E731
    return [
        {"id": "api", "label": "API online", "available": True, "reason": "",
         "llm": short(s.llm_model), "vision": short(s.vision_model)},
        {"id": "local", "label": "Lokal (Ollama)",
         "available": local["running"] and not local["missing"], "reason": local["reason"],
         "llm": short(s.local_llm_model), "vision": short(s.local_vision_model)},
    ]


@app.get("/api/footage")
def get_footage(folder: str = "footage/rental") -> dict:
    d = _safe_footage_dir(folder)
    clips = []
    for v in _videos_in(d):
        info = _probe_cached(v)
        clips.append({"name": v.name, "duration": round(info.duration, 1), "width": info.display_width,
                      "height": info.display_height, "size_mb": round(v.stat().st_size / 1e6, 1),
                      "thumb_url": _thumb_url(v, info.duration),
                      "video_url": "/media/footage/" + quote(v.relative_to(FOOTAGE).as_posix())})
    return {"folder": _rel(d), "clips": clips}


def _safe_filename(name: str) -> str:
    stem, ext = Path(name).stem, Path(name).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.") or "video"
    return f"{stem[:80]}{ext}"


def _narration_files() -> list[dict]:
    out = []
    for d in NARRATION_SOURCES:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not f.is_file() or f.suffix.lower() not in (*AUDIO_EXTS, *VIDEO_EXTS):
                continue
            try:
                dur = round(_probe_cached(f).duration, 1)
            except Exception:  # noqa: BLE001 — file rusak tetap ditampilkan tanpa durasi
                dur = 0.0
            out.append({"path": _rel(f), "name": f.name, "duration": dur, "size_mb": round(f.stat().st_size / 1e6, 1),
                        "url": "/media/footage/" + quote(f.relative_to(FOOTAGE).as_posix())})
    return out


@app.get("/api/narration")
def list_narration() -> dict:
    """Rekaman narasi yang tersedia (footage/_narasi dan footage/_uji)."""
    return {"files": _narration_files()}


class TranscribeIn(BaseModel):
    narration_path: str
    engine: str = "api"
    brief: str = ""


class DraftTextsIn(BaseModel):
    texts: list[str]


def _narration_file(rel: str) -> Path:
    f = (ROOT / rel).resolve()
    if FOOTAGE.resolve() not in f.parents or not f.is_file():
        raise bad("File narasi tidak ditemukan (harus di dalam folder footage/).")
    return f


def _draft_out(draft: dict) -> dict:
    """Draf transkrip untuk web: frasa (waktu + teks), teks asli Whisper, dan tanda koreksi AI."""
    from autoreels.edl import Narration

    nar = Narration(**draft["narration"])
    fixed = {f["index"] for f in draft.get("ai_fixes", [])}
    original = draft.get("original") or []
    return {
        "id": draft["id"], "source": _rel(Path(draft["source"])) if Path(draft["source"]).is_absolute() else draft["source"],
        "reviewed": draft.get("reviewed", False), "duration": nar.duration,
        "kind": draft.get("kind", "narasi"), "speaker_clip": draft.get("speaker_clip"),
        "talk_full": draft.get("talk_full", False),
        "audio_url": f"/api/narration/drafts/{draft['id']}/audio",
        "phrases": [{"index": i, "start": p.start, "end": p.end, "text": p.text,
                     "original": original[i] if i < len(original) else p.text, "ai_fixed": i in fixed}
                    for i, p in enumerate(nar.phrases)],
    }


@app.post("/api/narration/transcribe")
def transcribe_narration(body: TranscribeIn) -> dict:
    """Transkrip + buang jeda/kata pengisi + koreksi AI → draf untuk diperiksa (±30–90 dtk di CPU)."""
    from autoreels.llm import CostTracker, LLMClient
    from autoreels.narration import create_draft

    src = _narration_file(body.narration_path)
    engine = _check_engine(body.engine)
    model = get_settings().models_for(engine)[0]
    try:
        draft = create_draft(src, llm=LLMClient(CostTracker(), log=lambda *_: None), model=model, brief=body.brief,
                             log=lambda *_: None)
    except (RuntimeError, FileNotFoundError) as e:
        raise bad(str(e)) from None
    return _draft_out(draft)


class TalkTranscribeIn(BaseModel):
    input_path: str
    talk_clip: str
    brief: str = ""
    engine: str = "api"
    talk_full: bool = False
    duration: int = 40


@app.post("/api/talk/transcribe")
def transcribe_talk(body: TalkTranscribeIn) -> dict:
    """Video bicara: transkrip + pilih kalimat (ringkas/utuh) + koreksi AI → draf untuk diperiksa sebelum render."""
    from autoreels.llm import CostTracker, LLMClient
    from autoreels.narration import create_talk_draft
    from autoreels.pipeline import TALK_MAX_SEC

    folder = _safe_footage_dir(body.input_path)
    video = folder / body.talk_clip
    if not video.is_file() or video.suffix.lower() not in VIDEO_EXTS:
        raise bad("Video pembicara tidak ditemukan di folder footage terpilih.")
    if _probe_cached(video).duration > TALK_MAX_SEC:
        raise bad(f"Video lebih dari {TALK_MAX_SEC // 60} menit. Pakai \"Cari cuplikan terbaik\" dulu.")
    engine = _check_engine(body.engine)
    model = get_settings().models_for(engine)[0]
    try:
        draft = create_talk_draft(video, speaker_clip=video.name, llm=LLMClient(CostTracker(), log=lambda *_: None),
                                  model=model, brief=body.brief, target=float(body.duration), full=body.talk_full,
                                  log=lambda *_: None)
    except (RuntimeError, FileNotFoundError) as e:
        raise bad(str(e)) from None
    return _draft_out(draft)


@app.get("/api/narration/drafts/{draft_id}")
def get_draft(draft_id: str) -> dict:
    from autoreels.narration import load_draft

    try:
        return _draft_out(load_draft(draft_id))
    except (ValueError, FileNotFoundError) as e:
        raise bad(str(e), 404) from None


@app.put("/api/narration/drafts/{draft_id}")
def save_draft(draft_id: str, body: DraftTextsIn) -> dict:
    from autoreels.narration import update_draft

    try:
        return _draft_out(update_draft(draft_id, body.texts))
    except FileNotFoundError as e:
        raise bad(str(e), 404) from None
    except ValueError as e:
        raise bad(str(e)) from None


@app.get("/api/narration/drafts/{draft_id}/audio")
def draft_audio(draft_id: str):
    from autoreels.narration import _draft_dir

    try:
        f = _draft_dir(draft_id) / "narasi.wav"
    except ValueError as e:
        raise bad(str(e), 404) from None
    if not f.exists():
        raise bad("Audio draf tidak ditemukan.", 404)
    return FileResponse(f, media_type="audio/wav")


@app.post("/api/narration/upload")
async def upload_narration(file: UploadFile = File(...)) -> dict:
    name = _safe_filename(file.filename or "narasi.m4a")
    if Path(name).suffix.lower() not in (*AUDIO_EXTS, *VIDEO_EXTS):
        raise bad(f"{file.filename}: format tidak didukung (pakai mp3, m4a, wav, atau video).")
    NARRATION_DIR.mkdir(parents=True, exist_ok=True)
    dest, n = NARRATION_DIR / name, 2
    while dest.exists():
        dest = NARRATION_DIR / f"{Path(name).stem}-{n}{Path(name).suffix}"
        n += 1
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out, length=4 * 1024 * 1024)
    return {"path": _rel(dest), "name": dest.name}


@app.post("/api/footage/upload")
async def upload_footage(pillar: str = Form(...), files: list[UploadFile] = File(..., alias="files[]")) -> dict:
    if pillar not in [*ce.PILLARS, *EXTRA_FOOTAGE_DIRS]:
        raise bad(f"Pilar tidak dikenal: {pillar}")
    target = FOOTAGE / pillar
    target.mkdir(parents=True, exist_ok=True)
    saved = []
    for up in files:
        name = _safe_filename(up.filename or "video.mp4")
        if Path(name).suffix not in VIDEO_EXTS:
            raise bad(f"{up.filename}: format tidak didukung (pakai .mp4 atau .mov).")
        dest, n = target / name, 2
        while dest.exists():
            dest = target / f"{Path(name).stem}-{n}{Path(name).suffix}"
            n += 1
        with open(dest, "wb") as out:
            shutil.copyfileobj(up.file, out, length=4 * 1024 * 1024)
        saved.append(dest.name)
    return {"folder": _rel(target), "files": saved}


# ======================================================================================
# Jobs
# ======================================================================================
class JobIn(BaseModel):
    input_path: str
    pillar: str
    brief: str = ""
    style: str
    duration: int = 20
    hook_text: str | None = None
    cta_text: str | None = None
    music_file: str | None = None
    voiceover: str = "none"   # none | rekam | gemini
    voice: str = "Puck"
    engine: str = "api"      # api | local (Ollama)
    clips: list[str] | None = None  # nama file yang dipilih (None = semua isi folder)
    blur_faces: bool = False        # samarkan wajah (pilihan pengguna, default mati)
    blur_plates: bool = False       # samarkan pelat nomor
    narration_path: str | None = None  # alur "narasi dulu": file narasi di footage/
    narration_draft: str | None = None  # draf transkrip yang sudah diperiksa (dari /api/narration/transcribe)
    talk_clip: str | None = None  # alur "video bicara": nama file video pembicara di folder footage terpilih
    purpose: str | None = None    # promosi | informasi | None (dipilih AI)
    no_music: bool = False        # tanpa musik latar
    logo: bool = True             # watermark (logo kecil di pojok video)
    talk_full: bool = False       # video bicara utuh: durasi ikut panjang ucapan (maks 3 menit)


def _check_engine(engine: str) -> str:
    if engine not in ENGINES:
        raise bad(f"Mesin AI tidak dikenal: {engine}")
    if engine == "local":
        from autoreels.llm import ollama_status

        st = ollama_status()
        if not st["running"] or st["missing"]:
            raise bad(f"Model lokal belum siap. {st['reason']}")
    return engine


@app.post("/api/jobs")
def create_job(body: JobIn) -> dict:
    from autoreels.pipeline import run_pipeline

    if body.pillar not in ce.PILLARS:
        raise bad(f"Pilar tidak dikenal: {body.pillar}")
    if body.style not in list_styles():
        raise bad(f"Style tidak dikenal: {body.style}")
    folder = _safe_footage_dir(body.input_path)
    available = [v.name for v in _videos_in(folder)]
    if not available:
        raise bad("Folder footage belum berisi video.")
    clips = None
    if body.clips is not None:
        clips = [c for c in dict.fromkeys(body.clips) if c in available]
        if not clips:
            raise bad("Pilih minimal 1 klip video.")
        if len(clips) == len(available) and not body.talk_clip:
            clips = None  # semua dipilih = perilaku lama (video bicara: tetap eksplisit, folder bisa bertambah)
    if not body.talk_clip:  # montase/narasi: tolak video panjang sejak awal (podcast/kuliah → Video bicara)
        from autoreels.pipeline import MONTAGE_MAX_CLIP_SEC

        names = clips if clips is not None else available
        long_ones = [n for n in names if _duration_or_zero(folder / n) > MONTAGE_MAX_CLIP_SEC]
        if long_ones:
            raise bad(f"{', '.join(long_ones)} lebih dari {MONTAGE_MAX_CLIP_SEC // 60} menit. Untuk podcast/kuliah pilih "
                      "alur Video bicara lalu Cari cuplikan; untuk b-roll potong dulu jadi klip pendek.")
    narration = _narration_file(body.narration_path) if body.narration_path else None
    talk = None
    if body.talk_clip:
        if body.talk_clip not in available:
            raise bad("Video pembicara tidak ada di folder footage terpilih.")
        talk = folder / body.talk_clip
        from autoreels.pipeline import TALK_MAX_SEC

        if _probe_cached(talk).duration > TALK_MAX_SEC:
            raise bad(f"Video pembicara lebih dari {TALK_MAX_SEC // 60} menit. Pakai \"Cari cuplikan terbaik\" "
                      "untuk memotongnya jadi beberapa cuplikan 1–3 menit.")
    if body.purpose not in (None, "promosi", "informasi"):
        raise bad("Tujuan video tidak dikenal.")
    if body.narration_draft:
        from autoreels.narration import load_draft

        try:
            load_draft(body.narration_draft)
        except (ValueError, FileNotFoundError) as e:
            raise bad(str(e)) from None
    music = None
    if body.music_file:
        music = (PATHS["music"] / body.music_file).resolve()
        if PATHS["music"].resolve() not in music.parents or not music.is_file():
            raise bad("File musik tidak ditemukan.")
    duration = min(90, max(8, int(body.duration)))
    brief = body.brief.strip() or ce.DEFAULT_BRIEF[body.pillar]
    if body.voiceover not in ("none", "rekam", "gemini"):
        raise bad("Pilihan voice over tidak dikenal.")
    voice = body.voice if body.voice in VOICES else "Puck"
    engine = _check_engine(body.engine)

    job_id = RUNNER.new_id(body.pillar)
    _save_request(job_id, body.model_copy(update={"input_path": _rel(folder), "clips": clips, "duration": duration,
                                                  "brief": brief, "voice": voice}))
    RUNNER.submit(job_id, lambda log: run_pipeline(
        input_path=folder, pillar=body.pillar, brief=brief, style_name=body.style, duration=duration,
        music_file=music, log=log, hook_text=body.hook_text, cta_text=body.cta_text, job_id=job_id,
        voiceover=body.voiceover, voice=voice, engine=engine, clips=clips,
        blur_faces=body.blur_faces, blur_plates=body.blur_plates, narration=narration,
        narration_draft=body.narration_draft, talk=talk, purpose=body.purpose, no_music=body.no_music, logo=body.logo,
        talk_full=body.talk_full,
    ), label=f"Buat Reel {body.pillar} dari {_rel(folder)}")
    return {"job_id": job_id}


# ======================================================================================
# Varian: satu proyek → beberapa Reel (durasi lain, tanpa CTA, ringkas/utuh) tanpa mengulang analisis
# ======================================================================================
VARIANT_KEYS = {"duration", "purpose", "talk_full"}
MAX_VARIANTS = 4


def _save_request(job_id: str, body: "JobIn") -> None:
    d = PATHS["work"] / job_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "request.json").write_text(body.model_dump_json(indent=1), encoding="utf-8")


def _job_flow(meta: dict) -> str:
    return meta.get("flow") or "video"


def _request_for(job_id: str) -> "JobIn":
    """Permintaan asli job (request.json); job lama: disusun ulang dari job.json (lagu & suara AI kembali bawaan)."""
    f = PATHS["work"] / job_id / "request.json"
    if f.exists():
        return JobIn.model_validate_json(f.read_text(encoding="utf-8"))
    meta = _job_meta(job_id)
    if not meta.get("input") or meta.get("source") == "import":
        raise bad("Varian tidak tersedia untuk video ini (video impor atau data job tidak lengkap).")
    folder = Path(meta["input"])
    folder = folder if folder.is_absolute() else ROOT / folder
    opts = meta.get("options") or {}
    flow = _job_flow(meta)
    narration = Path(meta["narration"]) if meta.get("narration") else None
    return JobIn(
        input_path=_rel(folder.resolve()), pillar=meta["pillar"], brief=meta.get("brief", ""), style=meta["style"],
        duration=int(round(float(meta.get("duration") or 20))), hook_text=meta.get("hook_text"),
        cta_text=meta.get("cta_text"), voiceover=meta.get("voiceover") or "none", engine=meta.get("engine") or "api",
        clips=meta.get("clips"), blur_faces=bool(opts.get("blur_faces")), blur_plates=bool(opts.get("blur_plates")),
        purpose=opts.get("purpose"), no_music=bool(opts.get("no_music")), logo=opts.get("watermark", True) is not False,
        talk_full=bool(opts.get("talk_full")), narration_draft=meta.get("narration_draft"),
        talk_clip=narration.name if flow == "bicara" and narration else None,
        narration_path=_rel(narration) if flow == "narasi" and narration else None,
    )


def _variant_info(job_id: str, meta: dict) -> dict:
    """Pilihan varian yang masuk akal untuk alur job ini (dipakai web)."""
    flow = _job_flow(meta)
    opts = meta.get("options") or {}
    return {"available": meta.get("source") != "import" and bool(meta.get("input")), "flow": flow,
            "duration": round(float(meta.get("duration") or 0)), "purpose": opts.get("purpose"),
            "talk_full": bool(opts.get("talk_full"))}


class VariantsIn(BaseModel):
    variants: list[dict[str, Any]]


@app.post("/api/jobs/{job_id}/variants")
def create_variants(job_id: str, body: VariantsIn) -> dict:
    """Buat beberapa Reel dari proyek yang sama. Analisis klip & deskripsi adegan diambil dari cache, jadi hanya
    Director/Critic yang dipanggil ulang. Tiap varian divalidasi seperti job baru."""
    _check_job_id(job_id)
    if not 1 <= len(body.variants) <= MAX_VARIANTS:
        raise bad(f"Pilih 1–{MAX_VARIANTS} varian.")
    base = _request_for(job_id)
    flow = _job_flow(_job_meta(job_id))
    job_ids = []
    for v in body.variants:
        extra = set(v) - VARIANT_KEYS
        if extra or not v:
            raise bad(f"Pilihan varian tidak dikenal: {', '.join(sorted(extra)) or '(kosong)'}.")
        if "duration" in v and flow != "video":
            raise bad("Durasi hanya bisa diubah untuk alur Video dulu (alur lain mengikuti panjang suara).")
        if "talk_full" in v and flow != "bicara":
            raise bad("Ringkas/utuh hanya untuk alur Video bicara.")
        job_ids.append(create_job(base.model_copy(update=v))["job_id"])
    return {"job_ids": job_ids}


# ======================================================================================
# Cari cuplikan (video panjang → beberapa Reel)
# ======================================================================================
HIGHLIGHT_TASKS: dict[str, dict[str, Any]] = {}
HIGHLIGHT_LOCK = threading.Lock()


class HighlightIn(BaseModel):
    video_path: str            # relatif root, di dalam footage/
    count: int = 0             # 0 = semua bagian yang layak (maks 20)
    brief: str = ""
    engine: str = "api"
    exclude: list[dict] = []   # "Cari ulang": cuplikan yang sudah ditampilkan {start, end, title} → cari bagian lain


class HighlightJobsIn(JobIn):
    ranks: list[int]           # nomor kandidat yang dibuat Reel
    musik_claude: bool = False  # hanya jalur Claude + Remotion: musik orisinal gubahan Claude
    agen: str = "claude"       # "claude" | "antigravity"


def _highlight_dir(task_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]{6,80}", task_id):
        raise bad("ID tugas cuplikan tidak valid.", 404)
    return PATHS["work"] / "_cuplikan" / task_id


def _footage_video(rel: str) -> Path:
    f = (ROOT / rel).resolve()
    if FOOTAGE.resolve() not in f.parents or not f.is_file() or f.suffix.lower() not in VIDEO_EXTS:
        raise bad("Video tidak ditemukan (harus file video di dalam folder footage/).")
    return f


def _highlight_state(task_id: str) -> dict:
    with HIGHLIGHT_LOCK:
        if task_id in HIGHLIGHT_TASKS:
            return dict(HIGHLIGHT_TASKS[task_id])
    f = _highlight_dir(task_id) / "task.json"
    if not f.exists():
        raise bad("Tugas cuplikan tidak ditemukan.", 404)
    return json.loads(f.read_text(encoding="utf-8"))


def _set_highlight(task_id: str, **kw) -> None:
    with HIGHLIGHT_LOCK:
        st = HIGHLIGHT_TASKS.setdefault(task_id, {"task_id": task_id})
        st.update(kw)
        snap = dict(st)
    d = _highlight_dir(task_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "task.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")


@app.post("/api/highlights")
def start_highlights(body: HighlightIn) -> dict:
    """Mulai mencari cuplikan di latar (transkripsi video panjang ±13 menit/jam di CPU, sekali lalu di-cache)."""
    from autoreels.highlights import slugify

    video = _footage_video(body.video_path)
    engine = _check_engine(body.engine)
    task_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{slugify(video.stem)[:40]}"
    _set_highlight(task_id, state="berjalan", percent=0, detail="menunggu giliran CPU…", video=_rel(video),
                   video_url="/media/footage/" + quote(video.relative_to(FOOTAGE).as_posix()), candidates=[],
                   error=None)

    def run() -> None:
        from autoreels.highlights import find_highlights, save_candidates
        from autoreels.joblock import job_lock
        from autoreels.llm import CostTracker, LLMClient

        import contextlib

        from autoreels.analyze.transcribe import is_transcribed

        try:
            # transkrip sudah tersimpan → hanya panggilan AI ringan, tidak perlu menunggu giliran CPU
            lock = (contextlib.nullcontext() if is_transcribed(video)
                    else job_lock(f"Cari cuplikan {video.name}", wait=True))
            with lock:
                settings = get_settings()
                cands = find_highlights(
                    video, llm=LLMClient(CostTracker(), log=lambda *_: None), model=settings.models_for(engine)[0],
                    brief=body.brief, exclude=[(float(x.get("start", 0)), float(x.get("end", 0)), str(x.get("title", "")))
                                               for x in body.exclude[:40]],
                    n=0 if body.count <= 0 else min(8, body.count), log=lambda *_: None,
                    on_progress=lambda f, d: _set_highlight(task_id, percent=round(100 * f), detail=d))
            save_candidates(_highlight_dir(task_id) / "candidates.json", video, cands)
            _set_highlight(task_id, state="selesai", percent=100, detail=f"{len(cands)} cuplikan ditemukan",
                           candidates=[{"rank": c.rank, "title": c.title, "reason": c.reason, "score": c.score,
                                        "start": c.start, "end": c.end, "duration": round(c.duration, 1),
                                        "hook": c.hook, "preview": c.preview} for c in cands])
        except Exception as e:  # noqa: BLE001 — dilaporkan ke web
            _set_highlight(task_id, state="gagal", error=str(e)[:400])

    threading.Thread(target=run, name=f"cuplikan-{task_id}", daemon=True).start()
    return {"task_id": task_id}


@app.get("/api/highlights/{task_id}")
def get_highlights(task_id: str) -> dict:
    return _highlight_state(task_id)


@app.post("/api/highlights/{task_id}/jobs")
def create_highlight_jobs(task_id: str, body: HighlightJobsIn) -> dict:
    """Potong cuplikan terpilih ke footage/<folder>/cuplikan/ lalu masukkan satu job video bicara per cuplikan."""
    from autoreels.highlights import cut_candidate, load_candidates

    f = _highlight_dir(task_id) / "candidates.json"
    if not f.exists():
        raise bad("Cuplikan belum ditemukan untuk tugas ini.", 404)
    video, cands = load_candidates(f)
    chosen = [c for c in cands if c.rank in set(body.ranks)]
    if not chosen:
        raise bad("Pilih minimal satu cuplikan.")
    out_dir = video.parent / "cuplikan"
    job_ids = []
    for c in chosen:
        clip = cut_candidate(video, c, out_dir)
        brief = (body.brief.strip() + f"\nCuplikan: {c.title}.").strip()
        job = body.model_copy(update={"input_path": _rel(out_dir), "clips": [clip.name], "talk_clip": clip.name,
                                      "brief": brief, "narration_path": None, "narration_draft": None})
        job_ids.append(create_job(JobIn(**job.model_dump(exclude={"ranks"})))["job_id"])
    return {"job_ids": job_ids, "folder": _rel(out_dir)}


@app.post("/api/highlights/{task_id}/animasi")
def create_highlight_animasi(task_id: str, body: HighlightJobsIn) -> dict:
    """Cuplikan terpilih → dipotong → disiapkan untuk Claude + Remotion (halaman Animasi), satu per satu di latar."""
    from autoreels import server_animasi as sa
    from autoreels.highlights import cut_candidate, load_candidates, slugify

    f = _highlight_dir(task_id) / "candidates.json"
    if not f.exists():
        raise bad("Cuplikan belum ditemukan untuk tugas ini.", 404)
    if body.pillar not in ce.PILLARS:
        raise bad(f"Pilar tidak dikenal: {body.pillar}")
    engine = _check_engine(body.engine)
    video, cands = load_candidates(f)
    chosen = [c for c in cands if c.rank in set(body.ranks)]
    if not chosen:
        raise bad("Pilih minimal satu cuplikan.")
    out_dir = video.parent / "cuplikan"
    stamp = time.strftime("%H%M")
    names = []
    for c in chosen:
        clip = cut_candidate(video, c, out_dir)
        nama = f"{slugify(c.title)[:22].strip('-') or 'cuplikan'}-{c.rank}-{stamp}"
        brief = (body.brief.strip() + f"\nCuplikan: {c.title}.").strip()
        fb = sa.FootageIn(nama=nama, input_path=_rel(out_dir), pilar=body.pillar, brief=brief, style=body.style,
                          duration=float(min(90, max(8, body.duration))), hook_text=body.hook_text,
                          cta_text=body.cta_text, music_file=body.music_file, no_music=body.no_music,
                          musik_claude=body.musik_claude and not body.no_music,
                          talk_clip=clip.name, talk_full=body.talk_full, engine=engine, auto_claude=True,
                          agen=sa._check_agen(body.agen))
        names.append(sa.queue_cuplikan(fb, out_dir / clip.name))
    return {"names": names, "folder": _rel(out_dir)}


@app.get("/api/jobs/active")
def active_jobs() -> dict:
    """Job yang sedang antri/berjalan di server ini (agar web bisa menyambung lagi setelah refresh/pindah halaman)."""
    out = []
    for job_id, entry in RUNNER.active():
        prog = _read_progress(job_id) or {}
        out.append({"job_id": job_id, "state": entry.get("state"), "kind": entry.get("kind", "create"),
                    "label": entry.get("label", ""), "percent": prog.get("percent", 0),
                    "step_label": prog.get("step_label", ""), "detail": prog.get("detail", "")})
    return {"jobs": out}


@app.get("/api/jobs/{job_id}/progress")
def job_progress(job_id: str) -> dict:
    _check_job_id(job_id)
    entry = RUNNER.get(job_id)
    data = _read_progress(job_id)
    if data is None and entry is None:
        raise bad("Job tidak ditemukan.", 404)
    data = data or {"job_id": job_id, "percent": 0, "step": "ingest", "step_label": "Menunggu antrean",
                    "step_index": 1, "steps_total": len(STEPS), "detail": "", "elapsed_sec": 0,
                    "state": "berjalan"}
    log_file = PATHS["work"] / job_id / "log.txt"
    if entry is not None:
        log = entry["log"][-300:]
        error = entry["error"]
        if entry["state"] == "gagal":
            data["state"] = "gagal"
    else:  # job dari sesi/terminal lain
        log = log_file.read_text(encoding="utf-8").splitlines()[-300:] if log_file.exists() else []
        err_file = PATHS["work"] / job_id / "error.txt"
        error = err_file.read_text(encoding="utf-8").splitlines()[0] if err_file.exists() else None
        f = _progress_file(job_id)
        if data.get("state") == "berjalan" and f.exists() and time.time() - f.stat().st_mtime > 900:
            data["state"] = "gagal"
            error = error or "Proses terhenti (server/terminal ditutup sebelum selesai)."
    data.update({"job_id": job_id, "error": error, "log": log})
    return data


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _job_meta(job_id: str) -> dict:
    """job.json tanpa bagian besar (analysis/descriptions)."""
    data = _read_json(PATHS["output"] / job_id / "job.json")
    data.pop("analysis", None)
    data.pop("descriptions", None)
    return data


def _edl_texts(out_dir: Path, meta: dict) -> dict:
    edl_file = out_dir / "edl.json"
    if edl_file.exists():
        from autoreels.edl import EDL

        edl = EDL.load(edl_file)
        vo = edl.voiceover
        return {
            "hook_text": edl.hook.overlay_text or "",
            "cta_text": edl.cta.text if edl.cta else "",
            "segments": [{"index": s.index, "role": s.role.value, "source_file": s.source_file,
                          "start": s.start, "end": s.end, "overlay_text": s.overlay_text} for s in edl.segments],
            "voiceover": {"mode": vo.mode.value, "voice": vo.voice, "offset_sec": vo.offset_sec,
                          "lines": [{"at_sec": ln.at_sec, "text": ln.text} for ln in vo.lines],
                          "has_recording": bool(vo.recording and (out_dir / vo.recording).exists())},
            # subtitle karaoke (narasi / video bicara): bisa dibetulkan lalu render ulang tanpa AI
            "subtitles": ([{"index": i, "start": p.start, "end": p.end, "text": p.text}
                           for i, p in enumerate(edl.narration.phrases)] if edl.narration is not None else []),
        }
    return {"hook_text": meta.get("hook_text") or "", "cta_text": meta.get("cta_text") or "", "segments": [],
            "voiceover": None}


def _checklist_from_report(report: str) -> list[dict]:
    """Cadangan untuk job lama tanpa result.json: baca tabel checklist di report.md."""
    items = []
    for m in re.finditer(r"^\| ([^|]+) \| ([^|]+) \| (✅|❌|⚠️) \| ([^|]*) \|$", report, re.M):
        group, name, mark, detail = (x.strip() for x in m.groups())
        items.append({"group": group, "name": name, "passed": mark == "✅", "required": mark != "⚠️",
                      "detail": detail})
    return items


@app.get("/api/jobs")
def list_jobs() -> dict:
    jobs = []
    reels = sorted(PATHS["output"].glob("*/reel.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)[:100]
    for reel in reels:
        out_dir = reel.parent
        meta = _job_meta(out_dir.name)
        result = _read_json(out_dir / "result.json")
        status_file = out_dir / "status.txt"
        status = status_file.read_text(encoding="utf-8").strip() if status_file.exists() else "perlu_tinjau"
        duration = (result.get("stats") or {}).get("total_duration") or meta.get("duration") or 0
        cover = out_dir / "cover.jpg"
        jobs.append({
            "job_id": out_dir.name, "created": str(meta.get("created", "")).split(" (")[0],
            "pillar": meta.get("pillar", out_dir.name.rsplit("-", 1)[-1]), "status": status,
            "hook_text": _edl_texts(out_dir, meta)["hook_text"], "duration": float(duration or 0),
            "cover_url": _media_url(cover) if cover.exists() else "",
            "source": meta.get("source", "autoreels"),
        })
    return {"jobs": jobs}


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str) -> dict:
    _check_job_id(job_id)
    out_dir = PATHS["output"] / job_id
    reel = out_dir / "reel.mp4"
    if not reel.exists():
        raise bad("Hasil job belum ada (mungkin masih diproses atau gagal).", 404)
    meta = _job_meta(job_id)
    result = _read_json(out_dir / "result.json")
    report = (out_dir / "report.md").read_text(encoding="utf-8") if (out_dir / "report.md").exists() else ""
    status_file = out_dir / "status.txt"
    stats = result.get("stats") or {}
    if not stats.get("total_duration"):
        stats["total_duration"] = round(probe(reel).duration, 2)
    cover = out_dir / "cover.jpg"
    caption = out_dir / "caption.txt"
    return {
        "job_id": job_id,
        "status": result.get("status") or (status_file.read_text(encoding="utf-8").strip()
                                           if status_file.exists() else "perlu_tinjau"),
        "pillar": meta.get("pillar", ""), "style": meta.get("style", ""), "brief": meta.get("brief", ""),
        "source": meta.get("source", "autoreels"),
        "engine": meta.get("engine", "api"), "models": meta.get("models") or {},
        "reel_url": _media_url(reel),
        "cover_url": _media_url(cover) if cover.exists() else "",
        "caption": caption.read_text(encoding="utf-8") if caption.exists() else "",
        "stats": {"total_duration": stats.get("total_duration") or 0, "segments": stats.get("segments") or 0,
                  "hook_duration": stats.get("hook_duration") or 0, "beat_accuracy": stats.get("beat_accuracy") or 0,
                  "cost_usd": stats.get("cost_usd") or 0, "process_sec": stats.get("process_sec") or 0},
        "checklist": result.get("checklist") or _checklist_from_report(report),
        "critic": result.get("critic") or _read_json(out_dir / "critic.json") or None,
        "visual": result.get("visual") or _read_json(out_dir / "visual_review.json") or None,
        "edl": _edl_texts(out_dir, meta),
        "variant": _variant_info(job_id, meta),
        "report_md": report,
    }


class RerenderIn(BaseModel):
    hook_text: str = ""
    cta_text: str = ""
    segment_texts: dict[str, str | None] = {}
    subtitle_texts: list[str] | None = None  # teks subtitle per frasa (waktu suara tetap)


@app.post("/api/jobs/{job_id}/rerender")
def rerender(job_id: str, body: RerenderIn) -> dict:
    _check_job_id(job_id)
    out_dir = PATHS["output"] / job_id
    entry = RUNNER.get(job_id)
    if entry and entry.get("state") in ("antri", "berjalan"):
        raise bad("Job ini sedang diproses. Tunggu sampai selesai.", 409)
    edl_file = out_dir / "edl.json"
    meta = _job_meta(job_id)
    if edl_file.exists():
        from autoreels.edl import EDL
        from autoreels.pipeline import render_from_edl

        edl = EDL.load(edl_file)
        if body.hook_text.strip():
            edl.hook.overlay_text = body.hook_text.strip()
        if body.cta_text.strip() and edl.cta:
            edl.cta.text = body.cta_text.strip()
        if body.subtitle_texts is not None and edl.narration is not None:
            from autoreels.narration import apply_texts

            if len(body.subtitle_texts) != len(edl.narration.phrases):
                raise bad("Jumlah baris subtitle tidak cocok dengan video ini. Muat ulang halaman.")
            edl.narration = apply_texts(edl.narration, body.subtitle_texts)
        for seg in edl.segments:
            if str(seg.index) in body.segment_texts:
                seg.overlay_text = (body.segment_texts[str(seg.index)] or "").strip() or None
        edl.save(edl_file)
        RUNNER.submit(job_id, lambda log: render_from_edl(edl_file, log=log), label="Render ulang (tanpa AI)")
    elif meta.get("source") == "import" and Path(meta.get("input", "")).is_file():
        from autoreels.importer import import_video

        RUNNER.submit(job_id, lambda log: import_video(
            video=Path(meta["input"]), pillar=meta.get("pillar", "profil"), brief=meta.get("brief", ""),
            hook_text=body.hook_text or None, cta_text=body.cta_text or None,
            add_logo=True, add_cta=bool(body.cta_text.strip() or meta.get("cta_text")), log=log, job_id=job_id,
        ), label="Impor ulang dengan teks baru", kind="import")
    else:
        raise bad("Job ini tidak bisa dirender ulang (EDL/video sumber tidak ditemukan).")
    return {"job_id": job_id}


# ======================================================================================
# Voice over: edit naskah, ganti suara AI, unggah/rekam suara sendiri → render ulang
# ======================================================================================
class VoiceLineIn(BaseModel):
    at_sec: float
    text: str


class VoiceOverIn(BaseModel):
    mode: str                     # none | rekam | gemini
    voice: str = "Puck"
    lines: list[VoiceLineIn] = []
    offset_sec: float | None = None


def _load_job_edl(job_id: str):
    from autoreels.edl import EDL

    _check_job_id(job_id)
    entry = RUNNER.get(job_id)
    if entry and entry.get("state") in ("antri", "berjalan"):
        raise bad("Job ini sedang diproses. Tunggu sampai selesai.", 409)
    edl_file = PATHS["output"] / job_id / "edl.json"
    if not edl_file.exists():
        raise bad("Voice over hanya untuk Reel buatan AutoReels (bukan video impor).")
    return edl_file, EDL.load(edl_file)


def _rerender(job_id: str, edl_file: Path, label: str) -> None:
    from autoreels.pipeline import render_from_edl

    RUNNER.submit(job_id, lambda log: render_from_edl(edl_file, log=log), label=label)


@app.post("/api/jobs/{job_id}/voiceover")
def save_voiceover(job_id: str, body: VoiceOverIn) -> dict:
    from autoreels.edl import VoiceLine, VoiceOverMode

    edl_file, edl = _load_job_edl(job_id)
    if body.mode not in ("none", "rekam", "gemini"):
        raise bad("Pilihan voice over tidak dikenal.")
    from autoreels.voiceover import clean_script, total_duration

    lines, _ = clean_script([VoiceLine(at_sec=ln.at_sec, text=ln.text) for ln in body.lines if ln.text.strip()],
                            total_duration(edl))
    if body.mode != "none" and not lines:
        raise bad("Naskah voice over masih kosong.")
    vo = edl.voiceover
    vo.mode = VoiceOverMode(body.mode)
    vo.voice = body.voice if body.voice in VOICES else vo.voice
    vo.lines = lines
    if body.offset_sec is not None:
        vo.offset_sec = max(-2.0, min(2.0, float(body.offset_sec)))
    edl.save(edl_file)
    label = {"gemini": "Buat suara AI & render ulang", "rekam": "Render ulang dengan rekaman",
             "none": "Render ulang tanpa voice over"}[body.mode]
    _rerender(job_id, edl_file, label)
    return {"job_id": job_id}


@app.post("/api/jobs/{job_id}/voiceover/recording")
async def upload_recording(job_id: str, file: UploadFile = File(...), offset_ms: int = Form(0),
                           lines_json: str = Form("")) -> dict:
    """Rekaman suara (direkam di browser sambil video diputar, atau file dari perekam HP).
    lines_json (opsional): naskah terbaru agar edit naskah + rekaman cukup satu kali render."""
    from autoreels.edl import VoiceLine, VoiceOverMode
    from autoreels.voiceover import clean_script, total_duration

    edl_file, edl = _load_job_edl(job_id)
    if lines_json.strip():
        try:
            raw_lines = [VoiceLine(at_sec=float(x["at_sec"]), text=str(x["text"]))
                         for x in json.loads(lines_json) if str(x.get("text", "")).strip()]
        except (ValueError, KeyError, TypeError):
            raise bad("Format naskah tidak valid.")
        edl.voiceover.lines, _ = clean_script(raw_lines, total_duration(edl))
    out_dir = edl_file.parent
    ext = (Path(file.filename or "").suffix or ".webm").lower()
    if ext not in {".webm", ".ogg", ".wav", ".mp3", ".m4a", ".aac", ".mp4", ".3gp", ".amr", ".opus", ".flac"}:
        raise bad("Format rekaman tidak didukung (pakai webm/ogg/wav/mp3/m4a).")
    raw = out_dir / f"voiceover_upload{ext}"
    with open(raw, "wb") as f:
        shutil.copyfileobj(file.file, f, length=4 * 1024 * 1024)
    wav = out_dir / "voiceover_rekaman.wav"
    try:
        run_ffmpeg(["-i", str(raw), "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(wav)])
    except Exception as e:  # noqa: BLE001
        raise bad(f"Rekaman tidak bisa dibaca: {str(e).splitlines()[0][:200]}")
    finally:
        raw.unlink(missing_ok=True)
    if probe(wav).duration < 0.5:
        raise bad("Rekaman terlalu pendek atau kosong.")
    vo = edl.voiceover
    vo.mode = VoiceOverMode.rekam
    vo.recording = wav.name
    vo.offset_sec = max(-2.0, min(2.0, -offset_ms / 1000))  # latensi mulai rekam → geser maju
    edl.save(edl_file)
    _rerender(job_id, edl_file, "Render ulang dengan rekaman suara")
    return {"job_id": job_id}


# ======================================================================================
# Impor video jadi (video-use / editor lain)
# ======================================================================================
@app.get("/api/import/candidates")
def import_candidates() -> dict:
    found: list[Path] = []
    if FOOTAGE.is_dir():
        found += [p for p in FOOTAGE.rglob("final.mp4") if p.parent.name == "edit"]
        impor = FOOTAGE / "impor"
        if impor.is_dir():
            found += _videos_in(impor)
    found = sorted(set(found), key=lambda p: p.stat().st_mtime, reverse=True)[:30]
    out = []
    for p in found:
        has_tr = any((d / n).exists() for d in (p.parent, p.parent / "edit") for n in ("master.srt", "takes_packed.md"))
        out.append({"path": _rel(p), "name": p.name if p.name != "final.mp4" else f"{p.parent.parent.name}/final.mp4",
                    "size_mb": round(p.stat().st_size / 1e6, 1),
                    "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(p.stat().st_mtime)),
                    "has_transcript": has_tr, "source": "video-use" if p.parent.name == "edit" else "unggahan"})
    return {"candidates": out}


class ImportIn(BaseModel):
    video_path: str
    pillar: str
    brief: str = ""
    hook_text: str | None = None
    cta_text: str | None = None
    add_logo: bool = True
    add_cta: bool = True
    engine: str = "api"


@app.post("/api/import")
def start_import(body: ImportIn) -> dict:
    from autoreels.importer import import_video

    if body.pillar not in ce.PILLARS:
        raise bad(f"Pilar tidak dikenal: {body.pillar}")
    raw = body.video_path.strip().strip('"')
    video = Path(raw) if Path(raw).is_absolute() else ROOT / raw
    if not video.is_file() or video.suffix.lower() not in VIDEO_EXTS:
        raise bad(f"Video tidak ditemukan atau format tidak didukung: {raw}")
    engine = _check_engine(body.engine)
    job_id = RUNNER.new_id(body.pillar)
    RUNNER.submit(job_id, lambda log: import_video(
        video=video, pillar=body.pillar, brief=body.brief, hook_text=body.hook_text, cta_text=body.cta_text,
        add_logo=body.add_logo, add_cta=body.add_cta, log=log, job_id=job_id, engine=engine,
    ), label=f"Impor {video.name}", kind="import")
    return {"job_id": job_id}


# ======================================================================================
# Config
# ======================================================================================
@app.get("/api/config/hooks")
def get_hooks() -> dict:
    return ce.load_hooks()


@app.put("/api/config/hooks")
def put_hooks(body: dict[str, list[dict[str, str]]]) -> dict:
    clean: dict[str, list[dict]] = {}
    for pillar in ce.PILLARS:
        items = []
        for h in body.get(pillar, []) or []:
            text = (h.get("text") or "").strip()
            htype = h.get("type") if h.get("type") in ce.HOOK_TYPES else "pertanyaan"
            if text:
                items.append({"type": htype, "text": text})
        clean[pillar] = items
    ce.save_hooks(clean)
    return {"ok": True}


class PillarSeoIn(BaseModel):
    hashtags: list[str] = []
    keywords: list[str] = []


@app.get("/api/config/pillars/{pillar}")
def get_pillar_seo(pillar: str) -> dict:
    if pillar not in ce.PILLARS:
        raise bad("Pilar tidak dikenal.", 404)
    data = ce.get_pillar(pillar)
    return {"hashtags": data.get("hashtags") or [], "keywords": data.get("keywords") or []}


@app.put("/api/config/pillars/{pillar}")
def put_pillar_seo(pillar: str, body: PillarSeoIn) -> dict:
    if pillar not in ce.PILLARS:
        raise bad("Pilar tidak dikenal.", 404)
    ce.set_pillar_list(pillar, "hashtags", ce.normalize_hashtags(" ".join(body.hashtags)))
    ce.set_pillar_list(pillar, "keywords", ce.normalize_keywords(", ".join(body.keywords)))
    return {"ok": True}


@app.get("/api/config/trends")
def get_trends() -> dict:
    items = ce.read_trend_items()
    return {"updated": ce.trend_updated(), **{k: items.get(title, []) for k, title in TREND_KEYS.items()}}


@app.put("/api/config/trends")
def put_trends(body: dict[str, Any]) -> dict:
    vals = {k: [str(x).strip() for x in (body.get(k) or []) if str(x).strip()] for k in TREND_KEYS}
    ce.write_trend_brief(**vals)
    return {"ok": True}


class PreferencesIn(BaseModel):
    text: str


@app.get("/api/config/preferences")
def get_preferences() -> dict:
    from autoreels import preferences as pf

    return pf.status()


@app.put("/api/config/preferences")
def put_preferences(body: PreferencesIn) -> dict:
    from autoreels import preferences as pf

    pf.write_text(body.text)
    return pf.status()


@app.post("/api/config/preferences/summarize")
def summarize_preferences() -> dict:
    from autoreels import preferences as pf

    try:
        pf.summarize(log=lambda *_: None)
    except ValueError as e:
        raise bad(str(e))
    except RuntimeError as e:  # API LLM gagal
        raise bad(f"Gagal merangkum (AI): {str(e)[:200]}", 502)
    return pf.status()


class BrandIn(BaseModel):
    price_per_day: str = "[HARGA]"
    default_cta: dict[str, str] = {}


@app.get("/api/config/brand")
def get_brand() -> dict:
    b = ce.load_brand_raw()
    return {"price_per_day": str(b.get("pricing", {}).get("rental_per_day", "[HARGA]")),
            "whatsapp": b.get("whatsapp", {}).get("display", ""),
            "instagram": b.get("instagram", {}).get("main", ""),
            "default_cta": b.get("default_cta", {})}


@app.put("/api/config/brand")
def put_brand(body: BrandIn) -> dict:
    current = ce.load_brand_raw()
    if body.price_per_day.strip() != str(current.get("pricing", {}).get("rental_per_day", "")):
        ce.set_brand_value("pricing", "rental_per_day", body.price_per_day.strip() or "[HARGA]")
    for pillar, text in body.default_cta.items():
        if pillar in ce.PILLARS and text.strip() and text.strip() != current.get("default_cta", {}).get(pillar):
            ce.set_brand_value("default_cta", pillar, text.strip())
    return {"ok": True}


class CaptionGuideIn(BaseModel):
    fields: dict[str, str] = {}
    examples: list[str] = []


@app.get("/api/config/caption-guide")
def get_caption_guide() -> dict:
    fields = ce.load_caption_guide()
    return {"fields": {k: fields.get(k, "") for k in CAPTION_FIELDS} | {k: v for k, v in fields.items()
                                                                          if k not in CAPTION_FIELDS},
            "examples": ce.load_caption_examples()}


@app.put("/api/config/caption-guide")
def put_caption_guide(body: CaptionGuideIn) -> dict:
    ce.write_caption_guide({k: v.strip() for k, v in body.fields.items()},
                           [e.strip() for e in body.examples if e.strip()][:3])
    return {"ok": True}


# ======================================================================================
# File statis: media & UI (UI dipasang terakhir agar /api tidak tertimpa)
# ======================================================================================
for _d in (PATHS["output"], PATHS["music"], THUMBS):
    _d.mkdir(parents=True, exist_ok=True)
app.mount("/media/output", StaticFiles(directory=PATHS["output"]), name="output")
app.mount("/media/music", StaticFiles(directory=PATHS["music"]), name="music")
app.mount("/media/thumbs", StaticFiles(directory=THUMBS), name="thumbs")
# Preview footage mentah di web (mendukung range request untuk seek). Dijaga PIN yang sama saat mode HP.
app.mount("/media/footage", StaticFiles(directory=FOOTAGE, check_dir=False), name="footage")
from autoreels.server_animasi import mark_stale as _mark_stale_animasi  # noqa: E402
from autoreels.server_animasi import router as _animasi_router  # noqa: E402

app.include_router(_animasi_router)  # Racik Animasi (Claude Code + Remotion), sebelum penyaji UI statis
app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")


def serve(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True, lan: bool = False) -> None:
    """lan=True: bisa dibuka dari HP di Wi-Fi yang sama (0.0.0.0) dengan PIN 6 digit acak."""
    import secrets
    import socket
    import webbrowser

    import sys

    import uvicorn

    if hasattr(sys.stdout, "reconfigure"):  # info IP & PIN harus langsung tampil, walau stdout bukan terminal
        sys.stdout.reconfigure(line_buffering=True)
    local_url = f"http://127.0.0.1:{port}"
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            print(f"AutoReels Studio sudah berjalan di {local_url} — membuka browser.")
            if lan:
                print("Untuk mode HP, tutup dulu server yang sedang berjalan, lalu jalankan ulang dengan --lan.")
            if open_browser:
                webbrowser.open(local_url)
            return
    if lan:
        host = "0.0.0.0"
        app.state.pin = f"{secrets.randbelow(10**6):06d}"
        ip = _lan_ip()
        line = "=" * 64
        print(line)
        print(" AutoReels Studio — MODE HP (Wi-Fi yang sama)")
        print(f"   Di HP, buka   : http://{ip}:{port}")
        print(f"   PIN           : {app.state.pin}   (berubah setiap server dijalankan)")
        print(f"   Di laptop ini : {local_url}  (tanpa PIN)")
        print(" Bila Windows bertanya soal firewall → izinkan untuk jaringan *Private*.")
        print(" Siapa pun di Wi-Fi ini butuh PIN untuk masuk. Ctrl+C untuk berhenti.")
        print(line)
    else:
        print(f"AutoReels Studio berjalan di {local_url}  (tutup jendela ini / Ctrl+C untuk berhenti)")
    stale = mark_stale_jobs()
    _mark_stale_animasi()
    if stale:
        print(f"{len(stale)} job tertinggal dari sesi sebelumnya ditandai terhenti: {', '.join(stale[:5])}")
    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(local_url)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")
