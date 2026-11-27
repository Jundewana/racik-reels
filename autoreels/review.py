"""Cek visual video jadi: model vision menilai frame dari reel.mp4 (bukan EDL) setelah render.

Melengkapi Critic (yang hanya membaca EDL) dan cek kode di checklist: menangkap hal yang baru terlihat setelah
render — teks sulit dibaca di atas gambar, crop memotong kepala/subjek, frame gelap/blur/kosong, teks tidak cocok
dengan gambar. Masalah "berat" → job perlu ditinjau; "ringan" → catatan. Gagal memanggil AI tidak menggagalkan job.
Hasil: output/<job>/visual_review.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from autoreels.edl import EDL
from autoreels.media import probe, run_ffmpeg

FRAME_W, FRAME_H = 432, 768   # 9:16 diperkecil: cukup untuk menilai keterbacaan, hemat token
MAX_FRAMES = 6


class VisualIssue(BaseModel):
    frame: int = Field(..., ge=1)
    severity: Literal["berat", "ringan"]
    problem: str
    fix: str = ""


class VisualReview(BaseModel):
    score: int = Field(..., ge=1, le=5)
    issues: list[VisualIssue] = Field(default_factory=list)
    summary: str = ""


def _timeline(edl: EDL) -> list[tuple[float, float, str, str]]:
    """(mulai, selesai, peran, teks yang seharusnya tampil) per segmen di video jadi (perkiraan)."""
    out, t = [], 0.0
    phrases = edl.narration.phrases if edl.narration is not None else []
    for i, s in enumerate(edl.segments):
        dur = (s.end - s.start) / (s.speed or 1.0)
        if phrases and i < len(phrases):
            a, b = phrases[i].start, phrases[i].end
            text = phrases[i].text  # narasi/video bicara: subtitle karaoke frasa ini
        else:
            a, b = t, t + dur
            text = s.overlay_text or ""
        role = s.role.value
        if role == "hook" and edl.hook.overlay_text:
            text = edl.hook.overlay_text
        out.append((a, b, role, text))
        t += dur
    return out


KIND_LABEL = {"hook": "teks hook", "info": "teks info", "cta": "CTA", "cta_sub": "kontak CTA",
              "sub": "subtitle voice over", "karaoke": "subtitle karaoke", "badge": "label"}


def _plain(ass_text: str) -> str:
    import re

    return re.sub(r"\s+", " ", re.sub(r"\{[^}]*\}", "", ass_text).replace(r"\N", " ")).strip()


def screen_texts(edl: EDL, t: float, events=None) -> str:
    """Teks yang SEHARUSNYA tampil di layar pada detik t — dari jadwal teks yang sama dengan render
    (hook, subtitle karaoke per potongan, info, CTA). Subtitle disembunyikan selama hook ikut diperhitungkan."""
    if events is None:
        from autoreels.config import load_brand
        from autoreels.render.overlays import text_events

        events = text_events(edl, load_brand(), None, edl.narration.words if edl.narration is not None else None)
    parts = []
    for ev in events:
        if ev.start <= t < ev.end and t >= ev.start + getattr(ev, "reveal", 0.0):
            text = _plain(ev.text)
            if text:
                parts.append(f'{KIND_LABEL.get(ev.kind, ev.kind)}: "{text}"')
    return "; ".join(parts) or "tidak ada teks"


def frame_plan(edl: EDL, duration: float) -> list[tuple[float, str]]:
    """Waktu frame + keterangan: 2 frame hook, ≤3 di tengah (merata), 1 di CTA/akhir."""
    tl = _timeline(edl)
    plan: list[tuple[float, str]] = []
    hook_end = tl[0][1] if tl else 2.0
    hook_text = edl.hook.overlay_text or "-"
    plan.append((0.3, f"hook awal; teks hook seharusnya: \"{hook_text}\""))
    plan.append((min(1.6, max(0.6, hook_end - 0.2)), f"hook (teks harus sudah terbaca); teks: \"{hook_text}\""))
    middle = [x for x in tl[1:-1] if x[1] - x[0] > 0.4]
    if middle:
        step = max(1, len(middle) // 3)
        for a, b, role, text in middle[::step][:3]:
            plan.append(((a + b) / 2, f"segmen {role}; teks seharusnya: \"{text or '-'}\""))
    if edl.cta is not None:
        plan.append((min(duration - 0.2, edl.cta.at_sec + 1.0), f"CTA; teks seharusnya: \"{edl.cta.text}\""))
    else:
        plan.append((duration - 0.6, "penutup video"))
    try:  # keterangan teks dari jadwal yang sama dengan render (paling akurat, termasuk subtitle karaoke)
        from autoreels.config import load_brand
        from autoreels.render.overlays import text_events

        events = text_events(edl, load_brand(), None, edl.narration.words if edl.narration is not None else None)
    except Exception:  # noqa: BLE001 — cadangan: keterangan per segmen di atas
        events = None
    seen, out = set(), []
    for t, label in plan:
        t = round(min(max(0.0, t), max(0.0, duration - 0.1)), 2)
        if t not in seen:
            seen.add(t)
            where = label.split(";", 1)[0]
            out.append((t, f"{where}; teks di layar seharusnya: {screen_texts(edl, t, events)}" if events is not None
                        else label))
    return out[:MAX_FRAMES]


def extract_frames(reel: Path, plan: list[tuple[float, str]], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (t, _) in enumerate(plan, start=1):
        p = out_dir / f"cek_{i}.jpg"
        run_ffmpeg(["-ss", f"{t:.2f}", "-i", str(reel), "-frames:v", "1",
                    "-vf", f"scale={FRAME_W}:{FRAME_H}", "-q:v", "4", str(p)])
        paths.append(p)
    return paths


def review_video(reel: Path, edl: EDL, llm, model: str, work_dir: Path, *, log=print) -> dict:
    """Nilai video jadi. Selalu mengembalikan dict (berisi 'error' bila AI gagal)."""
    from autoreels.config import load_prompt
    from autoreels.llm import image_to_content, max_images_per_request

    try:
        duration = probe(reel).duration
        plan = frame_plan(edl, duration)
        frames = extract_frames(reel, plan, work_dir / "cek_visual")
        if max_images_per_request(model) < len(frames):
            plan, frames = plan[:max_images_per_request(model)], frames[:max_images_per_request(model)]
        content: list[dict] = [{"type": "text", "text": (
            f"Reel {duration:.1f} dtk, tujuan: {edl.purpose.value}, alur: "
            f"{'video bicara' if edl.narration and edl.narration.speaker_clip else 'narasi' if edl.narration else 'montase'}. "
            f"Privasi: blur wajah {'aktif' if edl.privacy.blur_faces else 'mati'}, "
            f"blur pelat {'aktif' if edl.privacy.blur_plates else 'mati'}.")}]
        for i, ((t, label), path) in enumerate(zip(plan, frames), start=1):
            content.append({"type": "text", "text": f"Frame {i} — detik {t:.1f}: {label}"})
            content.append(image_to_content(path))
        result = llm.complete_structured(
            [{"role": "system", "content": load_prompt("visual_review")}, {"role": "user", "content": content}],
            VisualReview, model=model, purpose="visual_review")
    except Exception as e:  # noqa: BLE001 — cek visual bersifat bantuan
        log(f"  [peringatan] cek visual dilewati: {str(e).splitlines()[0][:160]}")
        return {"error": str(e).splitlines()[0][:300], "model": model}
    data = {"model": model, **result.model_dump(),
            "frames": [{"frame": i, "sec": t, "label": label} for i, (t, label) in enumerate(plan, start=1)]}
    berat = [x for x in result.issues if x.severity == "berat"]
    log(f"  cek visual: skor {result.score}/5, {len(berat)} masalah berat, "
        f"{len(result.issues) - len(berat)} ringan")
    for x in result.issues:
        log(f"    frame {x.frame} ({x.severity}): {x.problem}")
    return data


def save_review(data: dict, out_dir: Path) -> None:
    (out_dir / "visual_review.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def add_visual_checks(c, data: dict | None) -> None:
    """Butir checklist 'Cek visual AI'. Masalah berat wajib diperbaiki; ringan & error hanya catatan."""
    if not data:
        return
    if data.get("error"):
        c.add("Cek visual AI", "Video jadi dinilai AI", False, f"tidak tersedia: {data['error']}", required=False)
        return
    berat = [x for x in data.get("issues", []) if x["severity"] == "berat"]
    ringan = [x for x in data.get("issues", []) if x["severity"] == "ringan"]
    detail = f"skor {data['score']}/5"
    if berat:
        detail += "; " + "; ".join(f"frame {x['frame']}: {x['problem']}" for x in berat)
    c.add("Cek visual AI", "Tidak ada masalah berat di frame video jadi", not berat, detail)
    for x in ringan:
        c.add("Cek visual AI", f"Catatan frame {x['frame']}", False,
              x["problem"] + (f" — {x['fix']}" if x.get("fix") else ""), required=False)
