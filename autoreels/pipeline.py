"""Orkestrasi pipeline: ingest → analyze → describe → direct/validate → render → checklist → laporan.

File per job:
  work/<job_id>/   analysis.json, descriptions.json, render/ (file antara)
  output/<job_id>/ reel.mp4, cover.jpg, edl.json, job.json, caption.txt, report.md, critic.json, result.json
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from autoreels.analyze import analyze_clips
from autoreels.analyze.audio import prepare_music
from autoreels.analyze.models import Analysis
from autoreels import critic as critic_mod
from autoreels.checklist import Checklist, build_checklist
from autoreels.config import PATHS, get_settings, load_brand, load_pillars, load_style
from autoreels.describe import SceneDescription, describe_scenes
from autoreels.director import MAX_CRITIC_ROUNDS, direct
from autoreels.edl import EDL, MusicMood
from autoreels.ingest import ingest, make_job_id
from autoreels.llm import CostTracker, LLMClient
from autoreels.progress import Progress
from autoreels.render import render_reel
from autoreels.validate import ValidationResult, validate_edl


@dataclass
class JobResult:
    job_id: str
    out_dir: Path
    reel: Path
    status: str
    checklist: Checklist
    validation: ValidationResult
    cost_usd: float
    timings: dict[str, float] = field(default_factory=dict)


class _Timer:
    def __init__(self) -> None:
        self.timings: dict[str, float] = {}

    def __call__(self, name: str):
        timer = self

        class _Ctx:
            def __enter__(self):
                self.t = time.perf_counter()

            def __exit__(self, *exc):
                timer.timings[name] = round(time.perf_counter() - self.t, 1)

        return _Ctx()


PROMO_WORDS = {"sewa", "rental", "booking", "pesan", "whatsapp", "wa", "hubungi", "konsultasi",
               "survei", "lowongan", "loker", "rekrut", "promo", "diskon", "harga", "jasa", "layanan", "order",
               "kontraktor", "renovasi", "katering"}


MONTAGE_MAX_CLIP_SEC = 600  # montase/narasi: klip > 10 menit = video bicara/podcast, analisis ratusan adegan sia-sia
TALK_MAX_SEC = 600  # video bicara > 10 menit → wajib lewat "cari cuplikan" (analisis ratusan adegan sia-sia)



# --- catatan keputusan AI untuk layar proses web (Progress.note) -----------------------
def _safe_note(fn):
    """Catatan untuk layar proses hanya tampilan: error di sini dicatat di log, job tetap jalan."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            print(f"  [catatan AI dilewati] {fn.__name__}: {e}")
    return wrapper


@_safe_note
def _note_talk(progress, narration) -> None:
    ph = narration.phrases
    lines = [f"{len(ph)} frasa, {narration.duration:.0f} dtk dari video pembicara"]
    if narration.cold_open_sec:
        lines.append(f"Cold open {narration.cold_open_sec:.1f} dtk di depan sebagai teaser")
    lines += [f"{p.start:5.1f} dtk  “{p.text}”" for p in ph[:12]]
    if len(ph) > 12:
        lines.append(f"… dan {len(ph) - 12} frasa lain")
    progress.note("AI memilih kalimat yang dipakai", lines)


@_safe_note
def _note_describe(progress, descriptions: dict) -> None:
    if not descriptions:
        return
    best = sorted(descriptions.items(), key=lambda kv: -(kv[1].hook_potential or 0))[:5]
    lines = [f"{len(descriptions)} adegan dilihat AI. Paling memikat:"]
    lines += [f"{sid}: {d.subject or '-'} — {d.action or '-'} (potensi hook {d.hook_potential}/5)" for sid, d in best]
    progress.note("AI melihat isi footage", lines)


