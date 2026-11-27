"""Antarmuka baris perintah AutoReels."""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from autoreels import __version__
from autoreels.config import list_styles
from autoreels.edl import EDL, Pillar

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(
    help="AutoReels — ubah video mentah menjadi Instagram Reels siap unggah.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _log(msg: str) -> None:
    console.print(msg, markup=False, highlight=False)


def _not_ready(stage: str) -> None:
    console.print(f"[yellow]Perintah ini belum diimplementasikan (dijadwalkan di {stage}).[/yellow]")
    raise typer.Exit(code=1)


def _progress_bar():
    """Progress bar real-time: langkah aktif, bar, persen, waktu berjalan, detail."""
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    return Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold cyan]{task.description:<38}"),
        BarColumn(bar_width=34, complete_style="green", finished_style="bold green"),
        TextColumn("[bold]{task.percentage:>5.1f}%"),
        TimeElapsedColumn(),
        TextColumn("[dim]{task.fields[detail]}"),
        console=console,
        refresh_per_second=8,
    )


def _run_with_progress(fn, **kwargs):
    from autoreels.joblock import JobBusyError, job_lock

    try:
        with job_lock(f"terminal: autoreels {' '.join(sys.argv[1:2])}"):
            return _run_locked(fn, **kwargs)
    except JobBusyError as e:
        console.print(f"[yellow]{e}[/yellow]")
        console.print("Tunggu sampai selesai (pantau dengan [bold]autoreels status[/bold]) agar CPU/GPU tidak berebut.")
        raise typer.Exit(code=2) from None


def _run_locked(fn, **kwargs):
    with _progress_bar() as bar:
        task = bar.add_task("Menyiapkan …", total=100, detail="")

        def on_progress(s: dict) -> None:
            bar.update(task, completed=s["percent"],
                       description=f"[{s['step_index']}/{s['steps_total']}] {s['step_label']}",
                       detail=s["detail"][:60])

        def log(msg: str) -> None:
            bar.console.print(msg, markup=False, highlight=False)

        result = fn(log=log, on_progress=on_progress, **kwargs)
        bar.update(task, completed=100, description="Selesai", detail="")
    return result


def _summary(result) -> None:
    ok = result.status == "siap_unggah"
    console.rule("[green]SIAP UNGGAH[/green]" if ok else "[yellow]PERLU TINJAU[/yellow]")
    console.print(f"Video   : {result.reel}")
    console.print(f"Laporan : {result.out_dir / 'report.md'}")
    console.print(f"Caption : {result.out_dir / 'caption.txt'}")
    console.print(f"Biaya API ≈ ${result.cost_usd:.4f} · waktu {sum(result.timings.values()):.0f} dtk")
    for item in result.checklist.failed():
        console.print(f"  [red]✗[/red] {item.group} — {item.name}: {item.detail}")


@app.command()
def version() -> None:
    """Tampilkan versi AutoReels."""
    console.print(f"AutoReels {__version__}")


