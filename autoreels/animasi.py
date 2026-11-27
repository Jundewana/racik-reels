"""Video animasi 2D flat (Remotion) — Claude Code menulis kode animasinya per video (skill racik-animasi).

Alur:
  prepare  rekaman suara → narasi bersih (jeda & kata pengisi dibuang) + timing per kata → animasi/public/<nama>/
           (data.json, narasi.wav, musik) + aset brand animasi/public/_brand/ (font, logo)
  (Claude menulis animasi/src/videos/<nama>/ dan mendaftarkannya di src/videos/index.ts)
  stills   render beberapa frame diam → work/_animasi/<nama>/stills/ + lembar kontak, untuk dicek sebelum render penuh
  render   Remotion → work/_animasi/<nama>/anim.mp4 → importer (logo, loudness −14 LUFS, caption, Checklist Siap Unggah)

Remotion butuh Node (tidak butuh GPU untuk gaya 2D flat). Lisensi: gratis untuk perorangan/≤3 karyawan; pemakaian
untuk perusahaan lebih besar butuh Company License (lihat animasi/README.md).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from autoreels.config import PATHS, load_brand
from autoreels.render.overlays import instagram_for, logo_file_for

ROOT = PATHS["config"].parent
ANIM_DIR = ROOT / "animasi"
PUBLIC = ANIM_DIR / "public"
FPS = 30
GAYA_FILE = ANIM_DIR / "src" / "kit" / "gaya.json"
GAYA_DEFAULT = "racik-flat"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")


def work_dir(name: str) -> Path:
    return PATHS["work"] / "_animasi" / name


def comp_id(name: str) -> str:
    """Nama video (kebab-case) → id komposisi Remotion (huruf, angka, '-')."""
    return name


def check_name(name: str) -> str:
    if not NAME_RE.match(name):
        raise ValueError(f"Nama video '{name}' tidak valid: pakai huruf kecil, angka, dan '-' (mis. rental-garut).")
    return name


def _npx() -> str:
    exe = shutil.which("npx.cmd") or shutil.which("npx")
    if not exe:
        raise RuntimeError("Node.js/npx tidak ditemukan. Pasang Node.js lalu jalankan `npm install` di folder animasi/.")
    if not (ANIM_DIR / "node_modules" / "remotion").exists():
        raise RuntimeError("Remotion belum terpasang. Jalankan `npm install` di folder animasi/.")
    return exe


def _run_node(args: list[str], log=print, npx: bool = True) -> None:
    exe = _npx()
    cmd = [exe, *args] if npx else [shutil.which("node") or "node", *args[1:]]
    proc = subprocess.run(cmd, cwd=ANIM_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"Perintah gagal:\n{' '.join(cmd)}\n\n{(proc.stderr or proc.stdout)[-4000:]}")


def typecheck(log=print) -> None:
    """Cek tipe TypeScript proyek animasi (tsc --noEmit). Gagal → RuntimeError berisi pesan tsc."""
    _run_node(["tsc", "--noEmit"], log=log)
    log("  cek tipe: OK")


def list_styles() -> dict[str, dict]:
    """Gaya animasi dari animasi/src/kit/gaya.json: id → {nama, deskripsi, warna, font, …}."""
    return json.loads(GAYA_FILE.read_text(encoding="utf-8"))


def check_style(gaya: str) -> str:
    if gaya not in list_styles():
        raise ValueError(f"Gaya '{gaya}' tidak dikenal. Pilihan: {', '.join(list_styles())}")
    return gaya


def ensure_fonts() -> None:
    """Salin font semua gaya ke public/_brand/fonts/<path> (agar gaya bisa diganti tanpa prepare ulang)."""
    for g in list_styles().values():
        for rel in g["font"].values():
            src, dst = PATHS["fonts"] / rel, PUBLIC / "_brand" / "fonts" / rel
            if not src.is_file():
                raise FileNotFoundError(f"Font gaya tidak ada: assets/fonts/{rel}")
            if not dst.exists() or dst.stat().st_size != src.stat().st_size:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)


def set_style(name: str, gaya: str) -> dict:
    data = load_data(name)
    data["gaya"] = check_style(gaya)
    save_data(name, data)
    return data


def prepare_brand(pillar: str) -> dict:
    """Salin font & logo ke public/_brand dan kembalikan data brand untuk animasi."""
    brand = load_brand()
    bdir = PUBLIC / "_brand"
    bdir.mkdir(parents=True, exist_ok=True)
    fonts = brand.get("fonts", {})
    out_fonts = {}
    for key in ("heading", "body"):
        src = PATHS["fonts"] / fonts.get(key, "")
        if src.is_file():
            shutil.copy(src, bdir / src.name)
            out_fonts[key] = f"_brand/{src.name}"
    logo_src = logo_file_for(brand, pillar)
    logo = None
    if logo_src.is_file():
        shutil.copy(logo_src, bdir / logo_src.name)
        logo = f"_brand/{logo_src.name}"
    return {
        "nama": brand.get("company_name"),
        "nama_pendek": brand.get("short_name"),
        "warna": brand.get("colors", {}),
        "whatsapp": brand.get("whatsapp", {}).get("display"),
        "instagram": instagram_for(brand, pillar),
        "font": out_fonts,
        "logo": logo,
        "harga_sewa_per_hari": brand.get("pricing", {}).get("rental_per_day"),
        "layanan_rental": brand.get("rental_services") or [],
        "cta_default": brand.get("default_cta", {}).get(pillar),
    }


def prepare(*, voice: Path, name: str, pillar: str, brief: str = "", mood: str = "claude",
            music_db: float = -20.0, ranges: list[tuple[float, float | None]] | None = None,
            gaya: str = GAYA_DEFAULT, dimensi: str = "2d", log=print) -> Path:
    """mood "claude" (default) = musik orisinal digubah Claude (musik.json → `animasi musik`); mood lain = lagu dari
    assets/music/<mood>/; "none" = tanpa musik. ranges = [(mulai, sampai), …] detik: potong & sambung bagian rekaman
    dulu sesuai urutan (mis. beberapa bagian podcast; urutan boleh diubah untuk cold open)."""
    """Rekaman suara → animasi/public/<nama>/data.json (+ narasi.wav, musik). Mengembalikan path data.json."""
    from autoreels.analyze.audio import choose_track_with_fallback
    from autoreels.narration import prepare_narration

    check_name(name)
    check_style(gaya)
    if dimensi not in ("2d", "3d"):
        raise ValueError("Dimensi harus 2d atau 3d.")
    vdir = PUBLIC / name
    vdir.mkdir(parents=True, exist_ok=True)
    if ranges:
        voice = cut_source(voice, ranges, work_dir(name) / "sumber.wav", log=log)
    narration = prepare_narration(voice, vdir, log=log)  # → vdir/narasi.wav
    music_rel = None
    if mood not in ("none", "claude"):
        track, used = choose_track_with_fallback(mood, name)
        if track:
            shutil.copy(track, vdir / f"musik{track.suffix}")
            music_rel = f"{name}/musik{track.suffix}"
            log(f"  musik: {track.name} (mood {used})")
        else:
            log("  [peringatan] tidak ada musik di assets/music/ → tanpa musik")
    data = {
        "nama": name,
        "pilar": pillar,
        "brief": brief,
        "fps": FPS,
        "lebar": 1080,
        "tinggi": 1920,
        "durasi": round(narration.duration + 1.0, 3),  # +1 dtk ekor setelah kalimat terakhir (CTA tetap tampil)
        "durasi_narasi": narration.duration,
        "audio": {"narasi": f"{name}/narasi.wav", "musik": music_rel, "musik_db": music_db, "sfx": None,
                  "sfx_db": -10.0},
        "kata": [w.model_dump() for w in narration.words],
        "frasa": [p.model_dump(include={"start", "end", "text"}) for p in narration.phrases],
        "brand": prepare_brand(pillar),
        "gaya": gaya,
        "dimensi": dimensi,  # 3d = dunia three.js (animasi/src/kit3d) + teks/kartu 2D di atasnya
    }
    ensure_fonts()
    out = vdir / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    wdir = work_dir(name)
    wdir.mkdir(parents=True, exist_ok=True)
    (wdir / "naskah.txt").write_text(
        "\n".join(f"{p['start']:6.2f}–{p['end']:6.2f}  {p['text']}" for p in data["frasa"]) + "\n", encoding="utf-8")
    log(f"  data animasi: {out.relative_to(ROOT)} · durasi {data['durasi']:.1f} dtk · {len(data['frasa'])} frasa")
    return out


def cut_source(src: Path, ranges: list[tuple[float, float | None]], out: Path, log=print) -> Path:
    """Potong satu/lebih rentang audio (mis. bagian podcast panjang) dan sambung berurutan → WAV 48 kHz mono.
    Tiap sambungan diberi fade 25 ms agar tidak "klik"."""
    from autoreels.media import probe, run_ffmpeg

    out.parent.mkdir(parents=True, exist_ok=True)
    total = probe(src).duration
    parts, labels = [], []
    for i, (a, b) in enumerate(ranges):
        b = min(b if b else total, total)
        if not 0 <= a < b:
            raise ValueError(f"Rentang tidak valid: {a}–{b} (durasi sumber {total:.1f} dtk)")
        d = b - a
        parts.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=mono,"
                     f"afade=t=in:d=0.025,afade=t=out:st={max(0.0, d - 0.025):.3f}:d=0.025[p{i}]")
        labels.append(f"[p{i}]")
    graph = ";".join(parts) + f";{''.join(labels)}concat=n={len(labels)}:v=0:a=1[a]"
    run_ffmpeg(["-i", str(src), "-filter_complex", graph, "-map", "[a]", "-ar", "48000", "-ac", "1", "-y", str(out)])
    log("  sumber dipotong: " + ", ".join(f"{a:.1f}–{b or total:.1f}" for a, b in ranges) + f" → {out.name}")
    return out


def compose_music(name: str, log=print) -> bool:
    """Gubah musik dari partitur Claude (work/_animasi/<nama>/musik.json) → public/<nama>/musik.wav (+ sfx.wav).
    Mengembalikan False bila partitur tidak ada (musik dari prepare dipakai apa adanya)."""
    from autoreels.musik_sintesis import render_score

    score_file = work_dir(name) / "musik.json"
    if not score_file.exists():
        return False
    data = load_data(name)
    score = json.loads(score_file.read_text(encoding="utf-8"))
    music, sfx = render_score(score, data["durasi"], PUBLIC / name / "musik.wav", PUBLIC / name / "sfx.wav")
    data["audio"]["musik"] = f"{name}/musik.wav"
    data["audio"]["sfx"] = f"{name}/sfx.wav" if sfx else None
    if "musik_db" in score:
        data["audio"]["musik_db"] = float(score["musik_db"])
    if "sfx_db" in score:
        data["audio"]["sfx_db"] = float(score["sfx_db"])
    save_data(name, data)
    log(f"  musik orisinal: {score.get('bpm')} bpm, {score.get('kunci')} {score.get('skala', 'mayor')}, "
        f"{len(score.get('sfx', []))} efek suara → public/{name}/musik.wav")
    return True


def load_data(name: str) -> dict:
    f = PUBLIC / check_name(name) / "data.json"
    if not f.exists():
        raise FileNotFoundError(f"{f} belum ada. Jalankan dulu: autoreels animasi prepare --nama {name} …")
    return json.loads(f.read_text(encoding="utf-8"))


def save_data(name: str, data: dict) -> None:
    (PUBLIC / name / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def style_previews(name: str, t: float | None = None, log=print) -> dict[str, Path]:
    """Satu frame video ini di SETIAP gaya (satu bundle) → work/_animasi/<nama>/gaya/<id>.jpg."""
    data = load_data(name)
    ensure_fonts()
    if t is None:  # frame yang ramai: tengah frasa ke-2 (hook sudah lewat, elemen sudah muncul)
        f = data["frasa"][min(1, len(data["frasa"]) - 1)]
        t = (f["start"] + f["end"]) / 2
    out = work_dir(name) / "gaya"
    out.mkdir(parents=True, exist_ok=True)
    frame = max(0, min(int(data["durasi"] * FPS) - 1, round(t * FPS)))
    jobs = [[frame, f"{g}.jpg", g] for g in list_styles()]
    _run_node(["node", "scripts/stills.mjs", comp_id(name), str(out), json.dumps(jobs), "0.4"], log=log, npx=False)
    log(f"  pratinjau {len(jobs)} gaya → {out.relative_to(ROOT)}")
    return {g: out / f"{g}.jpg" for g in list_styles()}


def stills(name: str, times: list[float] | None = None, log=print) -> Path:
    """Render frame diam (detik tertentu; default tiap frasa di tengahnya) + lembar kontak. Mengembalikan folder."""
    from autoreels.media import run_ffmpeg

    data = load_data(name)
    ensure_fonts()
    if not times and data["frasa"]:
        times = [round((p["start"] + p["end"]) / 2, 2) for p in data["frasa"]]
    elif not times:  # mode footage (tanpa narasi): tiap 1,5 dtk
        times = [round(t, 2) for t in [0.3 + 1.5 * i for i in range(int(data["durasi"] / 1.5))]]
    sdir = work_dir(name) / "stills"
    if sdir.exists():
        shutil.rmtree(sdir)
    sdir.mkdir(parents=True)
    total = int(data["durasi"] * FPS)
    jobs = [[max(0, min(total - 1, round(t * FPS))), f"{i:02d}_{t:05.2f}s.jpg"] for i, t in enumerate(times)]
    _run_node(["node", "scripts/stills.mjs", comp_id(name), str(sdir), json.dumps(jobs), "0.5"], log=log,
              npx=False)  # satu bundle untuk semua frame
    files = sorted(sdir.glob("*.jpg"))
    cols = 4
    rows = -(-len(files) // cols)
    sheet = work_dir(name) / "lembar_stills.jpg"
    inputs: list[str] = []
    for f in files:
        inputs += ["-i", str(f)]
    pad = cols * rows - len(files)
    font = next(iter(sorted((PATHS["fonts"] / "Montserrat").glob("*Bold.ttf"))), None)
    font_opt = ("fontfile='" + font.relative_to(ROOT).as_posix() + "':") if font else ""
    graph = "".join(f"[{i}:v]scale=270:480,drawtext={font_opt}text='{f.stem.split('_')[1]}':x=8:y=8:fontsize=22:"
                    f"fontcolor=white:box=1:boxcolor=black@0.6[s{i}];" for i, f in enumerate(files))
    for j in range(pad):
        graph += f"color=c=gray:s=270x480:d=1[p{j}];"
    labels = "".join(f"[s{i}]" for i in range(len(files))) + "".join(f"[p{j}]" for j in range(pad))
    layout = "|".join(f"{(k % cols) * 270}_{(k // cols) * 480}" for k in range(cols * rows))
    graph += f"{labels}xstack=inputs={cols * rows}:layout={layout}[o]"
    if len(files) > 1:
        run_ffmpeg([*inputs, "-filter_complex", graph, "-map", "[o]", "-frames:v", "1", "-q:v", "3", "-y", str(sheet)],
                   cwd=ROOT)  # fontfile relatif (path Windows dengan ':' merusak sintaks filter)
    log(f"  {len(files)} frame diam → {sdir.relative_to(ROOT)} · lembar: {sheet.relative_to(ROOT)}")
    return sdir


def load_caption(name: str) -> dict:
    """Caption + hashtag yang ditulis Claude Code di work/_animasi/<nama>/caption.json (tanpa API)."""
    f = work_dir(name) / "caption.json"
    if not f.exists():
        raise FileNotFoundError(
            f"{f} belum ada. Tulis dulu caption IG (Claude Code): "
            '{"caption": "…", "hashtags": ["#rentalmotorgarut", …]} — lihat config/caption_guide.md.')
    cap = json.loads(f.read_text(encoding="utf-8"))
    if not str(cap.get("caption", "")).strip() or not cap.get("hashtags"):
        raise ValueError(f"{f}: 'caption' dan 'hashtags' wajib diisi.")
    return cap


def render(name: str, *, cta: str | None = None, logo: bool = False, log=print, on_progress=None):
    """Render animasi penuh lalu teruskan ke importer (logo, loudness, caption dari file, checklist).
    Murni lokal: tidak ada panggilan LLM API (caption ditulis Claude Code di caption.json).
    logo: tempel logo/watermark di pojok (default False — animasi sudah memuat brand di dalam videonya)."""
    from autoreels.importer import import_video

    data = load_data(name)
    caption = load_caption(name)
    ensure_fonts()
    wdir = work_dir(name)
    wdir.mkdir(parents=True, exist_ok=True)
    raw = wdir / "anim.mp4"
    if compose_music(name, log=log):
        data = load_data(name)
    log(f"Render animasi '{name}' ({data['durasi']:.1f} dtk, gaya {data.get('gaya') or GAYA_DEFAULT}) …")
    _run_node(["remotion", "render", "src/index.ts", comp_id(name), str(raw), "--codec=h264", "--crf=18",
               "--log=error"], log=log)
    from autoreels.config import load_pillars

    informasi = load_pillars().get(data["pilar"], {}).get("default_purpose") == "informasi" and not cta
    drawn = None if informasi else (cta or data.get("cta") or data["brand"].get("cta_default"))
    wa = data["brand"].get("whatsapp")
    if drawn and wa and wa not in drawn:  # kartu CtaWA kit selalu menampilkan nomor brand
        drawn = f"{drawn} · WA {wa}"
    return import_video(video=raw, pillar=data["pilar"], brief=data.get("brief", ""), add_logo=logo,
                        drawn_cta=drawn, add_cta=False, log=log, on_progress=on_progress, source="animasi",
                        caption=caption, informasi=informasi)