@_safe_note
def _note_director(progress, edl: EDL, critic: dict | None, fixes: list[str]) -> None:
    lines = [f"Hook ({edl.hook.type.value}): “{edl.hook.overlay_text or '-'}”"]
    for seg in edl.segments[:16]:
        dur = (seg.end - seg.start) / (seg.speed or 1.0)
        why = f" — {seg.reason}" if seg.reason else ""
        lines.append(f"{seg.index}. {seg.role.value} {dur:.1f} dtk{why}")
    if len(edl.segments) > 16:
        lines.append(f"… dan {len(edl.segments) - 16} potongan lain")
    if edl.cta:
        lines.append(f"CTA di {edl.cta.at_sec:.1f} dtk: “{edl.cta.text}”")
    lines.append(f"Musik: {edl.music.mood.value}")
    progress.note("Director menyusun urutan edit", lines)
    for r in (critic or {}).get("rounds") or []:
        notes = r.get("revision_notes") or []
        rl = [f"Rata-rata {r['average']:.1f}/5, hook {r['hook']}/5 — {'lolos' if r.get('passed') else 'perlu revisi'}"]
        if r.get("summary"):
            rl.append(r["summary"])
        rl += [f"Catatan: {n}" for n in notes[:4]]
        progress.note(f"Critic menilai (putaran {r['round'] + 1})", rl)
    if critic and critic.get("critic_revisions"):
        progress.note("Director merevisi atas catatan Critic",
                      [f"{critic['critic_revisions']} kali revisi; dipakai versi putaran {critic.get('chosen_round', 0) + 1}"])
    if fixes:
        progress.note("Aturan otomatis merapikan edit", fixes[:8])


@_safe_note
def _note_visual(progress, visual: dict | None) -> None:
    """visual = dict dari review.review_video ({score, summary, issues[...]} atau {error})."""
    if not visual:
        return
    try:
        if visual.get("error"):
            progress.note("AI mengecek video jadi", [f"Tidak berjalan: {visual['error']}"])
            return
        lines = [f"Skor {visual.get('score')}/5" + (f" — {visual['summary']}" if visual.get("summary") else "")]
        for x in (visual.get("issues") or [])[:5]:
            lines.append(f"[{x.get('severity')}] {x.get('problem', '')}" + (f" → {x['fix']}" if x.get("fix") else ""))
        progress.note("AI mengecek video jadi", lines)
    except Exception:  # noqa: BLE001 — catatan tampilan tidak boleh menggagalkan job
        pass


def promo_signal(brief: str, narration, brand: dict) -> bool:
    """Apakah instruksi/ucapan menyinggung Brand atau layanannya (ajakan memakai jasa)?"""
    import re

    text = " ".join([brief or "", " ".join(p.text for p in narration.phrases) if narration is not None else ""])
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    names = {w for n in (brand.get("short_name", ""), brand.get("company_name", "")) for w in n.lower().split()
             if len(w) > 3 and w not in {"energi", "indonesia"}}
    return bool(words & (PROMO_WORDS | names))


def write_caption(edl: EDL, brand: dict, path: Path) -> Path:
    wa = brand.get("whatsapp", {}).get("display", "")
    lines = [edl.caption_suggestion.strip()]
    if edl.purpose.value == "promosi":  # video informasi: caption tanpa ajakan booking
        if wa and wa not in edl.caption_suggestion:
            lines.append(f"\n📲 Booking & info: WhatsApp {wa}")
        lines.append("📍 Garut, Jawa Barat")
    lines.append("\n" + " ".join(edl.hashtags))
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path


