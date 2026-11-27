"""API Racik Animasi untuk Racik Studio (web): siapkan suara → periksa transkrip → Claude Code (headless) menulis
animasi → frame diam → render. Tanpa API LLM: kode, musik, dan caption dibuat Claude Code (`claude -p`, memakai login
langganan pengguna — ANTHROPIC_API_KEY sengaja dibuang dari environment proses anak).

Status per video: work/_animasi/<nama>/status.json  {langkah, state, detail, log[], job_id, mulai, selesai}
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from autoreels import animasi
from autoreels.config import PATHS, ROOT, load_pillars

router = APIRouter()
FOOTAGE = ROOT / "footage"
UPLOAD_DIR = FOOTAGE / "_animasi"  # rekaman suara yang diunggah dari web (tidak di-commit)
LOG_MAX = 300
_procs: dict[str, subprocess.Popen] = {}
_cancels: dict[str, threading.Event] = {}
_lock = threading.Lock()
AGENTS = ("claude", "antigravity")


def _check_agen(agen: str) -> str:
    val = (agen or "claude").strip().lower()
    if val not in AGENTS:
        raise _bad(f"Agen '{agen}' tidak dikenal (pilih: claude, antigravity).")
    return val


def _bad(msg: str, code: int = 400) -> HTTPException:
    return HTTPException(status_code=code, detail=msg)


def _name(nama: str) -> str:
    try:
        return animasi.check_name(nama)
    except ValueError as e:
        raise _bad(str(e)) from None


# ---------------------------------------------------------------------------------------------- status
def _status_file(nama: str) -> Path:
    return animasi.work_dir(nama) / "status.json"


def _status(nama: str) -> dict:
    f = _status_file(nama)
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"langkah": None, "state": None, "detail": "", "log": [], "job_id": None}


def _set(nama: str, **kw) -> dict:
    with _lock:
        st = _status(nama)
        log = kw.pop("log_add", None)
        st.update(kw)
        if log:
            st["log"] = (st.get("log") or []) + [f"{time.strftime('%H:%M:%S')}  {log}"]
            st["log"] = st["log"][-LOG_MAX:]
        f = _status_file(nama)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
        return st


def _busy(nama: str) -> bool:
    return _status(nama).get("state") == "berjalan"


def _start(nama: str, langkah: str, target, *args) -> None:
    if _busy(nama):
        raise _bad(f"'{nama}' masih memproses langkah {_status(nama).get('langkah')}. Tunggu atau hentikan dulu.", 409)
    _set(nama, langkah=langkah, state="berjalan", detail="mulai…", mulai=time.time(), selesai=None, persen=2,
         log_add=f"— {langkah} dimulai —")

    def run() -> None:
        try:
            target(nama, *args)
            if _status(nama).get("state") == "berjalan":
                _set(nama, state="selesai", detail="selesai", selesai=time.time(), persen=100,
                     log_add=f"— {langkah} selesai —")
        except Exception as e:  # noqa: BLE001 — dilaporkan ke web
            _set(nama, state="gagal", detail=str(e)[:600], selesai=time.time(), log_add=f"GAGAL: {str(e)[:300]}")

    threading.Thread(target=run, name=f"animasi-{langkah}-{nama}", daemon=True).start()


def mark_stale() -> None:
    """Saat server mulai: status 'berjalan' dari sesi lama → 'terhenti'."""
    root = PATHS["work"] / "_animasi"
    for f in root.glob("*/status.json") if root.exists() else []:
        try:
            st = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if st.get("state") == "berjalan":
            st.update(state="terhenti", detail="server dimatikan saat proses berjalan")
            f.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------------------------- ringkasan
def _code_file(nama: str) -> Path:
    return animasi.ANIM_DIR / "src" / "videos" / nama / "Video.tsx"


def _reel(job_id: str | None) -> dict | None:
    if not job_id:
        return None
    out = PATHS["output"] / job_id
    reel = out / "reel.mp4"
    if not reel.exists():
        return None
    status = (out / "status.txt").read_text(encoding="utf-8").strip() if (out / "status.txt").exists() else ""
    caption = (out / "caption.txt").read_text(encoding="utf-8") if (out / "caption.txt").exists() else ""
    v = int(reel.stat().st_mtime)
    return {"job_id": job_id, "status": status, "url": f"/media/output/{job_id}/reel.mp4?v={v}",
            "caption": caption, "report_url": f"/media/output/{job_id}/report.md?v={v}"}


def _latest_job(nama: str) -> str | None:
    st = _status(nama)
    if st.get("job_id"):
        return st["job_id"]
    # job dari CLI: cari job.json bersumber animasi dengan input work/_animasi/<nama>/anim.mp4
    want = str(animasi.work_dir(nama) / "anim.mp4")
    best = None
    for j in sorted(PATHS["output"].glob("*/job.json"), reverse=True):
        try:
            d = json.loads(j.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if d.get("source") == "animasi" and Path(d.get("input", "")).resolve() == Path(want).resolve():
            best = j.parent.name
            break
    return best


def _data_or_draft(nama: str) -> dict:
    """data.json; selama suara masih disiapkan (belum ada) → data sementara dari status (pilar/brief)."""
    f = animasi.PUBLIC / nama / "data.json"
    if f.exists():
        return animasi.load_data(nama)
    st = _status(nama)
    if not st.get("langkah"):
        raise _bad(f"Video animasi '{nama}' tidak ditemukan.", 404)
    return {"pilar": st.get("pilar"), "brief": st.get("brief", ""), "durasi": 0, "kata": [], "frasa": []}


def _summary(nama: str) -> dict:
    data = _data_or_draft(nama)
    st = _status(nama)
    wdir = animasi.work_dir(nama)
    sheet = wdir / "lembar_stills.jpg"
    return {
        "nama": nama, "pilar": data.get("pilar"), "brief": data.get("brief", ""), "durasi": data.get("durasi"),
        "punya_kode": _code_file(nama).exists(), "punya_musik": (wdir / "musik.json").exists(),
        "punya_caption": (wdir / "caption.json").exists(),
        "langkah": st.get("langkah"), "state": st.get("state"), "detail": st.get("detail", ""),
        "agen": st.get("agen") or "claude",
        "lembar_url": f"/api/animasi/{nama}/lembar?v={int(sheet.stat().st_mtime)}" if sheet.exists() else None,
        "hasil": _reel(_latest_job(nama)),
        "diubah": int((wdir / "status.json").stat().st_mtime) if (wdir / "status.json").exists()
        else int((animasi.PUBLIC / nama / "data.json").stat().st_mtime),
        "mode": data.get("mode") or "narasi",
        "persen": st.get("persen"), "mulai": st.get("mulai"), "selesai_pada": st.get("selesai"),
        "siap": bool(data.get("kata")) or data.get("mode") == "footage",
        "gaya": data.get("gaya") or animasi.GAYA_DEFAULT,
        "hasil_gaya": st.get("hasil_gaya"),
        "dimensi": data.get("dimensi") or ("3d" if nama.endswith("-3d") else "2d"),
    }


@router.get("/api/animasi")
def list_animasi(mode: str = "animasi") -> dict:
    """mode=animasi (default): video animasi penuh saja (halaman Animasi). mode=footage: video Claude + Remotion dari
    footage (dipantau di Buat video, tidak tampil di halaman Animasi)."""
    items = []
    names = {f.parent.name for f in animasi.PUBLIC.glob("*/data.json")}
    work = PATHS["work"] / "_animasi"
    names |= {f.parent.name for f in work.glob("*/status.json")} if work.exists() else set()  # sedang disiapkan
    for nama in sorted(names):
        if nama.startswith("_") or not animasi.NAME_RE.match(nama):
            continue
        try:
            item = _summary(nama)
        except Exception:  # noqa: BLE001 — data rusak: lewati
            continue
        if (item["mode"] == "footage") == (mode == "footage"):
            items.append(item)
    items.sort(key=lambda x: x["diubah"], reverse=True)
    sources = []
    for d in [FOOTAGE / "_uji", FOOTAGE / "_narasi", UPLOAD_DIR, FOOTAGE / "umum"]:
        if d.exists():
            for p in sorted(d.iterdir()):
                if p.suffix.lower() in {".m4a", ".mp3", ".wav", ".ogg", ".aac", ".mp4", ".mov", ".mkv"}:
                    sources.append(p.relative_to(FOOTAGE).as_posix())
    styles = [{"id": gid, "nama": g["nama"], "deskripsi": g["deskripsi"],
               "warna": [g["warna"][k] for k in ("krem", "hijau", "ungu", "merah", "kuning")]}
              for gid, g in animasi.list_styles().items()]
    return {"videos": items, "sources": sources, "pillars": list(load_pillars().keys()), "styles": styles}


@router.get("/api/animasi/{nama}")
def get_animasi(nama: str) -> dict:
    nama = _name(nama)
    data = _data_or_draft(nama)
    st = _status(nama)
    stills_dir = animasi.work_dir(nama) / "stills"
    stills = [f"/api/animasi/{nama}/still/{p.name}?v={int(p.stat().st_mtime)}"
              for p in sorted(stills_dir.glob("*.jpg"))] if stills_dir.exists() else []
    gdir = animasi.work_dir(nama) / "gaya"
    previews = {p.stem: f"/api/animasi/{nama}/gaya/{p.name}?v={int(p.stat().st_mtime)}"
                for p in sorted(gdir.glob("*.jpg"))} if gdir.exists() else {}
    return {**_summary(nama), "kata": data["kata"], "frasa": data["frasa"], "log": st.get("log", [])[-120:],
            "stills": stills, "biaya": st.get("biaya"), "pratinjau_gaya": previews}


@router.get("/api/animasi/{nama}/lembar")
def sheet(nama: str) -> FileResponse:
    f = animasi.work_dir(_name(nama)) / "lembar_stills.jpg"
    if not f.exists():
        raise _bad("Lembar frame belum ada.", 404)
    return FileResponse(f)


@router.get("/api/animasi/{nama}/still/{file}")
def still(nama: str, file: str) -> FileResponse:
    f = animasi.work_dir(_name(nama)) / "stills" / Path(file).name
    if not f.exists():
        raise _bad("Frame tidak ada.", 404)
    return FileResponse(f)


@router.get("/api/animasi/{nama}/gaya/{file}")
def style_preview(nama: str, file: str) -> FileResponse:
    f = animasi.work_dir(_name(nama)) / "gaya" / Path(file).name
    if not f.exists():
        raise _bad("Pratinjau gaya belum ada.", 404)
    return FileResponse(f)


@router.get("/api/animasi/{nama}/audio")
def narration_audio(nama: str) -> FileResponse:
    f = animasi.PUBLIC / _name(nama) / "narasi.wav"
    if not f.exists():
        raise _bad("Narasi belum ada.", 404)
    return FileResponse(f, media_type="audio/wav")


# ---------------------------------------------------------------------------------------------- 1. siapkan
def _prepare(nama: str, src: Path, pilar: str, brief: str, ranges, gaya: str = animasi.GAYA_DEFAULT,
             dimensi: str = "2d") -> None:
    from autoreels.joblock import job_lock

    with job_lock(f"Animasi: siapkan {nama}", wait=True,
                  on_wait=lambda h: _set(nama, detail=f"menunggu giliran CPU ({h.get('label', '')})")):
        _set(nama, detail="transkripsi suara (CPU)…", log_add=f"sumber: {src.name}")
        animasi.prepare(voice=src, name=nama, pillar=pilar, brief=brief, ranges=ranges, gaya=gaya,
                        dimensi=dimensi, log=lambda m: _set(nama, log_add=str(m).strip()))


@router.post("/api/animasi")
async def create_animasi(nama: str = Form(...), pilar: str = Form(...), brief: str = Form(""),
                         sumber: str = Form(""), rentang: str = Form(""), gaya: str = Form("racik-flat"),
                         dimensi: str = Form("2d"),
                         file: UploadFile | None = File(None)) -> dict:
    nama = _name(nama)
    if pilar not in load_pillars():
        raise _bad(f"Pilar '{pilar}' tidak dikenal.")
    if gaya not in animasi.list_styles():
        raise _bad(f"Gaya '{gaya}' tidak dikenal.")
    if dimensi not in ("2d", "3d"):
        raise _bad("Dimensi harus 2d atau 3d.")
    if (animasi.PUBLIC / nama / "data.json").exists() or _busy(nama):
        raise _bad(f"Nama '{nama}' sudah dipakai. Pilih nama lain.", 409)
    if file is not None and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in {".m4a", ".mp3", ".wav", ".ogg", ".aac", ".mp4", ".mov", ".mkv", ".webm"}:
            raise _bad("Format suara tidak didukung (m4a, mp3, wav, ogg, aac, atau video).")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        src = UPLOAD_DIR / f"{nama}{ext}"
        with src.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    elif sumber:
        src = (FOOTAGE / sumber).resolve()
        if FOOTAGE.resolve() not in src.parents or not src.is_file():
            raise _bad("File sumber tidak ditemukan di folder footage.")
    else:
        raise _bad("Unggah rekaman suara atau pilih file sumber.")
    ranges = None
    if rentang.strip():
        try:
            ranges = [(float(a), float(b) if b.strip() else None)
                      for a, _, b in (part.strip().partition("-") for part in rentang.split(","))]
        except ValueError:
            raise _bad("Format rentang: '120-180' atau '2615.8-2621.9,2518.7-2547' (detik).") from None
    _set(nama, pilar=pilar, brief=brief)  # agar halaman detail bisa tampil sebelum data.json jadi
    _start(nama, "siapkan", _prepare, src, pilar, brief, ranges, gaya, dimensi)
    return {"nama": nama}


class FootageIn(BaseModel):
    nama: str
    input_path: str
    pilar: str
    brief: str = ""
    style: str = "rental_energik"
    duration: float = 20.0
    clips: list[str] | None = None
    hook_text: str | None = None
    cta_text: str | None = None
    music_file: str | None = None
    no_music: bool = False
    musik_claude: bool = False  # Claude menggubah musik & efek suara orisinal (musik.json) alih-alih lagu library
    narration_draft: str | None = None  # alur narasi dulu / video bicara: transkrip yang sudah diperiksa
    talk_clip: str | None = None        # video bicara: file pembicara di folder footage
    talk_full: bool = False             # cuplikan: utuh (tanpa diringkas AI)
    engine: str = "api"                 # mesin AI untuk transkrip otomatis cuplikan
    auto_claude: bool = False           # wizard Buat video: langsung jalankan Claude Code setelah footage siap
    agen: str = "claude"                # penyusun Remotion: "claude" | "antigravity"


_claude_gate = threading.Semaphore(1)  # satu Claude Code berjalan sekaligus (cuplikan beruntun diantre)


def _auto_claude(nama: str, agen: str = "claude") -> None:
    """Lanjut otomatis dari penyiapan footage ke agen Remotion (wizard Buat video), satu per satu."""
    label = "Antigravity" if agen == "antigravity" else "Claude"
    _set(nama, langkah="claude", agen=agen, detail=f"menunggu giliran {label}…",
         log_add=f"— footage siap, {label} menyusul —")
    with _claude_gate:
        if _status(nama).get("state") != "berjalan":  # dihentikan saat menunggu
            return
        _run_claude(nama, "", agen)


def _prepare_footage(nama: str, body: FootageIn, src: Path) -> None:
    from autoreels import footage_remotion
    from autoreels.joblock import job_lock

    with job_lock(f"Footage Remotion: siapkan {nama}", wait=True,
                  on_wait=lambda h: _set(nama, detail=f"menunggu giliran CPU ({h.get('label', '')})")):
        _set(nama, detail="analisis footage (adegan, kualitas, beat)…", persen=8, log_add=f"sumber: {src.name}")
        music = (PATHS["music"] / body.music_file).resolve() if body.music_file else None
        footage_remotion.prepare(nama=nama, input_path=src, pillar=body.pilar, brief=body.brief,
                                 style_name=body.style, duration=body.duration, clips=body.clips,
                                 hook_text=body.hook_text, cta_text=body.cta_text, music_file=music,
                                 narration_draft=body.narration_draft, talk_clip=body.talk_clip,
                                 no_music=body.no_music, musik_claude=body.musik_claude, log=lambda m: _set(nama, log_add=str(m).strip()))
    if body.auto_claude:  # di luar kunci CPU: Claude berjalan belasan menit, jangan menahan job lain
        _auto_claude(nama, _check_agen(body.agen))


def _prepare_cuplikan(nama: str, body: FootageIn, src: Path) -> None:
    """Cuplikan video bicara: transkrip + pilih kalimat + koreksi AI otomatis (tanpa tinjau manual, seperti jalur
    cuplikan biasa) → footage disiapkan. Satu kunci CPU agar cuplikan diproses berurutan."""
    from autoreels import footage_remotion
    from autoreels.config import get_settings
    from autoreels.joblock import job_lock
    from autoreels.llm import CostTracker, LLMClient
    from autoreels.narration import _draft_dir, _save_draft, create_talk_draft

    with job_lock(f"Cuplikan Remotion: siapkan {nama}", wait=True,
                  on_wait=lambda h: _set(nama, detail=f"menunggu giliran CPU ({h.get('label', '')})")):
        log = lambda m: _set(nama, log_add=str(m).strip())  # noqa: E731
        _set(nama, detail="transkrip cuplikan (CPU) + pilih kalimat…", log_add=f"cuplikan: {src.name}")
        model = get_settings().models_for(body.engine)[0]
        draft = create_talk_draft(src, speaker_clip=src.name, llm=LLMClient(CostTracker(), log=lambda *_: None),
                                  model=model, brief=body.brief, target=body.duration, full=body.talk_full, log=log)
        draft["reviewed"] = True  # jalur cuplikan otomatis: transkrip belum ditinjau manusia
        _save_draft(_draft_dir(draft["id"]), draft)
        _set(nama, detail="analisis footage (adegan, kualitas)…")
        music = (PATHS["music"] / body.music_file).resolve() if body.music_file else None
        footage_remotion.prepare(nama=nama, input_path=src.parent, pillar=body.pilar, brief=body.brief,
                                 style_name=body.style, duration=body.duration, clips=[src.name],
                                 hook_text=body.hook_text, cta_text=body.cta_text, music_file=music,
                                 narration_draft=draft["id"], talk_clip=src.name, no_music=body.no_music,
                                 musik_claude=body.musik_claude, log=log)
    if body.auto_claude:
        _auto_claude(nama, _check_agen(body.agen))


def queue_cuplikan(body: FootageIn, src: Path) -> str:
    """Dipakai server.py (cuplikan terbaik → Claude + Remotion): validasi lalu antrekan penyiapan di latar."""
    nama = _name(body.nama)
    if body.pilar not in load_pillars():
        raise _bad(f"Pilar '{body.pilar}' tidak dikenal.")
    if (animasi.PUBLIC / nama / "data.json").exists() or _busy(nama):
        raise _bad(f"Nama '{nama}' sudah dipakai.", 409)
    _set(nama, pilar=body.pilar, brief=body.brief)
    _start(nama, "siapkan", _prepare_cuplikan, body, src)
    return nama


TOTAL_MAX_SEC = 1800  # total footage yang boleh dianalisis & dibaca Claude per video (30 menit)


def _check_lengths(src: Path, body: FootageIn) -> None:
    """Tolak video panjang sejak awal (sama dengan jalur Director): podcast/kuliah jam-jaman → Video bicara + Cari cuplikan.
    Claude tidak boleh disuruh membaca ratusan adegan."""
    from autoreels.ingest import list_inputs
    from autoreels.media import probe
    from autoreels.pipeline import MONTAGE_MAX_CLIP_SEC, TALK_MAX_SEC

    try:
        files = list_inputs(src, body.clips)
    except (FileNotFoundError, ValueError) as e:
        raise _bad(str(e)) from None
    total = 0.0
    for f in files:
        try:
            d = float(probe(f).duration)
        except Exception:  # noqa: BLE001 — file tak terbaca dilaporkan jelas saat ingest
            continue
        total += d
        limit = TALK_MAX_SEC if f.name == body.talk_clip else MONTAGE_MAX_CLIP_SEC
        if d > limit:
            raise _bad(f"{f.name} berdurasi {d / 60:.0f} menit (maks {limit // 60} menit untuk satu klip). Untuk video panjang "
                       "(podcast, kuliah) pilih alur Video bicara lalu \"Cari cuplikan terbaik\"; untuk b-roll potong "
                       "jadi klip pendek.")
    if total > TOTAL_MAX_SEC:
        raise _bad(f"Total footage {total / 60:.0f} menit terlalu banyak (maks {TOTAL_MAX_SEC // 60} menit). "
                   "Pilih klip yang dipakai saja.")


@router.post("/api/animasi/footage")
def create_footage(body: FootageIn) -> dict:
    """Buat video dari footage mentah dengan Claude + Remotion (mode Buat video). Setelah siap, jalankan Claude
    dari halaman Animasi (`/claude`) — Ruang Kerja menampilkan kerjanya."""
    nama = _name(body.nama)
    if body.pilar not in load_pillars():
        raise _bad(f"Pilar '{body.pilar}' tidak dikenal.")
    from autoreels.config import list_styles as preset_styles

    if body.style not in preset_styles():
        raise _bad(f"Style preset '{body.style}' tidak dikenal.")
    if not 5 <= body.duration <= 200:
        raise _bad("Durasi harus 5–200 detik.")
    if body.narration_draft:
        from autoreels.narration import load_draft

        try:
            if not load_draft(body.narration_draft).get("reviewed"):
                raise _bad("Transkrip belum diperiksa. Simpan transkrip dulu.")
        except (ValueError, FileNotFoundError) as e:
            raise _bad(str(e)) from None
    elif body.talk_clip:
        raise _bad("Video bicara butuh transkrip yang sudah diperiksa.")
    src = (ROOT / body.input_path).resolve()
    if FOOTAGE.resolve() not in (src, *src.parents) or not src.exists():
        raise _bad("Folder footage tidak ditemukan di folder footage/.")
    _check_lengths(src, body)
    if (animasi.PUBLIC / nama / "data.json").exists() or _busy(nama):
        raise _bad(f"Nama '{nama}' sudah dipakai. Pilih nama lain.", 409)
    _set(nama, pilar=body.pilar, brief=body.brief)
    _start(nama, "siapkan", _prepare_footage, body, src)
    return {"nama": nama}


# ---------------------------------------------------------------------------------------------- 2. transkrip
class TranscriptIn(BaseModel):
    kata: list[str]


@router.put("/api/animasi/{nama}/transkrip")
def save_transcript(nama: str, body: TranscriptIn) -> dict:
    """Betulkan salah dengar: teks per kata (jumlah & urutan tetap, waktu tidak berubah)."""
    nama = _name(nama)
    if _busy(nama):
        raise _bad("Sedang diproses — tunggu selesai.", 409)
    data = animasi.load_data(nama)
    if len(body.kata) != len(data["kata"]):
        raise _bad(f"Jumlah kata harus {len(data['kata'])} (waktu per kata tidak boleh berubah).")
    for w, txt in zip(data["kata"], body.kata):
        txt = " ".join(txt.split())
        if not txt:
            raise _bad("Kata tidak boleh kosong.")
        w["text"] = txt
    for f in data["frasa"]:
        f["text"] = " ".join(w["text"] for w in data["kata"] if f["start"] <= (w["start"] + w["end"]) / 2 < f["end"])
    animasi.save_data(nama, data)
    _set(nama, log_add="transkrip diperbarui dari web")
    return {"ok": True}


# ---------------------------------------------------------------------------------------------- gaya
class StyleIn(BaseModel):
    gaya: str


@router.put("/api/animasi/{nama}/gaya")
def set_style(nama: str, body: StyleIn) -> dict:
    """Ganti gaya visual video (kode animasi tetap); berlaku pada render berikutnya."""
    nama = _name(nama)
    if _busy(nama):
        raise _bad("Sedang diproses — tunggu selesai.", 409)
    try:
        animasi.set_style(nama, body.gaya)
    except ValueError as e:
        raise _bad(str(e)) from None
    _set(nama, log_add=f"gaya diganti → {body.gaya}")
    return {"gaya": body.gaya}


def _previews(nama: str) -> None:
    _set(nama, detail="merender pratinjau semua gaya…")
    animasi.style_previews(nama, log=lambda m: _set(nama, log_add=str(m).strip()))


@router.post("/api/animasi/{nama}/pratinjau-gaya")
def run_previews(nama: str) -> dict:
    nama = _name(nama)
    _need_code(nama)
    _start(nama, "pratinjau", _previews)
    return {"ok": True}


# ---------------------------------------------------------------------------------------------- 3. Claude Code
def _claude_exe() -> str:
    exe = shutil.which("claude") or shutil.which("claude.exe")
    if not exe:
        home = Path.home() / ".local" / "bin" / "claude.exe"
        exe = str(home) if home.exists() else None
    if not exe:
        raise RuntimeError("Claude Code (perintah `claude`) tidak ditemukan. Pasang Claude Code lalu login sekali.")
    return exe


PROMPT = """Jalankan skill racik-animasi (.claude/skills/racik-animasi/SKILL.md — baca dulu) untuk video '{nama}'.
Kondisi: `autoreels animasi prepare` SUDAH dijalankan dan transkrip SUDAH diperiksa pengguna di web
(animasi/public/{nama}/data.json). Pengguna tidak bisa menjawab pertanyaan: jangan bertanya, putuskan sendiri.
{mode}
Wajib:
- Hanya ubah file milik video ini: animasi/src/videos/{nama}/, baris '{nama}' di animasi/src/videos/index.ts,
  work/_animasi/{nama}/musik.json, work/_animasi/{nama}/caption.json; elemen baru yang dipakai ulang boleh masuk
  animasi/src/kit/ (jangan merusak video lain).