@app.command()
def run(
    input: Path = typer.Option(None, "--input", "-i", help="Folder atau file video mentah (b-roll)."),
    pillar: Pillar = typer.Option(..., "--pillar", "-p", help="Pilar konten."),
    brief: str = typer.Option(..., "--brief", "-b", help="Instruksi edit dalam bahasa Indonesia."),
    style: str = typer.Option("rental_energik", "--style", "-s", help="Nama style preset."),
    duration: int = typer.Option(20, "--duration", "-d", min=8, max=90, help="Target durasi Reel (detik)."),
    music: Path = typer.Option(None, "--music", "-m", help="Paksa file musik tertentu (opsional)."),
    preview: bool = typer.Option(False, "--preview", help="Render cepat kualitas rendah."),
    hook: str = typer.Option(None, "--hook", help="Paksa teks hook (kosong = dipilih AI)."),
    cta: str = typer.Option(None, "--cta", help="Paksa teks CTA (kosong = dipilih AI)."),
    voiceover: str = typer.Option("none", "--voiceover", help="none | rekam (suara sendiri, rekam di web) | gemini (suara AI)."),
    voice: str = typer.Option("Puck", "--voice", help="Suara AI Gemini: Puck, Kore, Zephyr, Charon, Aoede, Fenrir."),
    engine: str = typer.Option("api", "--engine", help="api (default) | local (model Ollama di laptop, uji coba)."),
    clip: list[str] = typer.Option(None, "--clip", help="Hanya proses klip ini (nama file di folder input; boleh diulang)."),
    blur_wajah: bool = typer.Option(False, "--blur-wajah", help="Samarkan wajah (mis. pelanggan tanpa izin)."),
    blur_pelat: bool = typer.Option(False, "--blur-pelat", help="Samarkan pelat nomor kendaraan."),
    narasi: Path = typer.Option(None, "--narasi", help="Alur 'narasi dulu': file rekaman narasi (audio/video). "
                                "Durasi mengikuti narasi; b-roll dipilih per frasa; subtitle karaoke."),
    tanpa_critic: bool = typer.Option(False, "--tanpa-critic", help="Lewati Critic (hemat biaya / pembanding)."),
    tanpa_logo: bool = typer.Option(False, "--tanpa-watermark", "--tanpa-logo",
                                    help="Tanpa watermark (logo kecil di pojok video)."),
    utuh: bool = typer.Option(False, "--utuh", help="Video bicara utuh: durasi ikut panjang ucapan (maks 3 menit)."),
    tanpa_musik: bool = typer.Option(False, "--tanpa-musik", help="Tanpa musik latar (hanya suara / senyap)."),
    tujuan: str = typer.Option(None, "--tujuan", help="promosi | informasi (kosong = dipilih AI dari instruksi)."),
    bicara: Path = typer.Option(None, "--bicara", help="Video bicara (Tahap 3): kalimat terbaik jadi Reel "
                                "bersubtitle; --input = folder b-roll (opsional)."),
) -> None:
    """Jalankan pipeline lengkap: ingest -> analyze -> describe -> direct -> render -> checklist."""
    from autoreels.pipeline import run_pipeline

    if voiceover not in ("none", "rekam", "gemini"):
        raise typer.BadParameter("--voiceover harus none, rekam, atau gemini")
    if engine not in ("api", "local"):
        raise typer.BadParameter("--engine harus api atau local")
    if tujuan not in (None, 'promosi', 'informasi'):
        raise typer.BadParameter('--tujuan harus promosi atau informasi')
    if bicara is not None and narasi is not None:
        raise typer.BadParameter("pilih salah satu: --bicara atau --narasi")
    if input is None:
        if bicara is None:
            raise typer.BadParameter("--input wajib diisi")
        input = bicara
    result = _run_with_progress(run_pipeline, input_path=input, pillar=pillar.value, brief=brief,
                                style_name=style, duration=duration, music_file=music, preview=preview,
                                hook_text=hook, cta_text=cta, voiceover=voiceover, voice=voice,
                                engine=engine, clips=clip or None, blur_faces=blur_wajah, blur_plates=blur_pelat,
                                narration=narasi, critic=not tanpa_critic, talk=bicara, purpose=tujuan, no_music=tanpa_musik,
                                logo=not tanpa_logo, talk_full=utuh)
    _summary(result)