def write_report(
    *, path: Path, job: dict, edl: EDL, validation: ValidationResult, checklist: Checklist,
    tracker: CostTracker, timings: dict[str, float], revisions: int, analysis: Analysis,
    critic: dict | None = None,
) -> None:
    music = analysis.music
    usable = len(analysis.usable_scenes())
    lines = [
        f"# Laporan Job `{job['job_id']}`",
        "",
        f"**Status:** {'✅ SIAP UNGGAH' if checklist.status == 'siap_unggah' else '⚠️ PERLU TINJAU'}",
        "",
        "## Ringkasan",
        f"- Dibuat: {job['created']}",
        f"- Instruksi: {job['brief']}",
        f"- Pilar: {job['pillar']} · Style: {job['style']} · Target: {job['duration']} dtk",
        f"- Footage: {len(analysis.clips)} klip, {len(analysis.scenes)} adegan ({usable} layak pakai)",
        f"- Hasil: {validation.stats.get('total_duration')} dtk, {validation.stats.get('segments')} segmen, "
        f"hook {validation.stats.get('hook_duration')} dtk",
        f"- Musik: {Path(music.path).name if music else '-'}"
        + (f" ({music.tempo:.0f} BPM, mulai {music.start_offset:.1f} dtk)" if music else ""),
        f"- Ketepatan beat: {validation.stats.get('beat_accuracy')}",
        f"- Revisi Director: {revisions}"
        + (f" + {critic['critic_revisions']} atas catatan Critic" if critic and critic.get("critic_revisions") else ""),
        "- Critic: " + (f"rata-rata {critic['final']['average']:.1f}, hook {critic['final']['hook']}/5"
                       if critic and critic.get("final") else "tidak berjalan"),
        f"- Model: director `{job['models']['director']}`, vision `{job['models']['vision']}`",
        "",
        f"**Hook:** \"{edl.hook.overlay_text}\" ({edl.hook.type.value})  ",
        f"**CTA:** \"{edl.cta.text if edl.cta else '-'}\"",
        "",
        "## Checklist Siap Unggah",
        checklist.markdown(),
        "",
    ]
    if critic and critic.get("rounds"):
        reviews = [critic_mod.CriticReview.from_dict(r) for r in critic["rounds"]]
        lines += ["## Penilaian Critic (rubrik 1–5)", critic_mod.markdown(reviews, critic.get("chosen_round")), ""]
    if validation.errors:
        lines += ["## Error validasi (belum terselesaikan)", *[f"- {e}" for e in validation.errors], ""]
    if validation.fixes:
        lines += ["## Perbaikan otomatis oleh validator", *[f"- {f}" for f in validation.fixes], ""]
    if validation.warnings:
        lines += ["## Peringatan", *[f"- {w}" for w in validation.warnings], ""]
    lines += [
        "## Urutan segmen",
        "| # | Role | Sumber | Rentang | Durasi | Transisi | Teks | Alasan |",
        "|---|---|---|---|---|---|---|---|",
        *[f"| {s.index} | {s.role.value} | {s.source_file[:40]} | {s.start:.2f}–{s.end:.2f} | "
          f"{s.output_duration:.2f} | {s.transition_in.value} | {s.overlay_text or ''} | {s.reason} |"
          for s in edl.segments],
        "",
        "## Waktu proses (detik)",
        *[f"- {k}: {v}" for k, v in timings.items()],
        f"- **total: {round(sum(timings.values()), 1)}**",
        "",
        "## Biaya API",
        tracker.summary_markdown(),
        "",
        "## Catatan untuk peninjau",
        edl.notes_for_human or "-",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_result(out_dir: Path, checklist: Checklist, stats: dict, critic: dict | None = None,
                 visual: dict | None = None) -> Path:
    """Ringkasan hasil yang mudah dibaca mesin (dipakai web UI): status, statistik, checklist."""
    data = {
        "status": checklist.status,
        "stats": stats,
        "checklist": [{"group": i.group, "name": i.name, "passed": i.passed, "required": i.required,
                       "detail": i.detail} for i in checklist.items],
        "critic": critic,
        "visual": visual,
    }
    path = out_dir / "result.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def _finish(
    *, job: dict, edl: EDL, analysis: Analysis, descriptions: dict[str, SceneDescription],
    validation: ValidationResult, style: dict, brand: dict, work_dir: Path, out_dir: Path,
    tracker: CostTracker, timer: _Timer, revisions: int, log, preview: bool, progress: Progress,
    critic: dict | None = None, review_visual: bool = True, snapshot_ai: bool = True,
) -> JobResult:
    edl.save(out_dir / "edl.json")
    if snapshot_ai:  # versi AI disimpan sekali untuk belajar dari editan manusia
        from autoreels.preferences import snapshot_ai as _snapshot

        _snapshot(out_dir, edl)
    if critic is not None:
        (out_dir / "critic.json").write_text(json.dumps(critic, ensure_ascii=False, indent=1), encoding="utf-8")
    job_out = {**job, "analysis": analysis.model_dump(),
               "descriptions": {k: v.model_dump() for k, v in descriptions.items()}}
    (out_dir / "job.json").write_text(json.dumps(job_out, ensure_ascii=False, indent=1), encoding="utf-8")

    log("[7/7] Render …")
    progress.start("render")
    with timer("render"):
        rendered = render_reel(edl, analysis, style, brand, work_dir, out_dir, log=log, preview=preview,
                               llm=LLMClient(tracker, log=log),
                               progress=progress)
    caption = write_caption(edl, brand, out_dir / "caption.txt")
    progress.finish("render")

    visual = None
    vision_model = (job.get("models") or {}).get("vision")
    if review_visual and not preview and vision_model:  # cek frame video jadi (melengkapi Critic yang membaca EDL)
        from autoreels.review import review_video, save_review

        log(f"Cek visual video jadi ({vision_model}) …")
        progress.start("checklist", "AI melihat frame video jadi")
        with timer("cek_visual"):
            visual = review_video(rendered.reel, edl, LLMClient(tracker, log=log), vision_model, work_dir, log=log)
        save_review(visual, out_dir)
        _note_visual(progress, visual)

    log("Memeriksa Checklist Siap Unggah …")
    progress.start("checklist", "cek video, hook, style, teks")
    with timer("checklist"):
        checklist = build_checklist(
            edl=edl, analysis=analysis, validation=validation, style=style, brand=brand,
            reel=rendered.reel, descriptions=descriptions, caption_file=caption,
            cover=rendered.cover, font_file=rendered.font_file, voice=rendered.voice, privacy=rendered.privacy,
            critic=critic,
        )
        from autoreels.review import add_visual_checks

        add_visual_checks(checklist, visual)
    write_report(path=out_dir / "report.md", job=job, edl=edl, validation=validation, checklist=checklist,
                 tracker=tracker, timings=timer.timings, revisions=revisions, analysis=analysis, critic=critic)
    (out_dir / "status.txt").write_text(checklist.status + "\n", encoding="utf-8")
    final = (critic or {}).get("final") or {}
    write_result(out_dir, checklist, {
        **validation.stats, "cost_usd": round(tracker.total_cost, 5),
        "process_sec": round(sum(timer.timings.values()), 1),
        "target_duration": edl.target_duration_sec, "revisions": revisions,
        "critic_revisions": (critic or {}).get("critic_revisions", 0),
        "critic_average": final.get("average"), "critic_hook": final.get("hook"),
        "visual_score": (visual or {}).get("score"),
    }, critic=critic, visual=visual)
    progress.end("selesai")
    return JobResult(job["job_id"], out_dir, rendered.reel, checklist.status, checklist, validation,
                     tracker.total_cost, timer.timings)


