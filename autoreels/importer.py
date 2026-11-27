"""Impor video jadi (dari video-use atau editor lain) → paket siap unggah AutoReels.

Langkah: periksa video → normalisasi (1080×1920, 30 fps, −14 LUFS) + logo + CTA (+ hook opsional)
→ caption & hashtag oleh AI (membaca transkrip video-use bila ada) → cover → Checklist Siap Unggah.
Hasil di output/<job_id>/ sama seperti `autoreels run`, sehingga bisa dijadwalkan di Tahap 6.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from autoreels.checklist import Checklist, add_video_checks
from autoreels.config import PATHS, get_settings, load_brand, load_pillars, load_prompt, load_style
from autoreels.ingest import make_job_id
from autoreels.llm import CostTracker, LLMClient
from autoreels.media import probe, run_ffmpeg
from autoreels.progress import Progress
from autoreels.render.audio_mix import PEAK_GUARD, fix_true_peak, loudnorm_filter
from autoreels.render.overlays import instagram_for, logo_file_for, logo_position, prepare_logo
from autoreels.render.reframe import OUT_H, OUT_W, blur_pad_graph
from autoreels.render.text_ass import HOOK_SIZE, TextEvent, build_ass, fit_text, font_full_name
from autoreels.validate import PLACEHOLDER_RE

IMPORT_LABELS = {
    "ingest": "Periksa video",
    "render": "Normalisasi + logo + CTA",
    "direct": "Tulis caption & hashtag (AI)",
    "checklist": "Checklist Siap Unggah",
}
CTA_SEC = 3.0
HOOK_SEC = 2.5


class CaptionResult(BaseModel):
    caption: str
    hashtags: list[str] = Field(default_factory=list)
    hook_suggestion: str | None = None


@dataclass
class ImportResult:
    job_id: str
    out_dir: Path
    reel: Path
    status: str
    checklist: Checklist
    cost_usd: float
    timings: dict[str, float] = field(default_factory=dict)
    caption: str = ""


def find_transcript(video: Path) -> str:
    """Cari transkrip dari video-use di sekitar file (master.srt lebih akurat dari takes_packed.md)."""
    for folder in (video.parent, video.parent / "edit"):
        srt = folder / "master.srt"
        if srt.exists():
            lines = [ln.strip() for ln in srt.read_text(encoding="utf-8", errors="ignore").splitlines()]
            text = " ".join(ln for ln in lines if ln and not ln.isdigit() and "-->" not in ln)
            return text[:4000]
        packed = folder / "takes_packed.md"
        if packed.exists():
            text = re.sub(r"\[\d+\.\d+-\d+\.\d+\]\s*S\d+\s*", "", packed.read_text(encoding="utf-8", errors="ignore"))
            return text[:4000]
    return ""


def _normalize_hashtags(tags: list[str], base: list[str]) -> list[str]:
    out: list[str] = []
    for tag in [*base, *tags]:
        t = "#" + re.sub(r"[^0-9a-z_]", "", tag.lower().lstrip("#"))
        if len(t) > 1 and t not in out:
            out.append(t)
    return out[:12]


def write_caption_file(caption: str, hashtags: list[str], brand: dict, path: Path) -> Path:
    wa = brand.get("whatsapp", {}).get("display", "")
    lines = [caption.strip()]
    if wa and wa not in caption:
        lines.append(f"\n📲 Info & booking: WhatsApp {wa}")
    lines.append("📍 Garut, Jawa Barat")
    lines.append("\n" + " ".join(hashtags))
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path


def import_video(
    *, video: Path, pillar: str, brief: str = "", hook_text: str | None = None, cta_text: str | None = None,
    add_logo: bool = True, add_cta: bool = True, target_duration: float | None = None,
    log=print, on_progress=None, job_id: str | None = None, engine: str = "api",
    drawn_cta: str | None = None, source: str = "import", caption: dict | None = None, informasi: bool = False,
) -> ImportResult:
    """drawn_cta: CTA yang sudah digambar di dalam video (mis. animasi Remotion) → tidak ditempel ulang, tetapi
    dihitung di checklist (CTA & nomor WhatsApp). source: label asal job ("import" | "animasi").
    caption: {"caption": str, "hashtags": [..]} yang sudah ditulis (mis. oleh Claude Code) → tanpa panggilan LLM."""
    video = Path(video).resolve()
    if not video.is_file():
        raise FileNotFoundError(f"Video tidak ditemukan: {video}")
    job_id = job_id or make_job_id(pillar)
    work_dir = PATHS["work"] / job_id
    out_dir = PATHS["output"] / job_id
    rdir = work_dir / "render"
    (rdir / "fonts").mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    progress = Progress(job_id, work_dir / "progress.json", on_progress, labels=IMPORT_LABELS)
    progress.done_steps = {"analyze", "describe"}  # tidak dipakai di alur impor
    try:
        return _import(video=video, pillar=pillar, brief=brief, hook_text=(hook_text or "").strip() or None,
                       cta_text=(cta_text or "").strip() or None, add_logo=add_logo, add_cta=add_cta,
                       target_duration=target_duration, job_id=job_id, rdir=rdir, out_dir=out_dir,
                       progress=progress, log=log, engine=engine, drawn_cta=(drawn_cta or "").strip() or None,
                       source=source, caption=caption, informasi=informasi)
    except BaseException:
        progress.end("gagal")
        raise


def _import(*, video: Path, pillar: str, brief: str, hook_text: str | None, cta_text: str | None,
            add_logo: bool, add_cta: bool, target_duration: float | None, job_id: str, rdir: Path,
            out_dir: Path, progress: Progress, log, engine: str = "api", drawn_cta: str | None = None,
            source: str = "import", caption: dict | None = None, informasi: bool = False) -> ImportResult:
    if drawn_cta:
        add_cta = False  # CTA sudah ada di video
    timings: dict[str, float] = {}
    brand = load_brand()
    pillar_cfg = load_pillars().get(pillar, {})
    style_name = pillar_cfg.get("default_style", "rental_energik")
    style = load_style(style_name)
    llm_model, _ = get_settings().models_for(engine)
    tracker = CostTracker()
    log(f"Job {job_id} (impor dari {video.name})")

    # 1. periksa
    t0 = time.perf_counter()
    progress.start("ingest", video.name)
    info = probe(video)
    if info.width == 0:
        raise RuntimeError(f"{video.name} tidak berisi stream video.")
    dur = info.duration
    log(f"  {info.display_width}×{info.display_height}, {info.fps} fps, {dur:.1f} dtk, "
        f"audio: {'ada' if info.has_audio else 'tidak ada'}")
    progress.finish("ingest")
    timings["periksa"] = round(time.perf_counter() - t0, 1)

    # 2. caption (tidak bergantung pada render; dikerjakan dulu agar urutan progress maju 1→4→5→6)
    t0 = time.perf_counter()
    progress.start("direct", f"model {llm_model}")
    transcript = find_transcript(video)
    log(f"  transkrip video-use: {'ditemukan' if transcript else 'tidak ada (caption dari instruksi saja)'}")
    guide = PATHS["config"] / "caption_guide.md"
    context = {
        "pilar": pillar,
        "instruksi": brief or "(tidak ada — simpulkan dari transkrip)",
        "transkrip": transcript or "(tidak ada)",
        "teks_hook_di_layar": hook_text,
        "brand": {"nama": brand.get("company_name"), "whatsapp": brand.get("whatsapp", {}).get("display"),
                  "instagram": instagram_for(brand, pillar),
                  "harga_sewa_per_hari": brand.get("pricing", {}).get("rental_per_day"),
                  "layanan_rental_terkonfirmasi": brand.get("rental_services") if pillar == "rental" else None},
        "keyword_seo": pillar_cfg.get("keywords") or [],
        "hashtag_dasar": pillar_cfg.get("hashtags") or [],
        "panduan_caption": guide.read_text(encoding="utf-8") if guide.exists() else None,
    }
    messages = [{"role": "system", "content": load_prompt("caption")},
                {"role": "user", "content": yaml.safe_dump(context, allow_unicode=True, sort_keys=False)}]
    try:
        if caption is not None:  # caption sudah ditulis (Claude Code) → tanpa API
            cap = CaptionResult.model_validate(caption)
            llm_model = "claude-code (manual)"
            log("  caption: dari file (tanpa API)")
        else:
            cap = LLMClient(tracker, log=log).complete_structured(messages, CaptionResult, model=llm_model,
                                                                  purpose="caption")
    except Exception as e:  # noqa: BLE001 — caption gagal tidak boleh membatalkan video
        log(f"  [peringatan] caption AI gagal ({str(e)[:100]}) → caption dasar")
        cap = CaptionResult(caption=brief or "Video terbaru dari Contoh Brand.", hashtags=[])
    hashtags = _normalize_hashtags(cap.hashtags, pillar_cfg.get("hashtags") or [])
    caption_file = write_caption_file(cap.caption, hashtags, brand, out_dir / "caption.txt")
    progress.finish("direct")
    timings["caption"] = round(time.perf_counter() - t0, 1)

    # 3. normalisasi + overlay
    t0 = time.perf_counter()
    progress.start("render", "menyiapkan teks & logo")
    cta_final = cta_text or brand.get("default_cta", {}).get(pillar, "Hubungi kami via WhatsApp!")
    events: list[TextEvent] = []
    if hook_text:
        events.append(TextEvent(0.0, min(HOOK_SEC, dur), "hook", hook_text))
    if add_cta:
        start = max(0.0, dur - CTA_SEC)
        events.append(TextEvent(start, dur, "cta", cta_final))
        wa = brand.get("whatsapp", {}).get("display")
        ig = instagram_for(brand, pillar)
        sub = " • ".join(x for x in [f"WA {wa}" if wa and wa not in cta_final else None, ig] if x)
        if sub:
            events.append(TextEvent(start + 0.25, dur, "cta_sub", sub))
    font_file = PATHS["fonts"] / (style.get("font") or brand.get("fonts", {}).get("heading"))
    shutil.copy(font_file, rdir / "fonts" / font_file.name)
    (rdir / "text.ass").write_text(build_ass(events, style, font_full_name(font_file)), encoding="utf-8")

    aspect = info.display_width / info.display_height
    if abs(aspect - OUT_W / OUT_H) < 0.02:
        geo = f"[0:v]fps=30,scale={OUT_W}:{OUT_H}:flags=lanczos,setsar=1[g]"
        log("  rasio sudah 9:16 → skala ke 1080×1920")
    else:
        geo = "[0:v]fps=30,setsar=1[v0];" + blur_pad_graph("v0", "g")
        log(f"  rasio {info.display_width}:{info.display_height} bukan 9:16 → latar blur (blur_pad)")
    graph = geo + ";[g]subtitles=text.ass:fontsdir=fonts[t]"
    inputs = ["-i", str(video)]
    vlast = "t"
    next_idx = 1
    logo_src = logo_file_for(brand, pillar)
    if add_logo and logo_src.exists():
        logo = prepare_logo(logo_src, rdir / "logo.png")
        import cv2

        lh, lw = cv2.imread(str(logo), cv2.IMREAD_UNCHANGED).shape[:2]
        x, y = logo_position(brand.get("logo", {}).get("default_position", "top_right"), lw, lh)
        inputs += ["-i", "logo.png"]
        graph += f";[{next_idx}:v]format=rgba[lg];[t][lg]overlay={x}:{y}:format=auto[vl]"
        vlast = "vl"
        next_idx += 1
    graph += f";[{vlast}]format=yuv420p[v]"

    if info.has_audio:
        progress.update(1, 3, "mengukur loudness")
        norm = loudnorm_filter(["-i", str(video)])
        graph += f";[0:a]{norm},aresample=48000,{PEAK_GUARD}[a]"  # batasi puncak sebelum encoding AAC
        amap = "[a]"
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        amap = f"{next_idx}:a"
        log("  [peringatan] video tanpa audio → ditambah track senyap")
    progress.update(2, 3, "render 1080×1920")
    reel = out_dir / "reel.mp4"
    run_ffmpeg([*inputs, "-filter_complex", graph, "-map", "[v]", "-map", amap,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                "-t", f"{dur:.3f}", "-movflags", "+faststart", str(reel)], cwd=rdir)
    fix_true_peak(reel, log=log)  # tanpa PCM: hanya memperingatkan; checklist yang menilai
    cover = out_dir / "cover.jpg"
    run_ffmpeg(["-ss", f"{min(1.0, dur / 2):.2f}", "-i", str(reel), "-frames:v", "1", "-q:v", "2", str(cover)])
    progress.finish("render")
    timings["render"] = round(time.perf_counter() - t0, 1)

    # 4. checklist
    t0 = time.perf_counter()
    progress.start("checklist", "cek video, teks, brand")
    c = Checklist()
    add_video_checks(c, reel, target_duration)
    if hook_text:
        lines, size = fit_text(hook_text, HOOK_SIZE, 14)
        c.add("Hook benar", "Teks hook muncul di detik 0", True, hook_text)
        c.add("Hook benar", "Teks hook cukup besar (≥ 90 px, ≤ 2 baris)", size >= 90 and len(lines) <= 2,
              f"{size} px, {len(lines)} baris")
    else:
        c.add("Hook benar", "Hook dari editor sumber", True, "cek manual 3 detik pertama", required=False)
    c.add("Style benar", "Style mengikuti editor sumber", True, "tidak dicek otomatis (video impor)", required=False)
    texts = [cap.caption, hook_text or "", cta_final if add_cta else "", drawn_cta or ""]
    ph = [t for t in texts if PLACEHOLDER_RE.search(t)]
    c.add("Teks & brand", "Tanpa placeholder tersisa", not ph, "; ".join(ph) or "bersih")
    wa = brand.get("whatsapp", {}).get("display", "")
    on_screen = [e.text for e in events] + ([drawn_cta] if drawn_cta else [])
    if informasi:  # video informasi (mis. pilar umum): tanpa CTA jualan, sama seperti pipeline utama
        c.add("Teks & brand", "Video informasi: tanpa CTA jualan", not (add_cta or drawn_cta),
              "penutup tanpa ajakan booking (tujuan: informasi)")
    else:
        c.add("Teks & brand", "CTA tampil", add_cta or bool(drawn_cta),
              drawn_cta or (cta_final if add_cta else "dimatikan"))
        c.add("Teks & brand", "Nomor WhatsApp di layar", any(wa and wa in t for t in on_screen), wa)
    if source == "animasi" and not add_logo:  # animasi: brand digambar di dalam video, tanpa watermark (keputusan pemilik)
        c.add("Teks & brand", "Logo tampil", True, "tanpa watermark (brand di dalam animasi)", required=False)
    else:
        c.add("Teks & brand", "Logo tampil", add_logo and logo_src.exists(), "ya" if add_logo else "dimatikan")
    c.add("Siap posting", "Caption + hashtag tersedia", bool(cap.caption.strip()) and bool(hashtags),
          f"{len(hashtags)} hashtag")
    c.add("Siap posting", "Cover tersedia", cover.exists(), cover.name)
    progress.finish("checklist")
    timings["checklist"] = round(time.perf_counter() - t0, 1)

    # laporan & metadata
    job = {"job_id": job_id, "created": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "source": source,
           "input": str(video), "pillar": pillar, "brief": brief, "style": style_name,
           "hook_text": hook_text, "cta_text": drawn_cta or (cta_final if add_cta else None), "duration": round(dur, 2),
           "engine": engine, "models": {"caption": llm_model}, "hook_suggestion": cap.hook_suggestion}
    (out_dir / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "status.txt").write_text(c.status + "\n", encoding="utf-8")
    report = [
        f"# Laporan Job `{job_id}` (impor)", "",
        f"**Status:** {'✅ SIAP UNGGAH' if c.status == 'siap_unggah' else '⚠️ PERLU TINJAU'}", "",
        "## Ringkasan",
        f"- Sumber: `{video}`",
        f"- Pilar: {pillar} · gaya teks: {style_name}",
        f"- Durasi: {dur:.1f} dtk · asli {info.display_width}×{info.display_height} @ {info.fps} fps",
        f"- Hook di layar: {hook_text or '(dari editor sumber)'}",
        f"- CTA: {drawn_cta or (cta_final if add_cta else '(dimatikan)')}",
        f"- Saran hook dari AI: {cap.hook_suggestion or '-'}",
        f"- Transkrip video-use: {'dipakai' if transcript else 'tidak ada'}", "",
        "## Checklist Siap Unggah", c.markdown(), "",
        "## Waktu proses (detik)", *[f"- {k}: {v}" for k, v in timings.items()], "",
        "## Biaya API", tracker.summary_markdown(), "",
    ]
    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    from autoreels.pipeline import write_result

    write_result(out_dir, c, {"total_duration": round(dur, 2), "segments": None,
                              "hook_duration": HOOK_SEC if hook_text else None, "beat_accuracy": None,
                              "cost_usd": round(tracker.total_cost, 5),
                              "process_sec": round(sum(timings.values()), 1)})
    progress.end("selesai")
    return ImportResult(job_id, out_dir, reel, c.status, c, tracker.total_cost, timings,
                        caption_file.read_text(encoding="utf-8"))