- Cek tipe: `.venv/Scripts/autoreels animasi cek`. Cek tampilan: `.venv/Scripts/autoreels animasi stills -n {nama}`
  lalu lihat work/_animasi/{nama}/lembar_stills.jpg; perbaiki sampai bersih (maks 3 putaran).
- Gaya visual video ini: '{gaya}' (animasi/src/kit/gaya.json). Kode harus tetap bagus di SEMUA gaya: pakai token kit
  (WARNA, TINTA, tepi(), bayang(), garisSvg(), warnaObjek()), jangan menulis warna hex/garis tinta mati.
- Jangan sekadar menyusun komponen kit: buat minimal SATU elemen visual khas video ini (komponen SVG baru di folder
  videonya, mis. objek/adegan yang hanya ada di cerita ini) supaya tiap video punya ciri sendiri.
- {dimensi}
- Musik orisinal: tulis partitur work/_animasi/{nama}/musik.json (format di autoreels/musik_sintesis.py).
- Caption: work/_animasi/{nama}/caption.json.
- Terakhir render: `.venv/Scripts/autoreels animasi render -n {nama}` dan laporkan status checklist singkat.
- Jangan memanggil API LLM lain (Gemini/Groq/OpenAI) dan jangan membuka internet.
Instruksi pengguna: {instruksi}"""


PROMPT_FOOTAGE = """Jalankan skill racik-footage (.claude/skills/racik-footage/SKILL.md — baca dulu) untuk video '{nama}'.
Kondisi: `autoreels animasi footage` SUDAH dijalankan: footage dinormalisasi ke animasi/public/{nama}/klip/, data +
tabel adegan di animasi/public/{nama}/data.json, lembar kontak di work/_animasi/{nama}/lembar_kontak_*.jpg,
daftar adegan di work/_animasi/{nama}/adegan.txt. Pengguna tidak bisa menjawab pertanyaan: jangan bertanya, putuskan sendiri.
{mode}
Alur video ini: {alur}
Wajib:
- Hanya ubah file milik video ini: animasi/src/videos/{nama}/, baris '{nama}' di animasi/src/videos/index.ts,
  work/_animasi/{nama}/musik.json, work/_animasi/{nama}/caption.json; elemen yang dipakai ulang boleh masuk animasi/src/kit/
  (jangan merusak video lain).
