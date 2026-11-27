"""Buat video dengan Claude + Remotion: footage mentah → analisis (adegan, kualitas, crop, beat) → klip H.264 di
animasi/public/<nama>/klip/ + data.json (mode "footage") → Claude Code menulis komposisi Remotion yang memotong &
menyusun footage asli → render & impor lewat jalur Racik Animasi (loudness, caption, Checklist Siap Unggah).

Tanpa API LLM: Claude melihat lembar kontak adegan, memilih potongan, menulis kode, musik, dan caption.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from autoreels import animasi
from autoreels.config import load_style
from autoreels.media import run_ffmpeg

MAX_ADEGAN = 100   # batas adegan layak yang dibaca Claude (≈ 9 lembar kontak)
CLIP_MAX_H = 1920  # tinggi maks klip kerja (cukup untuk crop 9:16 penuh dari footage lebar)


def _normalize(src: Path, dst: Path, log=print) -> None:
    """Klip kerja yang pasti bisa didekode Chrome/Remotion: H.264, 30 fps, tanpa audio, keyframe rapat (seek presisi)."""
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp.mp4")
    log(f"  klip kerja: {src.name}")
    run_ffmpeg(["-i", str(src), "-an", "-vf", f"fps=30,scale=-2:'min(ih,{CLIP_MAX_H})'",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-g", "15", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(tmp)])
    tmp.replace(dst)


def _best_moment(scene) -> float | None:
    curve = scene.moment_curve
    return round(max(curve, key=lambda p: p[1])[0], 2) if curve else None


def prepare(*, nama: str, input_path: Path, pillar: str, brief: str, style_name: str, duration: float,
            clips: list[str] | None = None, hook_text: str | None = None, cta_text: str | None = None,
            music_file: Path | None = None, narration_draft: str | None = None, talk_clip: str | None = None,
            no_music: bool = False, musik_claude: bool = False, log=print) -> Path:
    """Siapkan semua bahan; mengembalikan path data.json. Analisis di-cache per hash file (cepat bila diulang).
    narration_draft = transkrip yang sudah diperiksa manusia (alur narasi dulu / video bicara): suara bersih jadi
    narasi.wav, kata & frasa masuk data.json; talk_clip = file pembicara (frasa membawa src_start → sinkron bibir)."""
    from autoreels import manual
    from autoreels.analyze.models import Analysis
    from autoreels.narration import load_draft, use_draft

    animasi.check_name(nama)
    style = load_style(style_name)
    narr = None
    if narration_draft:
        draft = load_draft(narration_draft)
        if not draft.get("reviewed"):
            raise RuntimeError("Transkrip belum diperiksa. Simpan transkrip dulu di langkah sebelumnya.")
        duration = float(draft["narration"]["duration"])
    job_id = manual.prepare(input_path=input_path, pillar=pillar, brief=brief, style_name=style_name,
                            duration=duration, describe="claude", clips=clips, music_file=music_file,
                            hook_text=hook_text, cta_text=cta_text, log=log)
    analysis = Analysis.model_validate_json((animasi.PATHS["work"] / job_id / "analysis.json").read_text(encoding="utf-8"))

    n_layak = len(analysis.usable_scenes())
    if n_layak > MAX_ADEGAN:  # Claude harus melihat semuanya lewat lembar kontak; terlalu banyak = lambat & mahal
        raise RuntimeError(f"{n_layak} adegan layak terlalu banyak untuk disusun Claude (maks {MAX_ADEGAN}). "
                           "Pilih lebih sedikit klip, atau potong video panjang jadi cuplikan.")
    vdir = animasi.PUBLIC / nama
    (vdir / "klip").mkdir(parents=True, exist_ok=True)
    log("Klip kerja untuk Remotion …")
    klip = []
    for c in analysis.clips:
        stem = Path(c.name).stem.lower().replace(" ", "_")
        _normalize(Path(c.path), vdir / "klip" / f"{stem}.mp4", log=log)
        klip.append({"nama": c.name, "file": f"{nama}/klip/{stem}.mp4", "durasi": round(c.duration, 3),
                     "lebar": c.width, "tinggi": c.height, "fps": round(c.fps, 2)})
    file_of = {k["nama"]: k["file"] for k in klip}

    adegan = []
    for s in analysis.scenes:
        adegan.append({
            "id": s.scene_id, "file": file_of[s.source_file], "sumber": s.source_file,
            "mulai": round(s.start, 2), "selesai": round(s.end, 2), "durasi": round(s.duration, 2),
            "layak": s.usable, "alasan": s.reasons, "tajam": round(s.sharpness, 1), "terang": round(s.brightness, 1),
            "goyang": round(s.shake, 2), "gerak": round(s.motion, 2),
            "crop": [[round(t, 2), round(x, 3)] for t, x in s.crop_path] or [[round(s.start, 2), round(s.crop_cx_start, 3)],
                                                                         [round(s.end, 2), round(s.crop_cx_end, 3)]],
            "momen_terbaik": _best_moment(s),
        })

    audio = {"narasi": None, "musik": None, "musik_db": -14.0, "sfx": None, "sfx_db": -10.0}
    extra: dict = {"alur": "montase"}
    if narration_draft:
        narr, _src = use_draft(narration_draft, vdir)  # → vdir/narasi.wav
        audio["narasi"] = f"{nama}/narasi.wav"
        audio["musik_db"] = -20.0  # di bawah suara; naik otomatis saat jeda (Bingkai)
        duration = round(narr.duration + 1.0, 3)  # +1 dtk ekor setelah kalimat terakhir (CTA tetap tampil)
        speaker = narr.speaker_clip or talk_clip
        extra = {"alur": "bicara" if speaker else "narasi", "durasi_narasi": narr.duration,
                 "cold_open_sec": narr.cold_open_sec,
                 "kata": [w.model_dump() for w in narr.words], "frasa": [p.model_dump() for p in narr.phrases]}
        if speaker:
            sp = next((k for k in klip if k["nama"] == speaker), None)
            if sp is None:
                raise RuntimeError(f"Video pembicara {speaker} tidak ada di footage terpilih.")
            extra["pembicara"] = sp
    beats, tempo = [], 0.0
    musik_claude = musik_claude and not no_music  # tanpa musik menang
    if analysis.music and not no_music and not musik_claude:  # musik_claude: lagu digubah Claude (musik.json) saat render
        m = analysis.music
        out = vdir / "musik.wav"  # dipotong dari titik mulai yang dipilih; musik.json Claude bisa menimpanya
        run_ffmpeg(["-ss", f"{m.start_offset:.3f}", "-t", f"{duration + 2:.2f}", "-i", m.path, "-ar", "48000",
                    "-ac", "2", str(out)])
        audio["musik"] = f"{nama}/musik.wav"
        beats, tempo = [round(b, 3) for b in m.beats if b <= duration + 1], round(m.tempo, 1)

    data = {
        "nama": nama, "pilar": pillar, "brief": brief, "fps": animasi.FPS, "lebar": 1080, "tinggi": 1920,
        "durasi": round(float(duration), 3), "durasi_narasi": 0, "audio": audio, "kata": [], "frasa": [],
        **extra,
        "brand": animasi.prepare_brand(pillar), "gaya": animasi.GAYA_DEFAULT, "dimensi": "2d",
        "mode": "footage", "style_preset": style_name, "preset": style, "hook_text": hook_text, "cta_text": cta_text,
        "tanpa_musik": no_music, "musik_orisinal": musik_claude, "klip": klip, "adegan": adegan, "beats": beats, "tempo": tempo, "sumber_job": job_id,
    }
    animasi.ensure_fonts()
    out = vdir / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    wdir = animasi.work_dir(nama)
    wdir.mkdir(parents=True, exist_ok=True)
    for old in wdir.glob("lembar_kontak_*.jpg"):
        old.unlink()
    for sheet in sorted((manual.manual_dir(job_id)).glob("lembar_*.jpg")):
        shutil.copy(sheet, wdir / f"lembar_kontak_{sheet.stem.split('_')[-1]}.jpg")
    rows = [f"{a['id']:<14} {a['sumber']:<22} {a['mulai']:7.2f}-{a['selesai']:7.2f} ({a['durasi']:4.1f}s) "
            f"{'layak' if a['layak'] else 'TIDAK LAYAK: ' + ', '.join(a['alasan'])} "
            f"momen={a['momen_terbaik']}" for a in adegan]
    (wdir / "adegan.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
    usable = sum(a["layak"] for a in adegan)
    log(f"  data footage: {out.relative_to(animasi.ROOT)} · {len(klip)} klip · {usable}/{len(adegan)} adegan layak · "
        f"durasi target {duration:.0f} dtk")
    return out