def run_pipeline(
    *, input_path: Path, pillar: str, brief: str, style_name: str, duration: float,
    music_file: Path | None = None, log=print, preview: bool = False, on_progress=None,
    hook_text: str | None = None, cta_text: str | None = None, job_id: str | None = None,
    voiceover: str = "none", voice: str = "Puck", engine: str = "api", clips: list[str] | None = None,
    blur_faces: bool = False, blur_plates: bool = False, narration: Path | None = None, critic: bool = True,
    narration_draft: str | None = None, talk: Path | None = None, purpose: str | None = None,
    no_music: bool = False, logo: bool = True,
    llm_model: str | None = None, critic_model: str | None = None, talk_full: bool = False,
) -> JobResult:
    """hook_text / cta_text: bila diisi, teks itu WAJIB dipakai; bila kosong, AI yang memilih.
    job_id: boleh ditentukan pemanggil (web server) agar ID diketahui sebelum proses mulai.
    voiceover: none | rekam (suara sendiri, direkam setelah naskah jadi) | gemini (suara AI).
    engine: api (default) | local (model Ollama di laptop, untuk uji coba).
    clips: nama file yang dipilih di folder input (None = semua).
    blur_faces / blur_plates: samarkan wajah / pelat nomor (pilihan pengguna, default mati).
    narration: file audio/video narasi → alur "narasi dulu" (durasi mengikuti narasi, potongan per frasa).
    critic: True = Critic menilai & Director merevisi; "nilai" = Critic hanya menilai (baseline evaluasi);
    False = tanpa Critic.
    narration_draft: ID draf transkrip yang sudah diperiksa manusia (web) — dipakai apa adanya.
    talk: video pembicara (Tahap 3) → kalimat terbaik jadi Reel bersubtitle; input_path = b-roll (boleh sama).
    purpose: promosi | informasi (None = dipilih Director); informasi = tanpa CTA jualan.
    no_music: True = tanpa musik latar (hanya suara narasi/pembicara, atau senyap).
    logo: False = tanpa logo/watermark di pojok video.
    llm_model / critic_model: ganti model Director / Critic untuk job ini (evaluasi antar-model).
    talk_full: video bicara utuh — durasi mengikuti panjang ucapan (maks 180 dtk), tanpa diringkas AI."""
    job_id = job_id or make_job_id(pillar)
    work_dir = PATHS["work"] / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    progress = Progress(job_id, work_dir / "progress.json", on_progress)
    try:
        return _run(job_id=job_id, work_dir=work_dir, progress=progress, input_path=input_path,
                    pillar=pillar, brief=brief, style_name=style_name, duration=duration,
                    music_file=music_file, log=log, preview=preview,
                    hook_text=(hook_text or "").strip() or None, cta_text=(cta_text or "").strip() or None,
                    voiceover=voiceover, voice=voice, engine=engine, clip_names=clips,
                    blur_faces=blur_faces, blur_plates=blur_plates, narration_source=narration,
                    use_critic=critic, narration_draft=narration_draft, talk_source=talk, purpose=purpose,
                    no_music=no_music, logo=logo, llm_model_override=llm_model, critic_model=critic_model,
                    talk_full=talk_full)
    except BaseException:
        progress.end("gagal")
        raise