- Cek tipe: `.venv/Scripts/autoreels animasi cek`. Cek tampilan: `.venv/Scripts/autoreels animasi stills -n {nama}`
  lalu lihat work/_animasi/{nama}/lembar_stills.jpg; perbaiki sampai bersih (maks 3 putaran).
- Style preset footage: '{preset}' (data.json → preset: tempo potongan, transisi, warna, font, mood musik). Ikuti angkanya.
- Musik: bila data.tanpa_musik true → TANPA musik sama sekali (jangan tulis musik.json). Bila data.musik_orisinal true → WAJIB gubah musik + efek suara orisinal (bagian 5 skill). Selain itu pakai musik.wav hasil prepare (beat di data.beats); musik.json orisinal hanya bila lagu itu jelas tidak cocok.
- Caption: work/_animasi/{nama}/caption.json.
- Terakhir render: `.venv/Scripts/autoreels animasi render -n {nama}` dan laporkan status checklist singkat.
- Jangan memanggil API LLM lain (Gemini/Groq/OpenAI) dan jangan membuka internet.
Instruksi pengguna: {instruksi}"""


def _tool_line(block: dict) -> str:
    name = block.get("name", "")
    inp = block.get("input") or {}
    if name in ("Write", "Edit", "Read"):
        verb = {"Write": "menulis", "Edit": "mengubah", "Read": "membaca"}[name]
        return f"{verb} {Path(str(inp.get('file_path', ''))).name}"
    if name == "Bash":
        return f"menjalankan: {str(inp.get('command', ''))[:120]}"
    return name


EVENT_CAP = 6000  # batas karakter isi kode/teks per event Ruang Kerja


def _events_file(nama: str) -> Path:
    return animasi.work_dir(nama) / "events.jsonl"


def _reset_events(nama: str) -> None:
    f = _events_file(nama)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("", encoding="utf-8")


def _emit(nama: str, t0: float, kind: str, **kw) -> None:
    """Tambah satu event Ruang Kerja (dibaca SSE & replay). Hanya aksi nyata Claude, bukan simulasi."""
    ev = {"t": round(time.time() - t0, 2), "k": kind, **kw}
    with _lock, _events_file(nama).open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def _read_events(nama: str, since: int = 0) -> list[dict]:
    f = _events_file(nama)
    if not f.exists():
        return []
    out = []
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines()):
        if i < since:
            continue
        try:
            out.append({"i": i, **json.loads(line)})
        except json.JSONDecodeError:
            pass
    return out


# Penanda adegan di Video.tsx (konvensi skill racik-animasi): // === ADEGAN 3: judul ===
SCENE_RE = re.compile(r"={2,}\s*ADEGAN\s+(\d+)\s*[:\-–]?\s*(.*?)\s*={2,}", re.IGNORECASE)


def _scene_markers(code: str) -> list[tuple[int, int, str]]:
    """[(posisi, nomor, judul)] berurut menurut posisi di kode."""
    return [(m.start(), int(m.group(1)), m.group(2).strip()[:40]) for m in SCENE_RE.finditer(code)]


def _scene_info(nama: str, inp: dict, name: str) -> dict:
    """Adegan yang disentuh edit ini + daftar adegan di kode. Edit: old_string masih ada di file sebelum diterapkan,
    jadi posisinya dicari di sana (tanpa menunggu); penanda di teks baru juga dihitung."""
    try:
        code = _code_file(nama).read_text(encoding="utf-8") if _code_file(nama).exists() else ""
    except OSError:
        code = ""
    if name == "Write":
        code = str(inp.get("content", ""))
    marks = _scene_markers(code)
    scene = None
    new = str(inp.get("new_string") or inp.get("content") or "")
    own = _scene_markers(new)
    if name == "Edit":
        old = str(inp.get("old_string", ""))
        pos = code.find(old) if old else -1
        if pos >= 0:
            before = [m for m in marks if m[0] <= pos]
            scene = before[-1][1] if before else None
        if own:  # edit menyisipkan/mengganti penanda: adegan pertama yang tercantum
            scene = own[0][1]
            for _, n, j in own:
                if n not in {x[1] for x in marks}:
                    marks.append((0, n, j))
    elif own:
        scene = own[0][1]
    scenes = sorted({n: j for _, n, j in marks}.items())
    return {"scene": scene, "scenes": [{"n": n, "judul": j} for n, j in scenes]}


def _pct(nama: str, value: int) -> None:
    """Persen kemajuan (perkiraan dari tonggak kerja Claude); hanya naik, maks 99 sampai benar-benar selesai."""
    if value > int(_status(nama).get("persen") or 0):
        _set(nama, persen=min(99, value))


def _milestone(nama: str, name: str, inp: dict) -> None:
    fname = Path(str(inp.get("file_path", ""))).name
    cmd = str(inp.get("command", ""))
    if name == "Read":
        _pct(nama, 28)
    elif name in ("Write", "Edit"):
        _pct(nama, {"Video.tsx": 50, "index.ts": 52, "musik.json": 68, "caption.json": 74}.get(fname, 45))
    elif name == "TodoWrite":
        _pct(nama, 32)
    elif name == "Bash":
        if "animasi cek" in cmd:
            _pct(nama, 60)
        elif "animasi stills" in cmd:
            _pct(nama, 78)
        elif "animasi render" in cmd:
            _pct(nama, 90)
        elif "animasi musik" in cmd:
            _pct(nama, 70)


def _block_event(nama: str, t0: float, b: dict, stills_ids: set[str]) -> None:
    name, inp = b.get("name", ""), b.get("input") or {}
    _milestone(nama, name, inp)
    fname = Path(str(inp.get("file_path", ""))).name
    if name == "Edit":
        _emit(nama, t0, "edit", file=fname, old=str(inp.get("old_string", ""))[:EVENT_CAP],
              new=str(inp.get("new_string", ""))[:EVENT_CAP], **_scene_info(nama, inp, "Edit"))
    elif name == "Write":
        _emit(nama, t0, "write", file=fname, content=str(inp.get("content", ""))[:EVENT_CAP],
              **_scene_info(nama, inp, "Write"))
    elif name == "Read":
        _emit(nama, t0, "read", file=fname)
    elif name == "TodoWrite":
        _emit(nama, t0, "plan", items=[{"text": x.get("content", ""), "status": x.get("status", "pending")}
                                      for x in inp.get("todos", [])])
    elif name == "Bash":
        cmd = str(inp.get("command", ""))
        _emit(nama, t0, "bash", cmd=cmd[:300])
        if "animasi stills" in cmd and b.get("id"):
            stills_ids.add(b["id"])
    elif name:
        _emit(nama, t0, "tool", name=name)


def _build_prompt(nama: str, instruksi: str) -> tuple[str, bool]:
    revisi = _code_file(nama).exists()
    mode = ("Kode video SUDAH ada — ini REVISI: baca kodenya, terapkan instruksi pengguna, sisanya pertahankan."
            if revisi else "Belum ada kode: buat rencana shot sendiri (langkah 3) lalu tulis kode (langkah 4).")
    data = animasi.load_data(nama)
    gaya = data.get("gaya") or animasi.GAYA_DEFAULT
    dimensi = ("Video ini 3D: bangun tiap shot dengan animasi/src/kit3d (Panggung3D, Kamera3D, dunia & objek toon "
               "bergaris tinta; contoh animasi/src/videos/rental-garut-3d) + teks/kartu/CTA 2D dari kit di atasnya. "
               "Cek pembingkaian 9:16 di frame diam (kamera menembus pohon/objek, objek terpotong, tertutup kartu)."
               if data.get("dimensi") == "3d" else "Video ini 2D: pakai kit 2D (animasi/src/kit).")
    if data.get("mode") == "footage":
        alur = {"montase": "montase b-roll (potongan ikut beat musik; bagian 'Alur montase' di skill)",
                "narasi": "narasi dulu (suara narasi menentukan tempo, footage menutupi tiap frasa; bagian 'Alur narasi')",
                "bicara": "video bicara (pembicara + sisipan b-roll, audio dari narasi.wav; bagian 'Alur bicara')",
                }.get(data.get("alur"), "montase")
        prompt = PROMPT_FOOTAGE.format(nama=nama, mode=mode, alur=alur, preset=data.get("style_preset", ""),
                                       instruksi=instruksi.strip() or "(tidak ada — ikuti skill)")
    else:
        prompt = PROMPT.format(nama=nama, mode=mode, gaya=gaya, dimensi=dimensi,
                               instruksi=instruksi.strip() or "(tidak ada — ikuti skill)")
    return prompt, revisi


def _run_antigravity(nama: str, instruksi: str) -> None:
    from autoreels import antigravity_agent

    prompt, revisi = _build_prompt(nama, instruksi)
    cancel_ev = threading.Event()
    _cancels[nama] = cancel_ev
    t0 = time.time()
    _reset_events(nama)
    _emit(nama, t0, "start", revisi=revisi, instruksi=instruksi[:300], agen="antigravity")
    _set(nama, agen="antigravity", persen=25, detail="Antigravity sedang bekerja…",
         log_add="Antigravity + Remotion dijalankan (cadangan)")
    res: dict | None = None
    try:
        res = antigravity_agent.run_remotion_agent(
            nama,
            prompt,
            on_text=lambda txt: (
                _set(nama, detail=txt.splitlines()[0][:160], log_add=txt[:600]),
                _emit(nama, t0, "text", text=txt[:1200]),
            ),
            on_tool=lambda b: (
                _set(nama, detail=_tool_line(b), log_add="▸ " + _tool_line(b)),
                _block_event(nama, t0, b, set()),
            ),
            on_frame=lambda: _emit(nama, t0, "frame", n=int(time.time())),
            cancel_event=cancel_ev,
        )
    finally:
        _cancels.pop(nama, None)
        _emit(nama, t0, "end", ok=bool(res and res.get("ok")))
    if _status(nama).get("state") == "dihentikan" or (res and res.get("cancelled")):
        return
    if not res or not res.get("ok"):
        raise RuntimeError(str((res or {}).get("result") or "Antigravity berhenti dengan kesalahan.")[:500])
    job = _latest_job_from_output(nama)
    _set(nama, job_id=job, biaya=res.get("cost"),
         hasil_gaya=animasi.load_data(nama).get("gaya") or animasi.GAYA_DEFAULT,
         log_add=str(res.get("result") or "")[:1500])


def _run_claude(nama: str, instruksi: str, agen: str = "claude") -> None:
    if agen == "antigravity":
        _run_antigravity(nama, instruksi)
        return
    prompt, revisi = _build_prompt(nama, instruksi)
    allowed = ",".join(["Read", "Write", "Edit", "Glob", "Grep", "TodoWrite",
                        "Bash(.venv/Scripts/autoreels animasi:*)", "Bash(.venv/Scripts/autoreels.exe animasi:*)"])
    cmd = [_claude_exe(), "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "acceptEdits", "--allowedTools", allowed,
           "--disallowedTools", "WebFetch,WebSearch,PowerShell"]
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    _set(nama, detail="Claude Code sedang bekerja…", log_add="Claude Code dijalankan (langganan, tanpa API key)")
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    _procs[nama] = proc
    result = None
    t0 = time.time()
    stills_ids: set[str] = set()
    _reset_events(nama)  # replay = jalannya terakhir
    _emit(nama, t0, "start", revisi=revisi, instruksi=instruksi[:300])
    _set(nama, persen=25)  # penyiapan footage/suara sudah selesai sebelum Claude dijalankan
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                _set(nama, log_add=line[:300])
                continue
            if ev.get("type") == "assistant":
                for b in ev.get("message", {}).get("content", []):
                    if b.get("type") == "text" and b.get("text", "").strip():
                        _set(nama, detail=b["text"].strip().splitlines()[0][:160], log_add=b["text"].strip()[:600])
                        _emit(nama, t0, "text", text=b["text"].strip()[:1200])
                    elif b.get("type") == "tool_use":
                        t = _tool_line(b)
                        _set(nama, detail=t, log_add="▸ " + t)
                        _block_event(nama, t0, b, stills_ids)
            elif ev.get("type") == "user":  # hasil alat: frame diam selesai dirender → tampilkan di ponsel
                content = ev.get("message", {}).get("content", [])
                for b in content if isinstance(content, list) else []:
                    if b.get("type") == "tool_result" and b.get("tool_use_id") in stills_ids:
                        stills_ids.discard(b["tool_use_id"])
                        _emit(nama, t0, "frame", n=int(time.time()))
            elif ev.get("type") == "result":
                result = ev
        proc.wait()
    finally:
        _procs.pop(nama, None)
        _emit(nama, t0, "end", ok=bool(result and not result.get("is_error")))
    if _status(nama).get("state") == "dihentikan":
        return
    if proc.returncode != 0 or not result or result.get("is_error"):
        msg = (result or {}).get("result") or f"Claude Code berhenti (kode {proc.returncode})."
        raise RuntimeError(str(msg)[:500])
    job = _latest_job_from_output(nama)
    _set(nama, job_id=job, biaya=result.get("total_cost_usd"),
         hasil_gaya=animasi.load_data(nama).get("gaya") or animasi.GAYA_DEFAULT,
         log_add=(result.get("result") or "")[:1500])


def _latest_job_from_output(nama: str) -> str | None:
    want = (animasi.work_dir(nama) / "anim.mp4").resolve()
    for j in sorted(PATHS["output"].glob("*/job.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            d = json.loads(j.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if d.get("source") == "animasi" and Path(d.get("input", "")).resolve() == want:
            return j.parent.name
    return None


class ClaudeIn(BaseModel):
    instruksi: str = ""
    agen: str = "claude"


@router.post("/api/animasi/{nama}/claude")
def run_claude(nama: str, body: ClaudeIn) -> dict:
    nama = _name(nama)
    agen = _check_agen(body.agen)
    animasi.load_data(nama)
    _set(nama, agen=agen)
    _start(nama, "claude", _run_claude, body.instruksi[:2000], agen)
    return {"ok": True, "agen": agen}


@router.get("/api/animasi/{nama}/events")
def events(nama: str, since: int = 0) -> dict:
    """Seluruh event jalannya Claude terakhir (untuk replay / muat awal)."""
    nama = _name(nama)
    return {"events": _read_events(nama, since), "running": _busy(nama) and _status(nama).get("langkah") == "claude"}


@router.get("/api/animasi/{nama}/events/stream")
def events_stream(nama: str, since: int = 0) -> StreamingResponse:
    """SSE: event baru tiap ±0,5 dtk selama Claude berjalan; ditutup dengan event `selesai`."""
    nama = _name(nama)

    def gen():
        pos, idle = since, 0
        while True:
            new = _read_events(nama, pos)
            for e in new:
                pos = e["i"] + 1
                yield f"data: {json.dumps(e, ensure_ascii=False)}\n\n"
            running = _busy(nama) and _status(nama).get("langkah") == "claude"
            if not running and not new:
                yield 'data: {"k":"selesai"}\n\n'
                return
            idle = 0 if new else idle + 1
            if idle % 30 == 29:
                yield ": ping\n\n"
            time.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------------------------------------- pratinjau Remotion Studio
STUDIO_PORT = 3010
_studio: dict[str, subprocess.Popen | None] = {"proc": None}


def _port_open(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sk:
        sk.settimeout(0.3)
        return sk.connect_ex(("127.0.0.1", port)) == 0


def stop_studio() -> None:
    """Matikan Remotion Studio (dipanggil saat server berhenti agar proses Node tidak yatim)."""
    proc = _studio.get("proc")
    if proc and proc.poll() is None:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    _studio["proc"] = None


@router.get("/api/studio-remotion")
def studio_status() -> dict:
    proc = _studio.get("proc")
    alive = bool(proc and proc.poll() is None)
    up = _port_open(STUDIO_PORT)  # Studio sisa dari server sebelumnya di port yang sama juga dipakai
    return {"running": alive or up, "ready": up, "port": STUDIO_PORT}


@router.post("/api/studio-remotion")
def studio_start() -> dict:
    """Nyalakan Remotion Studio (hot reload: pratinjau video berubah tiap Claude menyimpan kode). Sekali nyala, dipakai
    semua video; mati bersama server."""
    import atexit

    st = studio_status()
    if st["running"] or _port_open(STUDIO_PORT):
        return {**st, "running": True}
    try:
        exe = animasi._npx()
    except RuntimeError as e:
        raise _bad(str(e)) from None
    cmd = [exe, "remotion", "studio", "src/index.ts", f"--port={STUDIO_PORT}", "--no-open"]
    _studio["proc"] = subprocess.Popen(cmd, cwd=animasi.ANIM_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    atexit.register(stop_studio)
    return {"running": True, "ready": False, "port": STUDIO_PORT}


@router.post("/api/animasi/{nama}/stop")
def stop(nama: str) -> dict:
    nama = _name(nama)
    proc = _procs.get(nama)
    if proc and proc.poll() is None:
        _set(nama, state="dihentikan", detail="dihentikan pengguna", log_add="dihentikan dari web")
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)  # termasuk anak proses
        return {"ok": True}
    cancel_ev = _cancels.get(nama)
    if cancel_ev is not None:
        _set(nama, state="dihentikan", detail="dihentikan pengguna", log_add="dihentikan dari web")
        cancel_ev.set()
        return {"ok": True}
    raise _bad("Tidak ada proses penyusun yang berjalan untuk video ini.", 404)


# ---------------------------------------------------------------------------------------------- 4. frame & render
def _stills(nama: str) -> None:
    _set(nama, detail="merender frame diam…")
    animasi.stills(nama, log=lambda m: _set(nama, log_add=str(m).strip()))


def _render(nama: str) -> None:
    from autoreels.joblock import job_lock

    with job_lock(f"Animasi: render {nama}", wait=True,
                  on_wait=lambda h: _set(nama, detail=f"menunggu giliran CPU ({h.get('label', '')})")):
        _set(nama, detail="render Remotion + checklist…")
        res = animasi.render(nama, log=lambda m: _set(nama, log_add=str(m).strip()))
        _set(nama, job_id=res.job_id, hasil_gaya=animasi.load_data(nama).get("gaya") or animasi.GAYA_DEFAULT,
             log_add=f"hasil: {res.status}")


def _need_code(nama: str) -> None:
    if not _code_file(nama).exists():
        raise _bad("Kode animasi belum ada — jalankan 'Buat dengan Claude Code' dulu.")


@router.post("/api/animasi/{nama}/stills")
def run_stills(nama: str) -> dict:
    nama = _name(nama)
    _need_code(nama)
    _start(nama, "frame", _stills)
    return {"ok": True}


@router.post("/api/animasi/{nama}/render")
def run_render(nama: str) -> dict:
    nama = _name(nama)
    _need_code(nama)
    try:
        animasi.load_caption(nama)
    except (FileNotFoundError, ValueError) as e:
        raise _bad(str(e)) from None
    _start(nama, "render", _render)
    return {"ok": True}
