"""AutoReels — menu utama.

Jalankan:  python main.py
(otomatis memakai .venv proyek bila ada)

Semua pertanyaan punya nilai default — tekan Enter untuk memakai default.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _ensure_venv() -> None:
    """Bila dijalankan dengan Python sistem, ulangi dengan Python dari .venv."""
    in_venv = Path(sys.prefix).resolve() == (ROOT / ".venv").resolve()
    if not in_venv and VENV_PY.exists() and not os.environ.get("AUTOREELS_NO_REEXEC"):
        env = {**os.environ, "AUTOREELS_NO_REEXEC": "1"}
        sys.exit(subprocess.call([str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]], env=env))
    try:
        import autoreels  # noqa: F401
    except ImportError:
        print("Paket autoreels belum terpasang. Jalankan dulu:\n"
            "  python -m venv .venv\n  .\\.venv\\Scripts\\Activate.ps1\n  pip install -e \".[dev,analysis]\"")
        sys.exit(1)


_ensure_venv()
os.chdir(ROOT)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.prompt import Confirm, IntPrompt, Prompt  # noqa: E402
from rich.table import Table  # noqa: E402

from autoreels import config_editor as ce  # noqa: E402
from autoreels.config import PATHS, list_styles, load_brand, load_pillars  # noqa: E402
from autoreels.media import AUDIO_EXTS, VIDEO_EXTS  # noqa: E402

console = Console()

DEFAULT_BRIEF = ce.DEFAULT_BRIEF
DEFAULT_STYLE = ce.DEFAULT_STYLE


# --- helper input --------------------------------------------------------------------------
def ask(label: str, default: str = "", hint: str = "") -> str:
    """Input teks; Enter = default. `hint` ditampilkan bila default kosong (mis. 'Enter = dipilih AI')."""
    shown = f"[dim]({hint})[/dim]" if hint and not default else ""
    value = Prompt.ask(f"{label} {shown}".strip(), default=default or "", show_default=bool(default))
    return value.strip()


def choose(label: str, options: list[str], default: str | None = None) -> str:
    for i, opt in enumerate(options, 1):
        mark = " [green](default)[/green]" if opt == default else ""
        console.print(f"  {i}. {opt}{mark}")
    d = options.index(default) + 1 if default in options else 1
    while True:
        n = IntPrompt.ask(label, default=d)
        if 1 <= n <= len(options):
            return options[n - 1]
        console.print("[red]Pilihan tidak ada.[/red]")


def split_items(raw: str) -> list[str]:
    return [x.strip() for x in raw.replace("\n", ";").split(";") if x.strip()]


def open_path(path: Path) -> None:
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as e:
        console.print(f"[yellow]Tidak bisa membuka {path}: {e}[/yellow]")


def count_files(folder: Path, exts: set[str]) -> int:
    return sum(1 for f in folder.iterdir() if f.suffix.lower() in exts) if folder.is_dir() else 0


# --- 1. buat reel ---------------------------------------------------------------------------
def menu_make_reel() -> None:
    from autoreels.cli import _run_with_progress, _summary
    from autoreels.pipeline import run_pipeline

    console.rule("[bold]Buat Reel dari video mentah")
    pillar = choose("Pilar konten", ce.PILLARS, "rental")

    default_dir = ROOT / "footage" / pillar
    folder = Path(ask("Folder video mentah", str(default_dir.relative_to(ROOT))))
    folder = folder if folder.is_absolute() else ROOT / folder
    n = count_files(folder, VIDEO_EXTS) if folder.is_dir() else (1 if folder.is_file() else 0)
    if n == 0 and folder.is_dir():
        # video mungkin ada di subfolder (mis. footage → footage/rental): tawarkan pilihan
        subs = [d for d in sorted(folder.rglob("*")) if d.is_dir() and count_files(d, VIDEO_EXTS)]
        if subs:
            console.print(f"[yellow]Tidak ada video langsung di {folder.name}\\, tapi ada di subfolder:[/yellow]")
            labels = [f"{d.relative_to(ROOT)}  ({count_files(d, VIDEO_EXTS)} video)" for d in subs]
            default = next((lb for lb, d in zip(labels, subs) if d == default_dir), labels[0])
            folder = subs[labels.index(choose("Pakai folder", labels, default))]
            n = count_files(folder, VIDEO_EXTS)
    if n == 0:
        console.print(f"[red]Tidak ada video di {folder}. Taruh file .mp4/.mov di sana dulu.[/red]")
        return
    console.print(f"  [green]{n} video ditemukan.[/green]")

    brief = ask("Instruksi edit", DEFAULT_BRIEF[pillar])
    style_default = load_pillars().get(pillar, {}).get("default_style") or DEFAULT_STYLE[pillar]
    style = choose("Style", list_styles(), style_default)
    duration = IntPrompt.ask("Durasi (detik, 8–90)", default=20)
    duration = min(90, max(8, duration))

    hooks = ce.load_hooks().get(pillar, [])
    if hooks:
        console.print("  [dim]Contoh hook dari pustaka: " + " • ".join(h["text"] for h in hooks[:5]) + "[/dim]")
    hook = ask("Teks hook", "", "Enter = dipilih AI dari pustaka hook")
    if hook and (p := ce.hook_problems(hook)):
        console.print(f"  [yellow]Hook kepanjangan ({', '.join(p)}) — teks akan tampil kecil.[/yellow]")
        if not Confirm.ask("  Tetap pakai?", default=False):
            hook = ""
    cta_default = load_brand().get("default_cta", {}).get(pillar, "")
    cta = ask("Teks CTA", "", f"Enter = dipilih AI, mis. '{cta_default}'")

    vo_choice = choose("Voice over", ["tanpa", "suara sendiri (rekam di web setelah naskah jadi)", "suara AI (Gemini)"],
                    "tanpa")
    voiceover = {"tanpa": "none", "suara AI (Gemini)": "gemini"}.get(vo_choice, "rekam")
    voice = "Puck"
    if voiceover == "gemini":
        from autoreels.voiceover import VOICES

        voice = choose("Karakter suara", list(VOICES), "Puck")
    elif voiceover == "rekam":
        console.print("  [dim]Naskah ditulis AI. Setelah selesai, rekam suara di tampilan web "
                "(python main.py --web → Riwayat → buka Reel → panel Voice Over).[/dim]")

    music = None
    mood_dir = PATHS["music"]
    if Confirm.ask("Pilih lagu sendiri?", default=False):
        tracks = sorted(f for f in mood_dir.rglob("*") if f.suffix.lower() in AUDIO_EXTS)
        if tracks:
            pick = choose("Lagu", [str(t.relative_to(mood_dir)) for t in tracks])
            music = mood_dir / pick
        else:
            console.print("[yellow]Belum ada lagu di assets/music/.[/yellow]")

    table = Table(show_header=False, box=None)
    for k, v in [("Pilar", pillar), ("Folder", str(folder)), ("Instruksi", brief), ("Style", style),
                ("Durasi", f"{duration} dtk"), ("Hook", hook or "(dipilih AI)"),
                ("CTA", cta or "(dipilih AI)"), ("Musik", music.name if music else "(otomatis sesuai style)"),
                ("Voice over", vo_choice + (f" — {voice}" if voiceover == "gemini" else ""))]:
        table.add_row(f"[bold]{k}[/bold]", v)
    console.print(Panel(table, title="Ringkasan", border_style="cyan"))
    if not Confirm.ask("Mulai proses?", default=True):
        return

    try:
        result = _run_with_progress(run_pipeline, input_path=folder, pillar=pillar, brief=brief,
                                    style_name=style, duration=duration, music_file=music,
                                    hook_text=hook or None, cta_text=cta or None,
                                    voiceover=voiceover, voice=voice)
    except Exception as e:  # noqa: BLE001 — tampilkan error ke pengguna, menu tetap jalan
        console.print(f"[red]Gagal: {e}[/red]")
        return
    _summary(result)
    if Confirm.ask("Buka videonya sekarang?", default=True):
        open_path(result.reel)


# --- 1b. impor video jadi -------------------------------------------------------------------------
def find_import_candidates() -> list[Path]:
    """Video jadi dari video-use (<folder>/edit/final.mp4) di dalam footage/, terbaru dulu."""
    found = [p for p in (ROOT / "footage").rglob("final.mp4") if p.parent.name == "edit"]
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)[:10]


def menu_import() -> None:
    from autoreels.cli import _run_with_progress, _summary
    from autoreels.importer import import_video

    console.rule("[bold]Impor video jadi (video-use / editor lain)")
    console.print("[dim]Video diubah ke 1080×1920, suara dinormalisasi, ditempel logo + CTA WhatsApp, "
                "lalu dibuatkan caption & hashtag oleh AI.[/dim]")
    candidates = find_import_candidates()
    video: Path | None = None
    if candidates:
        labels = [str(p.relative_to(ROOT)) for p in candidates] + ["(ketik path lain)"]
        pick = choose("Video hasil video-use", labels, labels[0])
        if pick != "(ketik path lain)":
            video = ROOT / pick
    if video is None:
        raw = ask("Path video (boleh drag file ke terminal)").strip('"').strip("'")
        if not raw:
            return
        video = Path(raw) if Path(raw).is_absolute() else ROOT / raw
    if not video.is_file():
        console.print(f"[red]File tidak ditemukan: {video}[/red]")
        return

    pillar = choose("Pilar konten", ce.PILLARS, "profil")
    brief = ask("Isi/tujuan video (membantu AI menulis caption)", "", "Enter = AI menyimpulkan dari transkrip")
    hook = ask("Tempel teks hook di awal?", "", "Enter = tidak, pakai hook dari editor")
    if hook and (p := ce.hook_problems(hook)):
        console.print(f"  [yellow]Hook kepanjangan ({', '.join(p)}).[/yellow]")
    add_cta = Confirm.ask("Tempel CTA WhatsApp di 3 detik terakhir?", default=True)
    cta = ""
    if add_cta:
        cta_default = load_brand().get("default_cta", {}).get(pillar, "")
        cta = ask("Teks CTA", cta_default)
    add_logo = Confirm.ask("Tempel logo Brand?", default=True)
    try:
        result = _run_with_progress(import_video, video=video, pillar=pillar, brief=brief,
                                    hook_text=hook or None, cta_text=cta or None,
                                    add_logo=add_logo, add_cta=add_cta)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Gagal: {e}[/red]")
        return
    _summary(result)
    console.print(Panel(result.caption, title="Caption", border_style="cyan"))
    if Confirm.ask("Buka videonya sekarang?", default=True):
        open_path(result.reel)


# --- 2. hook ------------------------------------------------------------------------------------
def menu_hooks() -> None:
    while True:
        console.rule("[bold]Pustaka hook")
        hooks = ce.load_hooks()
        for pillar in ce.PILLARS:
            console.print(f"[bold cyan]{pillar}[/bold cyan]")
            for i, h in enumerate(hooks[pillar], 1):
                warn = " [yellow]⚠ kepanjangan[/yellow]" if ce.hook_problems(h["text"]) else ""
                console.print(f"  {i:2}. {h['text']}  [dim]({h['type']})[/dim]{warn}")
            if not hooks[pillar]:
                console.print("  [dim](kosong — AI memakai pola umum)[/dim]")
        action = choose("Aksi", ["tambah hook", "hapus hook", "kembali"], "kembali")
        if action == "kembali":
            return
        pillar = choose("Pilar", ce.PILLARS, "rental")
        if action == "tambah hook":
            text = ask(f"Teks hook (maks {ce.HOOK_MAX_WORDS} kata / {ce.HOOK_MAX_CHARS} huruf)")
            if not text:
                continue
            if p := ce.hook_problems(text):
                console.print(f"[yellow]Kepanjangan: {', '.join(p)}.[/yellow]")
                if not Confirm.ask("Tetap simpan?", default=False):
                    continue
            hook_type = choose("Tipe hook", ce.HOOK_TYPES, "pertanyaan")
            ce.add_hook(pillar, hook_type, text)
            console.print("[green]Hook disimpan.[/green]")
        else:
            if not hooks[pillar]:
                continue
            n = IntPrompt.ask("Nomor hook yang dihapus", default=0)
            if 1 <= n <= len(hooks[pillar]):
                removed = ce.remove_hook(pillar, n - 1)
                console.print(f"[green]Dihapus: {removed['text']}[/green]")


# --- 3. hashtag & keyword -------------------------------------------------------------------------
def menu_hashtags() -> None:
    console.rule("[bold]Hashtag & keyword per pilar")
    pillar = choose("Pilar", ce.PILLARS, "rental")
    data = ce.get_pillar(pillar)
    tags = data.get("hashtags") or []
    kws = data.get("keywords") or []
    console.print(f"Hashtag sekarang : {' '.join(tags) or '(kosong)'}")
    console.print(f"Keyword sekarang : {', '.join(kws) or '(kosong)'}")
    raw = ask("Hashtag baru (pisahkan spasi/koma)", "", "Enter = tidak diubah")
    if raw:
        new_tags = ce.normalize_hashtags(raw)
        ce.set_pillar_list(pillar, "hashtags", new_tags)
        console.print(f"[green]Hashtag disimpan ({len(new_tags)}): {' '.join(new_tags)}[/green]")
    raw = ask("Keyword SEO (pisahkan koma)", "", "Enter = tidak diubah")
    if raw:
        new_kws = ce.normalize_keywords(raw)
        ce.set_pillar_list(pillar, "keywords", new_kws)
        console.print(f"[green]Keyword disimpan: {', '.join(new_kws)}[/green]")


# --- 4. brief tren ----------------------------------------------------------------------------------
def menu_trends() -> None:
    console.rule("[bold]Brief tren")
    console.print("[dim]Pisahkan beberapa poin dengan titik koma ( ; ). Enter = tidak diubah.[/dim]")
    current = ce.read_trend_items()
    sections = [("formats", "Format yang sedang ramai"), ("hooks", "Gaya hook yang naik"),
                ("audio", "Audio trending (judul saja)"), ("moments", "Momen musiman / event Garut"),
                ("notes", "Catatan lain")]
    values = {}
    for key, title in sections:
        old = current.get(title, [])
        console.print(f"[bold]{title}[/bold]: {'; '.join(old) or '(kosong)'}")
        raw = ask("  baru", "", "Enter = tidak diubah")
        values[key] = split_items(raw) if raw else old
    if Confirm.ask("Kosongkan semua tren (AI mengabaikan tren)?", default=False):
        values = {k: [] for k, _ in sections}
    path = ce.write_trend_brief(**values)
    console.print(f"[green]Brief tren disimpan ke {path.relative_to(ROOT)}[/green]")


# --- 5. brand -------------------------------------------------------------------------------------------
def menu_brand() -> None:
    console.rule("[bold]Info brand")
    brand = ce.load_brand_raw()
    price = brand.get("pricing", {}).get("rental_per_day", "[HARGA]")
    console.print("[dim]Harga dipakai AI di hook/teks. Biarkan [HARGA] bila belum pasti (AI tidak akan menyebut harga).[/dim]")
    new_price = ask("Harga sewa motor per hari (mis. Rp100.000)", str(price))
    if new_price != str(price):
        ce.set_brand_value("pricing", "rental_per_day", new_price)
        console.print("[green]Harga disimpan.[/green]")
    console.print("[bold]CTA default per pilar[/bold] (dipakai bila AI tidak menulis CTA)")
    for pillar in ce.PILLARS:
        old = brand.get("default_cta", {}).get(pillar, "")
        new = ask(f"  {pillar}", old)
        if new and new != old:
            ce.set_brand_value("default_cta", pillar, new)
    console.print("[green]Info brand tersimpan.[/green]")


# --- 6. panduan caption --------------------------------------------------------------------------------
def menu_caption_guide() -> None:
    console.rule("[bold]Panduan caption")
    old = ce.load_caption_guide()
    fields = {
        "Sapaan": ask("Sapaan ke penonton (kamu/kak/sobat)", old.get("Sapaan", "kamu")),
        "Emoji": ask("Emoji (tidak/secukupnya/bebas)", old.get("Emoji", "secukupnya")),
        "Bahasa Sunda": ask("Sisipan bahasa Sunda (ya/tidak)", old.get("Bahasa Sunda", "ya, ringan, pilar rental")),
        "Kata dihindari": ask("Kata yang dihindari", old.get("Kata dihindari", "termurah, 100% aman, terbaik se-Garut")),
        "Panjang": ask("Panjang caption", old.get("Panjang", "2–4 kalimat")),
    }
    examples = []
    console.print("[dim]Contoh caption bagus (Enter kosong = selesai / tidak menambah).[/dim]")
    for i in range(1, 4):
        ex = ask(f"  Contoh {i}", "", "Enter = lewati")
        if not ex:
            break
        examples.append(ex)
    path = ce.write_caption_guide(fields, examples)
    console.print(f"[green]Panduan caption disimpan ke {path.relative_to(ROOT)}[/green]")


# --- 7. render ulang / hasil ---------------------------------------------------------------------------
def list_jobs(with_edl: bool = False) -> list[Path]:
    """Daftar job (file penanda: edl.json untuk render ulang, reel.mp4 untuk semua hasil)."""
    marker = "edl.json" if with_edl else "reel.mp4"
    return sorted((p for p in PATHS["output"].glob(f"*/{marker}")), key=lambda p: p.stat().st_mtime, reverse=True)


def pick_job(with_edl: bool = False) -> Path | None:
    jobs = list_jobs(with_edl)[:10]
    if not jobs:
        console.print("[yellow]Belum ada hasil di output/.[/yellow]")
        return None
    labels = []
    for j in jobs:
        status_file = j.parent / "status.txt"
        status = status_file.read_text(encoding="utf-8").strip() if status_file.exists() else "?"
        labels.append(f"{j.parent.name}  [{status}]")
    pick = choose("Pilih job", labels, labels[0])
    return jobs[labels.index(pick)]


def menu_rerender() -> None:
    from autoreels.cli import _run_with_progress, _summary
    from autoreels.edl import EDL
    from autoreels.pipeline import render_from_edl

    console.rule("[bold]Edit teks & render ulang (tanpa biaya AI)")
    console.print("[dim]Hanya untuk video buatan AutoReels (video impor tidak punya EDL).[/dim]")
    edl_path = pick_job(with_edl=True)
    if not edl_path:
        return
    edl = EDL.load(edl_path)
    hook = ask("Teks hook", edl.hook.overlay_text or "")
    if p := ce.hook_problems(hook):
        console.print(f"[yellow]Hook kepanjangan ({', '.join(p)}).[/yellow]")
    cta = ask("Teks CTA", edl.cta.text if edl.cta else "")
    edl.hook.overlay_text = hook
    if edl.cta:
        edl.cta.text = cta
    for seg in edl.segments:
        if seg.overlay_text:
            seg.overlay_text = ask(f"Teks segmen {seg.index}", seg.overlay_text) or None
    edl.save(edl_path)
    try:
        result = _run_with_progress(render_from_edl, edl_path=edl_path)
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Gagal: {e}[/red]")
        return
    _summary(result)
    if Confirm.ask("Buka videonya?", default=True):
        open_path(result.reel)


def menu_results() -> None:
    console.rule("[bold]Hasil")
    edl_path = pick_job()
    if not edl_path:
        return
    folder = edl_path.parent
    what = choose("Buka", ["video (reel.mp4)", "caption (caption.txt)", "laporan (report.md)", "folder"],
                "video (reel.mp4)")
    target = {"video (reel.mp4)": folder / "reel.mp4", "caption (caption.txt)": folder / "caption.txt",
            "laporan (report.md)": folder / "report.md", "folder": folder}[what]
    open_path(target)


def menu_web() -> None:
    from autoreels.server import serve

    console.print("[green]Membuka AutoReels Studio di browser…[/green] (Ctrl+C di jendela ini untuk berhenti)")
    serve()


def menu_status() -> None:
    from autoreels.cli import status

    status(job=None)


# --- menu utama ------------------------------------------------------------------------------------------
MENU = [
    ("Buka AutoReels Studio (tampilan web di browser)", menu_web),
    ("Buat Reel dari video mentah", menu_make_reel),
    ("Impor video jadi (video-use / editor lain)", menu_import),
    ("Kelola hook", menu_hooks),
    ("Hashtag & keyword per pilar", menu_hashtags),
    ("Brief tren minggu ini", menu_trends),
    ("Info brand (harga sewa, CTA default)", menu_brand),
    ("Panduan caption", menu_caption_guide),
    ("Edit teks hook/CTA & render ulang", menu_rerender),
    ("Lihat hasil (video, caption, laporan)", menu_results),
    ("Pantau progress job yang sedang jalan", menu_status),
]


def main() -> None:
    while True:
        console.print()
        console.print(Panel.fit("[bold]AutoReels[/bold] — Contoh Brand\n"
                                "[dim]Video mentah → Instagram Reels siap unggah[/dim]", border_style="green"))
        for i, (label, _) in enumerate(MENU, 1):
            console.print(f"  [bold]{i}[/bold]. {label}")
        console.print("  [bold]0[/bold]. Keluar")
        n = IntPrompt.ask("Pilih menu", default=1)
        if n == 0:
            console.print("Sampai jumpa!")
            return
        if 1 <= n <= len(MENU):
            try:
                MENU[n - 1][1]()
            except KeyboardInterrupt:
                console.print("\n[yellow]Dibatalkan.[/yellow]")
        else:
            console.print("[red]Menu tidak ada.[/red]")


if __name__ == "__main__":
    if "--web" in sys.argv or "--hp" in sys.argv:
        # python main.py --web → tampilan web di laptop; --hp → juga bisa dibuka dari HP (Wi-Fi sama, pakai PIN)
        from autoreels.server import serve

        serve(lan="--hp" in sys.argv or "--lan" in sys.argv)
        sys.exit(0)
    try:
        main()
    except KeyboardInterrupt:
        console.print("\nSampai jumpa!")
