"""Mode "Claude sebagai sutradara" (skill /racik-sutradara): Claude Code di chat menggantikan Director (dan
opsional vision/Critic), memakai kuota langganan lewat percakapan, tanpa biaya API untuk langkah itu.

Alur:
  1. `autoreels prepare`  → ingest, analisis, musik, narasi (opsional), deskripsi adegan (API atau lembar kontak
     gambar untuk dilihat Claude) → work/<job>/sutradara/konteks.md
  2. Claude membaca konteks.md, menulis work/<job>/sutradara/edl.json (+ opsional critic.json)
  3. `autoreels finish`   → validasi aturan keras (gagal = tidak dirender, Claude memperbaiki), render, checklist
Prinsip tetap: LLM (Claude) memutuskan, kode deterministik yang merender & memeriksa.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from autoreels.analyze.models import Analysis
from autoreels.config import PATHS, get_settings, load_brand, load_pillars, load_style
from autoreels.describe import SceneDescription
from autoreels.edl import EDL, Narration

MANUAL_DIRNAME = "sutradara"
CLAUDE_MODEL_LABEL = "claude-code (chat)"
SHEET_COLS, SHEET_ROWS, CELL_W = 3, 4, 360


class ManualEdlError(RuntimeError):
    """EDL tulisan Claude melanggar aturan keras — perbaiki lalu jalankan `finish` lagi."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("EDL belum lolos validasi:\n- " + "\n- ".join(errors))
        self.errors = errors


def manual_dir(job_id: str) -> Path:
    return PATHS["work"] / job_id / MANUAL_DIRNAME


def _state_file(job_id: str) -> Path:
    return manual_dir(job_id) / "prep.json"