def _run(
    *, job_id: str, work_dir: Path, progress: Progress, input_path: Path, pillar: str, brief: str,
    style_name: str, duration: float, music_file: Path | None, log, preview: bool,
    hook_text: str | None = None, cta_text: str | None = None,
    voiceover: str = "none", voice: str = "Puck", engine: str = "api", clip_names: list[str] | None = None,
    blur_faces: bool = False, blur_plates: bool = False, narration_source: Path | None = None,
    use_critic: bool | str = True, narration_draft: str | None = None, talk_source: Path | None = None,
    purpose: str | None = None, no_music: bool = False, logo: bool = True,
    llm_model_override: str | None = None, critic_model: str | None = None, talk_full: bool = False,
) -> JobResult:
    settings = get_settings()
    llm_model, vision_model = settings.models_for(engine)
    llm_model = llm_model_override or llm_model
    style = load_style(style_name)
    brand = load_brand()
    tracker = CostTracker()
    llm = LLMClient(tracker, log=log)
    if llm_model_override:  # model Director ditentukan (evaluasi): tanpa cadangan diam-diam agar hasil murni
        llm.fallback_enabled = False
    timer = _Timer()
    out_dir = PATHS["output"] / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    job = {
        "job_id": job_id, "created": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "input": str(input_path),
        "pillar": pillar, "brief": brief, "style": style_name, "duration": duration,
        "hook_text": hook_text, "cta_text": cta_text, "voiceover": voiceover,
        "clips": clip_names, "engine": engine,
        "options": {"watermark": logo, "no_music": no_music, "purpose": purpose, "talk_full": talk_full,
                    "blur_faces": blur_faces, "blur_plates": blur_plates},
        "critic": {True: "revisi", "nilai": "nilai"}.get(use_critic, "mati"), "models": {"director": llm_model, "vision": vision_model, "critic": critic_model or llm_model},
    }
    director_brief = brief
    if hook_text:
        director_brief += f"\nTeks hook WAJIB persis: \"{hook_text}\" (pilih visual hook yang cocok)."
    if cta_text:
        director_brief += f"\nTeks CTA WAJIB persis: \"{cta_text}\"."
    if purpose:
        director_brief += f"\nTujuan video (purpose) WAJIB: {purpose}."
    if no_music:
        director_brief += "\nTanpa musik latar: music.mood WAJIB \"none\"."
    log(f"Job {job_id}" + (" — mesin AI LOKAL (Ollama)" if engine == "local" else ""))

    log("[1/7] Ingest …")
    progress.start("ingest")
    with timer("ingest"):
        clips = ingest(input_path, log=log, progress=progress, only=clip_names)
        speaker_clip = None
        if talk_source is None:
            too_long = [c.name for c in clips if c.info.duration > MONTAGE_MAX_CLIP_SEC]
            if too_long:
                raise RuntimeError(
                    f"Klip {', '.join(too_long)} lebih dari {MONTAGE_MAX_CLIP_SEC // 60} menit — terlalu panjang untuk "
                    "montase/narasi (ratusan adegan dianalisis AI). Untuk podcast/kuliah pakai alur Video bicara + "
                    "Cari cuplikan; untuk b-roll potong dulu jadi klip pendek.")
        if talk_source is not None:  # video pembicara ikut dianalisis (wajah untuk crop, adegan)
            talk_source = Path(talk_source).resolve()
            speaker = next((c for c in clips if c.path == talk_source), None)
            if speaker is None:
                speaker = ingest(talk_source, log=log)[0]
                clips.append(speaker)
            speaker_clip = speaker.name
            if speaker.info.duration > TALK_MAX_SEC:
                raise RuntimeError(
                    f"Video pembicara {speaker.info.duration / 60:.0f} menit terlalu panjang untuk satu Reel "
                    f"(maks {TALK_MAX_SEC // 60} menit). Pakai \"Cari cuplikan terbaik\" di web atau "
                    "`autoreels cuplikan --input <video>` untuk memotongnya jadi beberapa cuplikan 1–3 menit.")
    progress.finish("ingest")
    log("[2/7] Analisis adegan, kualitas, crop & musik …")
    progress.start("analyze")
    with timer("analyze"):
        analysis = analyze_clips(clips, log=log, progress=progress)
        narration = None
        if talk_source is not None and narration_draft:  # video bicara, transkrip sudah diperiksa manusia
            from autoreels.narration import use_draft

            narration, _ = use_draft(narration_draft, out_dir)
            if narration.speaker_clip != speaker_clip:
                raise RuntimeError("Transkrip yang diperiksa milik video lain. Buat ulang 'Transkrip & periksa'.")
            narration_source = talk_source
            log(f"  video bicara: transkrip yang sudah diperiksa ({narration_draft}) · {len(narration.phrases)} frasa")
        elif talk_source is not None:  # Tahap 3: video bicara
            from autoreels.talk import prepare_talk

            progress.update(len(clips), len(clips) + 1, "transkripsi & pemilihan kalimat")
            narration = prepare_talk(talk_source, out_dir, speaker_clip=speaker_clip, llm=llm, model=llm_model,
                                     brief=brief, target=duration, full=talk_full, log=log)
            from autoreels.narration import proofread

            narration, _ = proofread(narration, llm, llm_model, brief=brief, log=log)
            narration_source = talk_source
            _note_talk(progress, narration)
        elif narration_draft:  # transkrip sudah diperiksa manusia di web
            from autoreels.narration import use_draft

            narration, src = use_draft(narration_draft, out_dir)
            narration_source = Path(src)
            log(f"  narasi: transkrip yang sudah diperiksa ({narration_draft}) · {len(narration.phrases)} frasa")
        elif narration_source is not None:
            from autoreels.narration import prepare_narration, proofread

            progress.update(len(clips), len(clips) + 1, "transkripsi & pembersihan narasi")
            narration = prepare_narration(narration_source, out_dir, log=log)
            progress.update(len(clips), len(clips) + 1, "koreksi transkrip (AI)")
            narration, _ = proofread(narration, llm, llm_model, brief=brief, log=log)
        if narration is not None:
            if narration.duration > (180 if talk_full else 90):
                raise RuntimeError(f"Narasi {narration.duration:.0f} dtk terlalu panjang untuk Reels (maks 90 dtk). "
                                   "Persingkat rekamannya.")
            duration = narration.duration
            job.update({"flow": "bicara" if talk_source is not None else "narasi", "narration": str(narration_source), "duration": round(duration, 2),
                        "narration_draft": narration_draft})
            if voiceover != "none":
                log("  [narasi] voice over dimatikan: narasi sudah menjadi suara utama")
                voiceover = "none"
        progress.update(len(clips), len(clips) + 1, "analisis beat musik")
        mood = style.get("music_mood_default", "upbeat")
        if no_music:
            analysis.music = None
            log("  musik: tanpa musik (pilihan pengguna)")
        else:
            analysis.music = prepare_music(mood, job_id, duration, forced=music_file, log=log)
        if analysis.music is not None:
            log(f"  musik: {Path(analysis.music.path).name} — {analysis.music.tempo:.0f} BPM")
        elif not no_music:
            log(f"  [peringatan] tidak ada musik di assets/music/{mood}/")
        (work_dir / "analysis.json").write_text(analysis.model_dump_json(indent=1), encoding="utf-8")
    progress.finish("analyze")
    if not analysis.usable_scenes():
        raise RuntimeError("Semua adegan tidak layak pakai (blur/gelap/goyang). Periksa footage.")

    log(f"[3/7] Deskripsi visual ({vision_model}) …")
    progress.start("describe")
    with timer("describe"):
        skip = {speaker_clip} if speaker_clip else set()  # video bicara: wajah pembicara tidak perlu dideskripsikan
        if skip:
            log("  video pembicara dilewati (gambarnya mengikuti ucapan); hanya b-roll yang dideskripsikan")
        descriptions = describe_scenes(analysis, llm, vision_model, log=log, progress=progress, skip_clips=skip)
        (work_dir / "descriptions.json").write_text(
            json.dumps({k: v.model_dump() for k, v in descriptions.items()}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    _note_describe(progress, descriptions)
    progress.finish("describe")
    log(f"[4–6/7] Director ({llm_model}) + validasi"
        + {True: " + Critic", "nilai": " + Critic (nilai saja)"}.get(use_critic, "") + " …")
    progress.start("direct")
    pillar_purpose = load_pillars().get(pillar, {}).get("default_purpose")
    if not purpose and pillar_purpose:  # mis. pilar "umum": konten di luar unit usaha → informasi, tanpa CTA
        purpose = pillar_purpose
        director_brief += f"\nTujuan video (purpose) WAJIB: {purpose}."
        log(f"  tujuan video: {purpose} (bawaan pilar {pillar})")
    if not purpose and (pillar == "profil" or talk_source is not None) and not promo_signal(brief, narration, brand):
        # instruksi & ucapan tidak menyinggung Brand/layanannya (mis. klip kuliah) → video informasi, tanpa CTA
        purpose = "informasi"
        director_brief += "\nTujuan video (purpose) WAJIB: informasi (bukan promosi; tanpa CTA)."
        log("  tujuan video: informasi (tidak ada ajakan/layanan Brand di instruksi maupun ucapan)")
    with timer("direct+validate"):
        dres = direct(
            llm=llm, model=llm_model, analysis=analysis, descriptions=descriptions,
            music=analysis.music, brief=director_brief, pillar=pillar, style_name=style_name, style=style,
            duration=duration, log=log, progress=progress, narration=narration,
            critic_rounds=MAX_CRITIC_ROUNDS if use_critic is True else 0 if use_critic == "nilai" else -1,
            critic_model=critic_model,
        )
        validation, revisions, critic = dres.validation, dres.revisions, dres.critic_dict()
        if no_music and validation.edl.music.mood.value != "none":
            validation.edl.music.mood = MusicMood.none
            validation = validate_edl(validation.edl, analysis, style, analysis.music, brand,
                                      load_pillars().get(pillar, {}).get("hashtags", []), descriptions)
        if hook_text or cta_text or (purpose and validation.edl.purpose.value != purpose):
            # pastikan pilihan manusia (teks hook/CTA, tujuan video) benar-benar dipakai
            edl = validation.edl.model_copy(deep=True)
            if purpose:
                from autoreels.edl import Purpose

                edl.purpose = Purpose(purpose)
            if hook_text:
                edl.hook.overlay_text = hook_text
            if cta_text and edl.cta:
                edl.cta.text = cta_text
            validation = validate_edl(edl, analysis, style, analysis.music, brand,
                                      load_pillars().get(pillar, {}).get("hashtags", []), descriptions)
            for e in validation.errors:
                log(f"  [perhatian] {e}")
        # privasi = keputusan manusia (bukan LLM): wajah/pelat disamarkan hanya bila dipilih pengguna
        if blur_faces and talk_source is not None:
            log("  [perhatian] samarkan wajah diabaikan: di video bicara wajah pembicara ikut tersamar")
            blur_faces = False
        validation.edl.privacy.blur_faces = blur_faces
        validation.edl.privacy.blur_plates = blur_plates
        validation.edl.branding.logo = logo  # watermark = keputusan manusia
        if not logo:
            log("  watermark: dimatikan pengguna")
        if voiceover in ("rekam", "gemini"):  # naskah VO ditulis setelah urutan segmen final
            from autoreels.edl import VoiceOver
            from autoreels.voiceover import write_script

            progress.update(2, 3, "menulis naskah voice over")
            log("  menulis naskah voice over …")
            lines = write_script(edl=validation.edl, descriptions=descriptions, brand=brand, brief=brief,
                                 llm=llm, model=llm_model, log=log)
            validation.edl.voiceover = VoiceOver(mode=voiceover, voice=voice, lines=lines)
    _note_director(progress, validation.edl, critic, validation.fixes)
    progress.finish("direct")
    for f in validation.fixes:
        log(f"  perbaikan otomatis: {f}")
    return _finish(job=job, edl=validation.edl, analysis=analysis, descriptions=descriptions,
                   validation=validation, style=style, brand=brand, work_dir=work_dir, out_dir=out_dir,
                   tracker=tracker, timer=timer, revisions=revisions, log=log, preview=preview,
                   progress=progress, critic=critic)


def render_from_edl(edl_path: Path, log=print, preview: bool = False, on_progress=None) -> JobResult:
    """Render ulang dari edl.json (mis. setelah teks hook/CTA diedit manusia) tanpa memanggil LLM."""
    out_dir = edl_path.parent
    job_file = out_dir / "job.json"
    if not job_file.exists():
        raise FileNotFoundError(f"job.json tidak ada di {out_dir} — render ulang butuh hasil `autoreels run`.")
    job_all = json.loads(job_file.read_text(encoding="utf-8"))
    analysis = Analysis(**job_all.pop("analysis"))
    descriptions = {k: SceneDescription(**v) for k, v in job_all.pop("descriptions", {}).items()}
    style = load_style(job_all["style"])
    brand = load_brand()
    edl = EDL.load(edl_path)
    from autoreels.preferences import record_edits

    for c in record_edits(out_dir, edl)[:5]:
        log(f"  editan dicatat untuk preferensi: {c}")
    hashtags = load_pillars().get(job_all["pillar"], {}).get("hashtags", [])
    validation = validate_edl(edl, analysis, style, analysis.music, brand, hashtags, descriptions)
    for e in validation.errors:
        log(f"  [error validasi] {e}")
    for f in validation.fixes:
        log(f"  perbaikan otomatis: {f}")
    timer = _Timer()
    job_all["created"] = f"{datetime.now():%Y-%m-%d %H:%M:%S} (render ulang)"
    work_dir = PATHS["work"] / job_all["job_id"]
    work_dir.mkdir(parents=True, exist_ok=True)
    progress = Progress(job_all["job_id"], work_dir / "progress.json", on_progress)
    progress.done_steps = {"ingest", "analyze", "describe", "direct"}  # tidak diulang
    critic_file = out_dir / "critic.json"  # penilaian Critic dari proses awal (tidak dinilai ulang)
    critic = json.loads(critic_file.read_text(encoding="utf-8")) if critic_file.exists() else None
    try:
        return _finish(job=job_all, edl=validation.edl, analysis=analysis, descriptions=descriptions,
                       validation=validation, style=style, brand=brand, work_dir=work_dir, out_dir=out_dir,
                       tracker=CostTracker(), timer=timer, revisions=0, log=log, preview=preview,
                       progress=progress, critic=critic, snapshot_ai=False)
    except BaseException:
        progress.end("gagal")
        raise