@app.command()
def status(job: str = typer.Option(None, "--job", help="ID job (default: job terbaru).")) -> None:
    """Pantau progress job secara real-time (bisa dari terminal lain)."""
    import json
    import time

    from autoreels.config import PATHS

    def latest() -> Path | None:
        files = sorted(PATHS["work"].glob("*/progress.json"), key=lambda p: p.stat().st_mtime)
        return files[-1] if files else None

    pfile = PATHS["work"] / job / "progress.json" if job else latest()
    if pfile is None:
        console.print("[yellow]Belum ada job. Menunggu job baru dimulai …[/yellow]")
        while pfile is None:
            time.sleep(1)
            pfile = latest()
    console.print(f"Memantau job [bold]{pfile.parent.name}[/bold] (Ctrl+C untuk berhenti memantau)")
    seen_running = False
    with _progress_bar() as bar:
        task = bar.add_task("…", total=100, detail="")
        while True:
            if not job:  # ikut pindah bila ada job yang lebih baru
                newest = latest()
                if newest and newest != pfile:
                    pfile = newest
                    bar.console.print(f"→ beralih ke job terbaru [bold]{pfile.parent.name}[/bold]")
            try:
                s = json.loads(pfile.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                time.sleep(0.5)
                continue
            stale = time.time() - pfile.stat().st_mtime > 900
            bar.update(task, completed=s["percent"],
                       description=f"[{s['step_index']}/{s['steps_total']}] {s['step_label']}",
                       detail=("(tidak aktif >15 mnt) " if stale else "") + s["detail"][:60])
            if s["state"] == "berjalan":
                seen_running = True
            elif seen_running or job:
                break
            else:  # job terakhir sudah selesai sebelum dipantau → tunggu job baru
                bar.update(task, description="Menunggu job baru …", detail=f"terakhir: {s['state']}")
            time.sleep(0.5)
    state = s["state"]
    color = "green" if state == "selesai" else "red"
    console.print(f"Status: [{color}]{state}[/{color}] · {s['elapsed_sec']:.0f} dtk")


@app.command()
def studio(
    port: int = typer.Option(8000, "--port", help="Port lokal."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Jangan buka browser otomatis."),
    lan: bool = typer.Option(False, "--lan", help="Bisa dibuka dari HP di Wi-Fi yang sama (pakai PIN)."),
) -> None:
    """Jalankan AutoReels Studio (tampilan web) di http://127.0.0.1:8000."""
    from autoreels.server import serve

    serve(port=port, open_browser=not no_browser, lan=lan)


@app.command()
def transcribe(
    input: Path = typer.Option(..., "--input", "-i", help="File audio/video berisi ucapan."),
    model: str = typer.Option(None, "--model", help="Model faster-whisper: tiny|base|small|medium (default .env)."),
    demo: bool = typer.Option(False, "--demo", help="Buat video contoh: audio bersih + subtitle karaoke."),
) -> None:
    """Transkrip ucapan per kata (CPU), tandai kata pengisi & jeda panjang, hitung hasil pembersihan (Tahap 3)."""
    from autoreels.analyze.transcribe import cleanup_stats, keep_ranges, remap_words
    from autoreels.analyze.transcribe import transcribe as do_transcribe
    from autoreels.config import PATHS

    tr = do_transcribe(input, model_name=model, log=console.print)
    ranges = keep_ranges(tr)
    st = cleanup_stats(tr, ranges)
    out_dir = PATHS["work"] / "_uji" / input.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    # transkrip mudah dibaca: [pengisi] ditandai, jeda panjang jadi ‖
    pauses = {round(a, 3) for a, _ in tr.pauses()}
    marked = []
    for w in tr.words:
        marked.append(f"[{w.text}]" if w.filler else (w.text + (" ‖" if round(w.end, 3) in pauses else "")))
    (out_dir / "transkrip.txt").write_text(" ".join(marked) + "\n", encoding="utf-8")
    console.rule(f"Transkrip {input.name} — model {tr.model}, bahasa {tr.language}")
    console.print(" ".join(marked), markup=False, highlight=False)
    console.rule()
    console.print(f"Durasi {st['duration']:.1f} dtk → bersih {st['kept']:.1f} dtk (dibuang {st['removed']:.1f} dtk) · "
                  f"{st['words']} kata · {st['fillers']} kata pengisi · {st['long_pauses']} jeda > 0,6 dtk")
    doubtful = [w.text for w in tr.words if w.prob < 0.5 and not w.filler]
    if doubtful:
        console.print(f"Kata yang kurang yakin (periksa): {', '.join(doubtful[:20])}", markup=False)
    console.print(f"Transkrip disimpan: {out_dir / 'transkrip.txt'}")
    if demo and ranges:
        from autoreels.render.audio_mix import cut_audio
        from autoreels.render.karaoke import render_karaoke_preview

        clean = cut_audio(input, ranges, out_dir / "audio_bersih.wav")
        video = render_karaoke_preview(clean, remap_words(tr, ranges), out_dir / "demo_karaoke.mp4", st["kept"])
        console.print(f"Video contoh karaoke: {video}")


@app.command(name="import")
def import_cmd(
    video: Path = typer.Option(..., "--video", "-v", help="Video jadi (mis. dari video-use: <folder>/edit/final.mp4)."),
    pillar: Pillar = typer.Option(..., "--pillar", "-p", help="Pilar konten."),
    brief: str = typer.Option("", "--brief", "-b", help="Isi/tujuan video (membantu AI menulis caption)."),
    hook: str = typer.Option(None, "--hook", help="Tempel teks hook di 0–2,5 dtk (kosong = tidak ditempel)."),
    cta: str = typer.Option(None, "--cta", help="Teks CTA (kosong = CTA default brand)."),
    no_logo: bool = typer.Option(False, "--no-logo", help="Jangan tempel logo."),
    no_cta: bool = typer.Option(False, "--no-cta", help="Jangan tempel CTA di akhir video."),
    engine: str = typer.Option("api", "--engine", help="api (default) | local (model Ollama di laptop, uji coba)."),
) -> None:
    """Impor video jadi (video-use/editor lain) → normalisasi, logo, CTA, caption, checklist."""
    from autoreels.importer import import_video

    result = _run_with_progress(import_video, video=video, pillar=pillar.value, brief=brief,
                                hook_text=hook, cta_text=cta, add_logo=not no_logo, add_cta=not no_cta,
                                engine=engine)
    _summary(result)


@app.command()
def analyze(input: Path = typer.Option(..., "--input", "-i", help="Folder atau file video.")) -> None:
    """Analisis footage saja (adegan & kualitas), tanpa LLM — untuk mengecek footage."""
    from autoreels.analyze import analyze_clips
    from autoreels.ingest import ingest

    analysis = analyze_clips(ingest(input, log=_log), log=_log)
    for s in analysis.scenes:
        flag = "OK " if s.usable else "BURUK"
        _log(f"{flag} {s.scene_id:7} {s.source_file[:45]:45} {s.start:6.2f}–{s.end:6.2f} "
             f"tajam={s.sharpness:6.1f} terang={s.brightness:5.1f} goyang={s.shake:4.1f} "
             f"{'; '.join(s.reasons)}")


@app.command()
def render(
    edl: Path = typer.Option(..., "--edl", help="Path output/<job_id>/edl.json."),
    preview: bool = typer.Option(False, "--preview", help="Render cepat kualitas rendah."),
) -> None:
    """Render ulang Reel dari edl.json saja (tanpa LLM), mis. setelah mengedit teks hook/CTA."""
    from autoreels.pipeline import render_from_edl

    _summary(_run_with_progress(render_from_edl, edl_path=edl, preview=preview))


@app.command()
def validate(edl: Path = typer.Argument(..., help="Path edl.json.")) -> None:
    """Validasi file EDL terhadap skema."""
    data = EDL.load(edl)
    console.print(
        f"[green]EDL valid[/green] — pilar {data.pillar.value}, {len(data.segments)} segmen, "
        f"durasi ~{data.total_duration:.1f} dtk (target {data.target_duration_sec} dtk)"
    )


@app.command()
def styles() -> None:
    """Daftar style preset yang tersedia."""
    for name in list_styles():
        console.print(f"- {name}")


@app.command()
def prepare(
    input: Path = typer.Option(None, "--input", "-i", help="Folder atau file video mentah."),
    pillar: Pillar = typer.Option(None, "--pillar", "-p", help="Pilar konten."),
    brief: str = typer.Option("", "--brief", "-b", help="Instruksi edit dalam bahasa Indonesia."),
    style: str = typer.Option("rental_energik", "--style", "-s", help="Nama style preset."),
    duration: int = typer.Option(20, "--duration", "-d", min=8, max=90, help="Target durasi (detik)."),
    deskripsi: str = typer.Option("claude", "--deskripsi", help="claude (lembar kontak untuk dilihat Claude) | api."),
    narasi: Path = typer.Option(None, "--narasi", help="Alur 'narasi dulu': file rekaman narasi."),
    clip: list[str] = typer.Option(None, "--clip", help="Hanya proses klip ini (boleh diulang)."),
    hook: str = typer.Option(None, "--hook", help="Paksa teks hook."),
    cta: str = typer.Option(None, "--cta", help="Paksa teks CTA."),
    blur_wajah: bool = typer.Option(False, "--blur-wajah", help="Samarkan wajah."),
    blur_pelat: bool = typer.Option(False, "--blur-pelat", help="Samarkan pelat nomor."),
    job: str = typer.Option(None, "--job", help="Dengan --konteks: job yang sudah disiapkan."),
    konteks: bool = typer.Option(False, "--konteks", help="Tulis ulang konteks.md (setelah deskripsi.json diisi)."),
) -> None:
    """Mode Claude sebagai sutradara (skill /racik-sutradara): siapkan bahan + konteks Director, tanpa Director API."""
    from autoreels import manual

    if konteks:
        if not job:
            raise typer.BadParameter("--konteks butuh --job")
        console.print(f"Konteks: {manual.build_context(job)}")
        return
    if input is None or pillar is None:
        raise typer.BadParameter("--input dan --pillar wajib diisi")
    if deskripsi not in ("claude", "api"):
        raise typer.BadParameter("--deskripsi harus claude atau api")
    from autoreels.joblock import JobBusyError, job_lock

    try:
        with job_lock("terminal: autoreels prepare"):
            job_id = manual.prepare(input_path=input, pillar=pillar.value, brief=brief, style_name=style,
                                    duration=duration, describe=deskripsi, clips=clip or None, narration=narasi,
                                    hook_text=hook, cta_text=cta, blur_faces=blur_wajah, blur_plates=blur_pelat,
                                    log=lambda m: console.print(m, markup=False, highlight=False))
    except JobBusyError as e:
        console.print(f"[yellow]{e}[/yellow]")
        raise typer.Exit(code=2) from None
    d = manual.manual_dir(job_id)
    console.rule(f"Siap: {job_id}")
    console.print(f"Folder kerja Claude: {d}")
    if deskripsi == "claude":
        console.print("Berikutnya: lihat lembar_*.jpg, isi deskripsi.json, lalu "
                      f"`autoreels prepare --job {job_id} --konteks`")
    else:
        console.print(f"Berikutnya: baca konteks.md, tulis edl.json, lalu `autoreels finish --job {job_id}`")


@app.command()
def finish(
    job: str = typer.Option(..., "--job", help="ID job dari `autoreels prepare`."),
    edl: Path = typer.Option(None, "--edl", help="File EDL (default: work/<job>/sutradara/edl.json)."),
    critic: Path = typer.Option(None, "--critic", help="Penilaian rubrik tulisan Claude (JSON format Critic)."),
    cek: bool = typer.Option(False, "--cek", help="Hanya validasi, tanpa render."),
    preview: bool = typer.Option(False, "--preview", help="Render cepat kualitas rendah."),
    paksa: bool = typer.Option(False, "--paksa", help="Render walau masih ada error validasi."),
) -> None:
    """Mode Claude sebagai sutradara: validasi EDL tulisan Claude → render → Checklist Siap Unggah."""
    from autoreels import manual

    if cek:
        r = manual.check(job, edl)
        for f in r.fixes:
            console.print(f"  perbaikan otomatis: {f}", markup=False)
        for w in r.warnings:
            console.print(f"  peringatan: {w}", markup=False)
        for e in r.errors:
            console.print(f"  [red]✗[/red] {e}", highlight=False)
        console.print("[green]EDL lolos validasi[/green]" if r.ok else f"[red]{len(r.errors)} error[/red]")
        console.print(f"Durasi {r.stats.get('total_duration')} dtk · {r.stats.get('segments')} segmen · "
                      f"hook {r.stats.get('hook_duration')} dtk · beat {r.stats.get('beat_accuracy')}")
        raise typer.Exit(code=0 if r.ok else 1)
    try:
        result = _run_with_progress(manual.finish, job_id=job, edl_file=edl, critic_file=critic, preview=preview,
                                    force=paksa)
    except manual.ManualEdlError as e:
        for err in e.errors:
            console.print(f"  [red]✗[/red] {err}", highlight=False)
        console.print("EDL belum dirender. Perbaiki edl.json lalu jalankan lagi.")
        raise typer.Exit(code=1) from None
    _summary(result)


@app.command()
def cuplikan(
    input: Path = typer.Option(..., "--input", "-i", help="Video bicara panjang (podcast, kuliah, wawancara)."),
    jumlah: int = typer.Option(0, "--jumlah", "-n", min=0, max=8, help="Jumlah kandidat cuplikan (0 = semua yang layak, maks 20)."),
    brief: str = typer.Option("", "--brief", "-b", help="Topik yang dicari / konteks video (opsional)."),
    pilih: str = typer.Option(None, "--pilih", help="Nomor cuplikan yang dipotong, mis. '1,3' (atau 'semua')."),
    buat: bool = typer.Option(False, "--buat", help="Setelah dipotong, langsung buat Reel tiap cuplikan."),
    pillar: Pillar = typer.Option(Pillar.umum, "--pillar", "-p", help="Pilar untuk --buat."),
    style: str = typer.Option(None, "--style", "-s", help="Gaya untuk --buat (kosong = bawaan pilar)."),
    engine: str = typer.Option("api", "--engine", help="api | local."),
) -> None:
    """Cari cuplikan 1–3 menit terbaik dari video bicara panjang → potong → (opsional) jadikan Reel masing-masing."""
    from autoreels import config_editor as ce
    from autoreels.config import PATHS, get_settings, load_pillars
    from autoreels.highlights import cut_candidate, find_highlights, load_candidates, save_candidates, slugify
    from autoreels.llm import CostTracker, LLMClient

    store = PATHS["work"] / "_cuplikan" / f"cli-{slugify(input.stem)}" / "candidates.json"
    if store.exists() and pilih:
        _, cands = load_candidates(store)
    else:
        settings = get_settings()
        tracker = CostTracker()
        cands = _run_with_progress(
            lambda log, on_progress, **_: find_highlights(
                input, llm=LLMClient(tracker, log=log), model=settings.models_for(engine)[0],
                brief=brief, n=jumlah, log=log),
        )
        save_candidates(store, input, cands)
        console.print(f"Biaya AI ≈ ${tracker.total_cost:.4f}")
    for c in cands:
        console.print(f"[bold]{c.rank}. {c.title}[/bold]  ({int(c.start // 60)}:{int(c.start % 60):02d}–"
                      f"{int(c.end // 60)}:{int(c.end % 60):02d}, {c.duration:.0f} dtk, skor {c.score}/5)")
        console.print(f"   {c.reason}", highlight=False)
    if not pilih:
        console.print("\nPotong & buat Reel: autoreels cuplikan --input <video> --pilih 1,3 --buat")
        return
    ranks = {c.rank for c in cands} if pilih == "semua" else {int(x) for x in pilih.split(",") if x.strip().isdigit()}
    chosen = [c for c in cands if c.rank in ranks]
    out_dir = input.parent / "cuplikan"
    clips = [cut_candidate(input, c, out_dir) for c in chosen]
    for c, clip in zip(chosen, clips):
        console.print(f"Dipotong: {clip}")
    if not buat:
        return
    from autoreels.pipeline import run_pipeline

    style = style or load_pillars().get(pillar.value, {}).get("default_style", ce.DEFAULT_STYLE[pillar.value])
    for c, clip in zip(chosen, clips):
        console.rule(f"Reel dari cuplikan {c.rank}: {c.title}")
        result = _run_with_progress(run_pipeline, input_path=clip, pillar=pillar.value,
                                    brief=(brief + f"\nCuplikan: {c.title}.").strip(), style_name=style, duration=40,
                                    engine=engine, talk=clip)
        _summary(result)


@app.command()
def preferensi(
    rangkum: bool = typer.Option(False, "--rangkum", help="Rangkum editan semua job → config/preferensi.md "
                                 "(1 panggilan LLM murah)."),
) -> None:
    """Belajar dari editan Anda: tampilkan status/isi preferensi, atau rangkum ulang dengan --rangkum."""
    from autoreels import preferences as pf

    if rangkum:
        try:
            pf.summarize(log=console.print)
        except ValueError as e:
            console.print(f"[yellow]{e}[/yellow]")
            raise typer.Exit(1)
    st = pf.status()
    console.print(f"Job yang diedit: {st['edited_jobs']} · belum dirangkum: {st['new_since_summary']} · "
                  f"rangkuman terakhir: {st['last_summarized'] or 'belum pernah'}")
    console.print(st["text"] or "(config/preferensi.md belum ada)")


@app.command(name="eval")
def eval_cmd(
    jalankan: bool = typer.Option(False, "--jalankan", help="Proses set uji di eval/testset/manifest.csv dulu "
                                  "(memakai biaya AI), lalu rangkum hasilnya."),
    sejak: str = typer.Option(None, "--sejak", help="Rangkum job sejak tanggal ini (YYYY-MM-DD)."),
    engine: list[str] = typer.Option(None, "--engine", help="--jalankan: mesin yang diuji (boleh diulang: api, local)."),
    bandingkan_critic: bool = typer.Option(False, "--bandingkan-critic",
                                           help="--jalankan: proses tiap set dengan DAN tanpa Critic."),
    set_id: list[str] = typer.Option(None, "--set", help="--jalankan: hanya set_id ini (boleh diulang)."),
    model: list[str] = typer.Option(None, "--model", help="--jalankan: model Director yang dibandingkan "
                                    "(boleh diulang), mis. runcrate/openai/gpt-oss-120b."),
    penilai: str = typer.Option(None, "--penilai", help="--jalankan: model Critic tetap untuk semua job "
                                "(agar skor antar-model adil)."),
    preview: bool = typer.Option(False, "--preview", help="--jalankan: render cepat kualitas rendah."),
) -> None:
    """Evaluasi: rangkum job (waktu, biaya, durasi, hook, beat, skor Critic, revisi, error) → eval/report.md."""
    from autoreels import evaluate

    job_ids = None
    if jalankan:
        engines = engine or ["api"]
        bad_engine = [e for e in engines if e not in ("api", "local")]
        if bad_engine:
            raise typer.BadParameter(f"--engine tidak dikenal: {', '.join(bad_engine)}")
        modes = ["nilai", True] if bandingkan_critic else [True]  # baseline: Critic menilai tanpa revisi
        rows = [r for r in evaluate.read_manifest() if not set_id or r["set_id"] in set_id]
        n_models = len(model) if model else 1
        console.print(f"Set uji: {len(rows)} · mesin: {', '.join(engines)} · model: {', '.join(model or ['bawaan'])} · "
                      f"Critic: {'nilai saja & revisi' if bandingkan_critic else 'revisi'} → "
                      f"{len(rows) * len(engines) * n_models * len(modes)} job")
        job_ids = _run_with_progress(evaluate.run_testset, engines=engines, critic_modes=modes, preview=preview,
                                     only=set_id or None, models=model or None, judge=penilai)
    jobs, failed = evaluate.collect(since=sejak, job_ids=job_ids)
    title = "set uji" if jalankan else (f"job sejak {sejak}" if sejak else "semua job")
    report, csv_path = evaluate.write_outputs(jobs, failed, title)
    console.print(f"{len(jobs)} job dirangkum ({len(failed)} gagal).")
    console.print(f"Laporan : {report}")
    console.print(f"Data CSV: {csv_path}")


animasi_app = typer.Typer(help="Video animasi 2D flat (Remotion), kodenya ditulis Claude Code (skill racik-animasi).",
                          no_args_is_help=True)
app.add_typer(animasi_app, name="animasi")


def _parse_ranges(text: str, start: float | None, end: float | None) -> list[tuple[float, float | None]] | None:
    if text.strip():
        out = []
        for part in text.split(","):
            a, _, b = part.strip().partition("-")
            out.append((float(a), float(b) if b.strip() else None))
        return out
    if start is not None or end is not None:
        return [(start or 0.0, end)]
    return None


@animasi_app.command("prepare")
def animasi_prepare(
    suara: Path = typer.Option(..., "--suara", "-s", help="Rekaman suara (narasi) untuk video ini."),
    nama: str = typer.Option(..., "--nama", "-n", help="Nama video, huruf kecil + '-' (mis. rental-garut)."),
    pillar: Pillar = typer.Option(..., "--pillar", "-p", help="Pilar konten."),
    brief: str = typer.Option("", "--brief", "-b", help="Isi/tujuan video."),
    mood: str = typer.Option("claude", "--mood", help="claude (musik orisinal dari partitur Claude, default) | "
                             "mood folder assets/music/ | none."),
    musik_db: float = typer.Option(-20.0, "--musik-db", help="Volume musik di bawah narasi (dB)."),
    mulai: float = typer.Option(None, "--mulai", help="Potong rekaman mulai detik ini (mis. bagian podcast)."),
    sampai: float = typer.Option(None, "--sampai", help="Potong rekaman sampai detik ini."),
    rentang: str = typer.Option("", "--rentang", help="Beberapa bagian disambung berurutan, mis. "
                                "'2615.8-2621.9,2518.7-2547' (detik; urutan boleh diubah)."),
    gaya: str = typer.Option("racik-flat", "--gaya", help="Gaya animasi (lihat `autoreels animasi gaya`)."),
    dimensi: str = typer.Option("2d", "--dimensi", help="2d (kit 2D) | 3d (dunia three.js + teks 2D, butuh GPU)."),
) -> None:
    """Rekaman suara → narasi bersih + timing per kata → animasi/public/<nama>/data.json."""
    from autoreels import animasi

    out = animasi.prepare(voice=suara, name=nama, pillar=pillar.value, brief=brief, mood=mood,
                          music_db=musik_db, ranges=_parse_ranges(rentang, mulai, sampai), gaya=gaya,
                          dimensi=dimensi, log=_log)
    console.print(f"Data: {out}")
    console.print(f"Naskah per frasa: {animasi.work_dir(nama) / 'naskah.txt'}")


@animasi_app.command("footage")
def animasi_footage(
    input_path: Path = typer.Option(..., "--input", "-i", help="Folder/file footage mentah."),
    nama: str = typer.Option(..., "--nama", "-n", help="Nama video, huruf kecil + '-'."),
    pillar: Pillar = typer.Option(..., "--pillar", "-p", help="Pilar konten."),
    brief: str = typer.Option("", "--brief", "-b", help="Isi/tujuan video."),
    style: str = typer.Option("rental_energik", "--style", help="Style preset config/styles/*.yaml."),
    duration: float = typer.Option(20.0, "--duration", "-d", help="Durasi target (detik)."),
    clip: list[str] = typer.Option(None, "--clip", help="Hanya klip ini (boleh diulang)."),
    hook: str = typer.Option(None, "--hook", help="Teks hook dari pengguna."),
    cta: str = typer.Option(None, "--cta", help="Teks CTA dari pengguna."),
) -> None:
    """Buat video dengan Claude + Remotion: footage → klip kerja + data.json (lalu jalankan Claude Code di web)."""
    from autoreels import footage_remotion

    out = footage_remotion.prepare(nama=nama, input_path=input_path, pillar=pillar.value, brief=brief,
                                   style_name=style, duration=duration, clips=clip or None, hook_text=hook,
                                   cta_text=cta, log=_log)
    console.print(f"Data: {out}")


@animasi_app.command("stills")
def animasi_stills(
    nama: str = typer.Option(..., "--nama", "-n", help="Nama video."),
    detik: str = typer.Option("", "--detik", help="Detik yang dirender, dipisah koma (default: tengah tiap frasa)."),
) -> None:
    """Render frame diam + lembar kontak untuk dicek sebelum render penuh."""
    from autoreels import animasi

    times = [float(x) for x in detik.split(",") if x.strip()] or None
    animasi.stills(nama, times, log=_log)


@animasi_app.command("musik")
def animasi_musik(nama: str = typer.Option(..., "--nama", "-n", help="Nama video.")) -> None:
    """Gubah musik orisinal + efek suara dari partitur Claude (work/_animasi/<nama>/musik.json)."""
    from autoreels import animasi

    if not animasi.compose_music(nama, log=_log):
        console.print(f"[yellow]Partitur belum ada: {animasi.work_dir(nama) / 'musik.json'}[/yellow]")
        raise typer.Exit(code=1)


@animasi_app.command("gaya")
def animasi_gaya(
    nama: str = typer.Option(None, "--nama", "-n", help="Video yang diatur (kosong = tampilkan daftar gaya)."),
    pakai: str = typer.Option(None, "--pakai", help="Id gaya yang dipakai video ini."),
    pratinjau: bool = typer.Option(False, "--pratinjau", help="Render satu frame video ini di setiap gaya."),
) -> None:
    """Daftar gaya animasi, ganti gaya sebuah video, atau buat pratinjau semua gaya."""
    from autoreels import animasi

    if nama and pakai:
        animasi.set_style(nama, pakai)
        console.print(f"Gaya '{nama}' → {pakai} (render ulang untuk menerapkan).")
    if nama and pratinjau:
        animasi.style_previews(nama, log=_log)
    if not nama:
        for gid, g in animasi.list_styles().items():
            console.print(f"[bold]{gid}[/bold]: {g['nama']}. {g['deskripsi']}")


@animasi_app.command("cek")
def animasi_cek() -> None:
    """Cek tipe TypeScript semua kode animasi (npx tsc --noEmit)."""
    from autoreels import animasi

    try:
        animasi.typecheck(log=_log)
    except RuntimeError as e:
        console.print(str(e), markup=False)
        raise typer.Exit(code=1) from None


@animasi_app.command("render")
def animasi_render(
    nama: str = typer.Option(..., "--nama", "-n", help="Nama video."),
    cta: str = typer.Option(None, "--cta", help="Teks CTA yang tampil di animasi (default: CTA brand)."),
    logo: bool = typer.Option(False, "--logo", help="Tempel logo/watermark di pojok (default: tanpa)."),
) -> None:
    """Render animasi penuh → loudness, caption (caption.json), Checklist Siap Unggah. Tanpa API LLM & watermark."""
    from autoreels import animasi

    result = _run_with_progress(animasi.render, name=nama, cta=cta, logo=logo)
    _summary(result)


if __name__ == "__main__":
    app()