def load_state(job_id: str) -> dict:
    f = _state_file(job_id)
    if not f.exists():
        raise FileNotFoundError(f"Job {job_id} belum disiapkan (jalankan `autoreels prepare` dulu).")
    return json.loads(f.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 1. prepare
def prepare(
    *, input_path: Path, pillar: str, brief: str, style_name: str, duration: float, describe: str = "claude",
    engine: str = "api", clips: list[str] | None = None, narration: Path | None = None,
    music_file: Path | None = None, hook_text: str | None = None, cta_text: str | None = None,
    blur_faces: bool = False, blur_plates: bool = False, log=print,
) -> str:
    """describe: 'claude' (lembar kontak gambar, Claude yang mendeskripsikan) | 'api' (vision model .env)."""
    from autoreels.analyze import analyze_clips
    from autoreels.analyze.audio import prepare_music
    from autoreels.ingest import ingest, make_job_id

    if describe not in ("claude", "api"):
        raise ValueError("describe harus 'claude' atau 'api'")
    job_id = make_job_id(pillar)
    work_dir = PATHS["work"] / job_id
    mdir = manual_dir(job_id)
    mdir.mkdir(parents=True, exist_ok=True)
    style = load_style(style_name)
    _, vision_model = get_settings().models_for(engine)
    log(f"Job {job_id} — mode Claude sebagai sutradara")

    log("[1/4] Ingest …")
    sources = ingest(input_path, log=log, only=clips)
    log("[2/4] Analisis adegan, kualitas, crop …")
    analysis = analyze_clips(sources, log=log)
    if not analysis.usable_scenes():
        raise RuntimeError("Semua adegan tidak layak pakai (blur/gelap/goyang). Periksa footage.")

    narr = None
    if narration is not None:
        from autoreels.narration import prepare_narration

        log("  narasi: transkripsi & pembersihan …")
        narr = prepare_narration(narration, mdir, log=log)
        if narr.duration > 90:
            raise RuntimeError(f"Narasi {narr.duration:.0f} dtk terlalu panjang untuk Reels (maks 90 dtk).")
        duration = narr.duration
        (mdir / "narasi.json").write_text(json.dumps(narr.model_dump(), ensure_ascii=False, indent=1),
                                          encoding="utf-8")
        (mdir / "narasi_frasa.json").write_text(
            json.dumps([p.text for p in narr.phrases], ensure_ascii=False, indent=1), encoding="utf-8")

    log("[3/4] Musik …")
    analysis.music = prepare_music(style.get("music_mood_default", "upbeat"), job_id, duration, forced=music_file,
                                   log=log)
    (work_dir / "analysis.json").write_text(analysis.model_dump_json(indent=1), encoding="utf-8")

    job = {
        "job_id": job_id, "created": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "input": str(input_path),
        "pillar": pillar, "brief": brief, "style": style_name, "duration": round(duration, 2),
        "hook_text": hook_text, "cta_text": cta_text, "voiceover": "none", "clips": clips, "engine": engine,
        "critic": False, "mode": "sutradara_claude",
        "models": {"director": CLAUDE_MODEL_LABEL,
                   "vision": vision_model if describe == "api" else CLAUDE_MODEL_LABEL},
    }
    if narr is not None:
        job.update({"flow": "narasi", "narration": str(narration)})
    state = {"job": job, "describe": describe, "blur_faces": blur_faces, "blur_plates": blur_plates,
             "music_file": str(music_file) if music_file else None}
    _state_file(job_id).write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

    log("[4/4] Deskripsi adegan …")
    if describe == "api":
        from autoreels.describe import describe_scenes
        from autoreels.llm import CostTracker, LLMClient

        tracker = CostTracker()
        descriptions = describe_scenes(analysis, LLMClient(tracker, log=log), vision_model, log=log)
        _save_descriptions(job_id, descriptions)
        log(f"  biaya vision ≈ ${tracker.total_cost:.4f}")
        build_context(job_id)
    else:
        sheets = contact_sheets(job_id, analysis)
        template = [{"scene_id": s.scene_id, "durasi": round(s.duration, 2), "subject": "", "action": "",
                     "setting": "", "mood": "", "hook_potential": 0, "relevance_rental": 0, "suggested_text": None,
                     "stage": None} for s in analysis.usable_scenes()]
        (mdir / "deskripsi.json").write_text(json.dumps(template, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"  {len(sheets)} lembar kontak ({len(template)} adegan) → isi {mdir / 'deskripsi.json'}, "
            "lalu `autoreels prepare --job <id> --konteks`")
    return job_id


def contact_sheets(job_id: str, analysis: Analysis) -> list[Path]:
    """Gambar tengah tiap adegan layak pakai, 12 per lembar, berlabel scene_id + durasi (hemat dibaca Claude)."""
    import cv2
    import numpy as np

    from autoreels.describe import extract_frames
    from autoreels.ingest import CACHE_ROOT

    mdir = manual_dir(job_id)
    for old in mdir.glob("lembar_*.jpg"):
        old.unlink()
    cells = []
    for s in analysis.usable_scenes():
        clip = analysis.clip(s.source_file)
        frames = extract_frames(s, clip.hash, CACHE_ROOT / clip.hash / "proxy.mp4")
        img = cv2.imread(str(frames[len(frames) // 2]))
        if img is None:
            continue
        h = int(img.shape[0] * CELL_W / img.shape[1])
        img = cv2.resize(img, (CELL_W, min(h, CELL_W)))  # potret dipotong persegi agar grid rapi
        label = f"{s.scene_id}  {s.duration:.1f}s"
        cv2.rectangle(img, (0, 0), (CELL_W, 30), (0, 0, 0), -1)
        cv2.putText(img, label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cells.append(img)
    per = SHEET_COLS * SHEET_ROWS
    out = []
    for n in range(0, len(cells), per):
        chunk = cells[n:n + per]
        cell_h = max(c.shape[0] for c in chunk)
        sheet = np.full((cell_h * SHEET_ROWS, CELL_W * SHEET_COLS, 3), 24, np.uint8)
        for k, c in enumerate(chunk):
            r, col = divmod(k, SHEET_COLS)
            sheet[r * cell_h:r * cell_h + c.shape[0], col * CELL_W:(col + 1) * CELL_W] = c
        rows_used = (len(chunk) + SHEET_COLS - 1) // SHEET_COLS
        f = mdir / f"lembar_{n // per + 1:02d}.jpg"
        cv2.imwrite(str(f), sheet[:cell_h * rows_used], [cv2.IMWRITE_JPEG_QUALITY, 80])
        out.append(f)
    return out


def _save_descriptions(job_id: str, descriptions: dict[str, SceneDescription]) -> None:
    (PATHS["work"] / job_id / "descriptions.json").write_text(
        json.dumps({k: v.model_dump() for k, v in descriptions.items()}, ensure_ascii=False, indent=1),
        encoding="utf-8")


def load_descriptions(job_id: str) -> dict[str, SceneDescription]:
    """descriptions.json (API) atau sutradara/deskripsi.json (diisi Claude; baris kosong dilewati)."""
    api_file = PATHS["work"] / job_id / "descriptions.json"
    if api_file.exists():
        data = json.loads(api_file.read_text(encoding="utf-8"))
        return {k: SceneDescription(**v) for k, v in data.items()}
    manual_file = manual_dir(job_id) / "deskripsi.json"
    if not manual_file.exists():
        return {}
    out = {}
    for row in json.loads(manual_file.read_text(encoding="utf-8")):
        if not str(row.get("subject", "")).strip():
            continue
        d = SceneDescription(**{k: v for k, v in row.items() if k != "durasi"})
        out[d.scene_id] = d
    return out


def _analysis(job_id: str) -> Analysis:
    return Analysis.model_validate_json((PATHS["work"] / job_id / "analysis.json").read_text(encoding="utf-8"))


def _narration(job_id: str) -> Narration | None:
    f = manual_dir(job_id) / "narasi.json"
    if not f.exists():
        return None
    narr = Narration(**json.loads(f.read_text(encoding="utf-8")))
    texts_file = manual_dir(job_id) / "narasi_frasa.json"
    if texts_file.exists():  # teks frasa yang dikoreksi Claude/manusia (waktu audio tetap)
        from autoreels.narration import apply_texts

        narr = apply_texts(narr, json.loads(texts_file.read_text(encoding="utf-8")))
    return narr


def build_context(job_id: str) -> Path:
    """Tulis konteks Director (prompt sistem + data) yang sama persis dengan yang dikirim ke LLM API."""
    from autoreels.director import build_messages

    state = load_state(job_id)
    job = state["job"]
    analysis = _analysis(job_id)
    descriptions = load_descriptions(job_id)
    missing = [s.scene_id for s in analysis.usable_scenes() if s.scene_id not in descriptions]
    brief = job["brief"]
    if job.get("hook_text"):
        brief += f"\nTeks hook WAJIB persis: \"{job['hook_text']}\" (pilih visual hook yang cocok)."
    if job.get("cta_text"):
        brief += f"\nTeks CTA WAJIB persis: \"{job['cta_text']}\"."
    narr = _narration(job_id)
    messages = build_messages(
        analysis=analysis, descriptions=descriptions, music=analysis.music, brief=brief, pillar=job["pillar"],
        style_name=job["style"], style=load_style(job["style"]), duration=job["duration"], narration=narr)
    mdir = manual_dir(job_id)
    lines = [
        f"# Konteks Director — job `{job_id}`", "",
        "Tulis EDL (JSON) ke `edl.json` di folder ini, sesuai prompt sistem di bawah, lalu jalankan "
        f"`autoreels finish --job {job_id}`.",
    ]
    if missing:
        lines += ["", f"⚠️ {len(missing)} adegan belum punya deskripsi (dianggap 'tidak diketahui'): "
                      + ", ".join(missing[:20])]
    lines += ["", "## Prompt sistem", "", messages[0]["content"], "", "## Data", "", messages[1]["content"]]
    out = mdir / "konteks.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ---------------------------------------------------------------- 3. finish
def _critic_dict(critic_file: Path | None) -> dict | None:
    if critic_file is None:
        return None
    from autoreels.critic import CriticOutput, CriticReview

    out = CriticOutput.model_validate_json(Path(critic_file).read_text(encoding="utf-8"))
    review = CriticReview(round=0, output=out, model=CLAUDE_MODEL_LABEL)
    return {"chosen_round": 0, "critic_revisions": 0, "final": review.to_dict(), "rounds": [review.to_dict()]}


def check(job_id: str, edl_file: Path | None = None):
    """Validasi EDL tulisan Claude (tanpa render). Kembalikan ValidationResult."""
    from autoreels.validate import validate_edl

    state = load_state(job_id)
    job = state["job"]
    edl = EDL.load(edl_file or manual_dir(job_id) / "edl.json")
    narr = _narration(job_id)
    if narr is not None:  # data narasi selalu dari kode
        edl.narration = narr
        edl.target_duration_sec = round(narr.duration, 2)
    if job.get("hook_text"):
        edl.hook.overlay_text = job["hook_text"]
    if job.get("cta_text") and edl.cta:
        edl.cta.text = job["cta_text"]
    analysis = _analysis(job_id)
    result = validate_edl(edl, analysis, load_style(job["style"]), analysis.music, load_brand(),
                          load_pillars().get(job["pillar"], {}).get("hashtags", []), load_descriptions(job_id))
    result.edl.privacy.blur_faces = state.get("blur_faces", False)
    result.edl.privacy.blur_plates = state.get("blur_plates", False)
    return result


def finish(job_id: str, *, edl_file: Path | None = None, critic_file: Path | None = None, preview: bool = False,
           force: bool = False, log=print, on_progress=None):
    """Validasi → (gagal: ManualEdlError, tidak dirender) → render, checklist, laporan. Kembalikan JobResult."""
    from autoreels.llm import CostTracker
    from autoreels.pipeline import _finish, _Timer
    from autoreels.progress import Progress

    validation = check(job_id, edl_file)
    for f in validation.fixes:
        log(f"  perbaikan otomatis: {f}")
    for w in validation.warnings:
        log(f"  peringatan: {w}")
    if validation.errors and not force:
        raise ManualEdlError(validation.errors)
    state = load_state(job_id)
    job = state["job"]
    out_dir = PATHS["output"] / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    if validation.edl.narration is not None:
        shutil.copyfile(manual_dir(job_id) / "narasi.wav", out_dir / "narasi.wav")
    progress = Progress(job_id, PATHS["work"] / job_id / "progress.json", on_progress)
    progress.done_steps = {"ingest", "analyze", "describe", "direct"}
    try:
        return _finish(job=job, edl=validation.edl, analysis=_analysis(job_id),
                       descriptions=load_descriptions(job_id), validation=validation, style=load_style(job["style"]),
                       brand=load_brand(), work_dir=PATHS["work"] / job_id, out_dir=out_dir, tracker=CostTracker(),
                       timer=_Timer(), revisions=0, log=log, preview=preview, progress=progress,
                       critic=_critic_dict(critic_file), review_visual=False)  # mode tanpa API
    except BaseException:
        progress.end("gagal")
        raise
