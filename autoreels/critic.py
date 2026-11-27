"""[6] Critic — LLM kedua menilai EDL dengan rubrik 1–5 dan memberi catatan revisi untuk Director.

Loop revisi (maks 2 putaran) dijalankan oleh `director.direct`. Critic hanya menilai; aturan keras tetap milik
`validate.py` dan Checklist Siap Unggah.
"""

from __future__ import annotations

from dataclasses import dataclass

import yaml
from pydantic import BaseModel, Field

from autoreels.config import load_hooks, load_pillars, load_prompt
from autoreels.edl import EDL
from autoreels.llm import LLMClient
from autoreels.render.overlays import instagram_for

PASS_AVERAGE = 4.0   # rata-rata minimal agar tidak perlu revisi
PASS_HOOK = 4        # skor hook minimal (syarat Checklist Siap Unggah)

LABELS = {
    "hook": "Kekuatan hook",
    "instruction_fit": "Kesesuaian instruksi & pilar",
    "flow": "Alur / koherensi",
    "pace": "Tempo sesuai style",
    "text_readability": "Keterbacaan teks",
    "cta": "Kejelasan CTA",
    "brand": "Konsistensi brand",
}


def _opening_speech(narration) -> str:
    """Ucapan yang terdengar di detik pertama: seluruh cold open, atau frasa pertama."""
    if narration.cold_open_sec > 0:
        return " ".join(p.text for p in narration.phrases if p.start < narration.cold_open_sec - 0.01)
    return narration.phrases[0].text

def _score() -> int:
    return Field(..., ge=1, le=5)


class CriticScores(BaseModel):
    hook: int = _score()
    instruction_fit: int = _score()
    flow: int = _score()
    pace: int = _score()
    text_readability: int = _score()
    cta: int = _score()
    brand: int = _score()


class CriticOutput(BaseModel):
    scores: CriticScores
    hook_comment: str = ""
    revision_notes: list[str] = Field(default_factory=list)
    summary: str = ""


@dataclass
class CriticReview:
    round: int          # 0 = EDL awal, 1..n = setelah revisi ke-n
    output: CriticOutput
    model: str = ""

    @property
    def average(self) -> float:
        s = self.output.scores.model_dump()
        return round(sum(s.values()) / len(s), 2)

    @property
    def hook(self) -> int:
        return self.output.scores.hook

    @property
    def passed(self) -> bool:
        return self.average >= PASS_AVERAGE and self.hook >= PASS_HOOK

    def weak(self) -> list[str]:
        return [LABELS[k] for k, v in self.output.scores.model_dump().items() if v < PASS_HOOK]

    def to_dict(self) -> dict:
        return {"round": self.round, "model": self.model, "average": self.average, "hook": self.hook,
                "passed": self.passed, **self.output.model_dump()}

    @classmethod
    def from_dict(cls, d: dict) -> CriticReview:
        out = CriticOutput(scores=d["scores"], hook_comment=d.get("hook_comment", ""),
                           revision_notes=d.get("revision_notes", []), summary=d.get("summary", ""))
        return cls(round=d.get("round", 0), output=out, model=d.get("model", ""))


def _scene_text(desc) -> str:
    if desc is None:
        return "tidak diketahui"
    parts = [desc.subject, desc.action, desc.setting, desc.mood]
    stage = f", tahap {desc.stage}" if getattr(desc, "stage", None) else ""
    return "; ".join(p for p in parts if p) + f" (hook={desc.hook_potential}{stage})"


def build_critic_messages(
    *, edl: EDL, descriptions: dict, stats: dict, brief: str, pillar: str, style_name: str, style: dict,
    brand: dict,
) -> list[dict]:
    pillar_cfg = load_pillars().get(pillar, {})
    price = brand.get("pricing", {}).get("rental_per_day")
    if price and "[" in str(price):  # placeholder di brand.yaml = harga belum diisi → jangan dijadikan saran
        price = None
    t = 0.0
    segments = []
    for s in edl.segments:
        dur = s.output_duration
        speed = f" | dipercepat x{s.speed:g}" if s.speed != 1 else ""
        text = f" | teks: \"{s.overlay_text}\"" if s.overlay_text else ""
        compare = (f" | before–after: sebelum = adegan {s.compare.scene_id}: "
                   f"{_scene_text(descriptions.get(s.compare.scene_id))} → sesudah = adegan di atas (wipe + label)"
                   if s.compare else "")
        speaker = edl.narration.speaker_clip if edl.narration is not None else None
        what = ("PEMBICARA (terkunci ke ucapannya, sinkron bibir — tidak bisa diganti adegan lain)"
                if speaker and s.source_file == speaker
                else f"adegan {s.scene_id}: {_scene_text(descriptions.get(s.scene_id))}")
        segments.append(f"#{s.index} {s.role.value} | {t:.1f}–{t + dur:.1f} dtk | {s.transition_in.value}{speed} | "
                        f"{what}{compare}{text}")
        t += dur
    used = {s.scene_id for s in edl.segments}
    speaker_scenes = ({s.scene_id for s in edl.segments if s.source_file == edl.narration.speaker_clip}
                      if edl.narration is not None and edl.narration.speaker_clip else set())
    speaker_prefixes = {sid.split("-")[0] for sid in speaker_scenes}
    others = sorted(((sid, d) for sid, d in descriptions.items()
                     if sid not in used and sid.split("-")[0] not in speaker_prefixes),
                    key=lambda x: -x[1].hook_potential)[:12]
    best_hook = max((d.hook_potential for d in descriptions.values()), default=0)
    context = {
        "instruksi": brief,
        "pilar": {"nama": pillar, "tujuan": pillar_cfg.get("goal"), "audiens": pillar_cfg.get("audience"),
                  "struktur_naratif": pillar_cfg.get("narrative")},
        "style_preset": {"nama": style_name, **{k: v for k, v in style.items() if k in (
            "cut_pace_sec", "transitions", "music_mood_default", "speed_range", "zoom_punch_on_emphasis")}},
        "brand": {
            "nama": brand.get("company_name"), "instagram": instagram_for(brand, pillar),
            "whatsapp": brand.get("whatsapp", {}).get("display"), "gaya_bahasa": brand.get("language_style"),
            "harga_sewa_per_hari": price or "(belum diisi — jangan sarankan teks harga)",
            "keunggulan_terkonfirmasi": brand.get("rental_services") if pillar == "rental" else None,
        },
        "hook": {"tipe": edl.hook.type.value, "teks": edl.hook.overlay_text,
                 **({"ucapan_pembuka": _opening_speech(edl.narration)} if speaker_scenes else
                    {"hook_potential_tertinggi_tersedia": best_hook})},
        "segmen": segments,
        "cta": {"teks": edl.cta.text if edl.cta else None, "muncul_detik": edl.cta.at_sec if edl.cta else None},
        "musik_mood": edl.music.mood.value,
        "caption": edl.caption_suggestion,
        "hashtag": edl.hashtags,
        "adegan_lain_yang_tersedia": [f"{sid}: {_scene_text(d)}" for sid, d in others],
        "pustaka_hook": [f"{h['type']}: {h['text']}" for h in load_hooks().get(pillar, [])
                         if price or "[" not in h["text"]][:15],
        "fakta_otomatis": {k: stats.get(k) for k in (
            "total_duration", "hook_duration", "segments", "beat_accuracy", "pace_ratio") if k in stats},
    }
    context["fakta_otomatis"]["target_durasi"] = edl.target_duration_sec
    if edl.narration is not None:  # tempo & jumlah segmen ditentukan narasi, bukan style
        for k in ("cut_pace_sec", "speed_range"):
            context["style_preset"].pop(k, None)
        context["fakta_otomatis"].pop("pace_ratio", None)
        context["fakta_otomatis"].pop("beat_accuracy", None)
        context["alur"] = ("narasi dulu: segmen i = frasa narasi i, durasi = lama frasa, speed 1, subtitle karaoke "
                           "(jumlah & durasi segmen TETAP)")
        context["narasi_frasa"] = [f"P{i + 1} → segmen #{i} | {p.text}" for i, p in enumerate(edl.narration.phrases)]
        if edl.narration.speaker_clip:
            context["alur"] += ("; video_bicara: suara & wajah pembicara asli (segmen pembicara terkunci ke ucapannya, "
                                "visual hook = pembicara)")
            if edl.narration.cold_open_sec > 0:
                context["alur"] += (f"; detik 0–{edl.narration.cold_open_sec:.1f} = cold open (cuplikan ucapan terkuat, "
                                    "diulang di tempat aslinya — disengaja). Nilai hook dari gabungan ucapan_pembuka "
                                    "+ teks hook di layar")
    context["tujuan_video"] = edl.purpose.value + (" — tanpa CTA, nilai `cta` dari penutupnya"
                                                   if edl.purpose.value == "informasi" else "")
    user = "Nilai EDL berikut.\n\n" + yaml.safe_dump(context, allow_unicode=True, sort_keys=False, width=200)
    return [{"role": "system", "content": load_prompt("critic")}, {"role": "user", "content": user}]


def critique(
    *, llm: LLMClient, model: str, edl: EDL, descriptions: dict, stats: dict, brief: str, pillar: str,
    style_name: str, style: dict, brand: dict, round_no: int = 0, log=print,
) -> CriticReview | None:
    """Nilai satu EDL. Gagal (LLM error) → None; job tetap jalan, checklist mencatat Critic tidak berjalan."""
    messages = build_critic_messages(edl=edl, descriptions=descriptions, stats=stats, brief=brief, pillar=pillar,
                                     style_name=style_name, style=style, brand=brand)
    try:
        out = llm.complete_structured(messages, CriticOutput, model=model, purpose=f"critic#{round_no + 1}")
    except Exception as e:  # noqa: BLE001 — Critic bersifat penilai, kegagalannya tidak boleh menggagalkan job
        log(f"  [peringatan] Critic gagal: {e}")
        return None
    review = CriticReview(round=round_no, output=out, model=model)
    s = out.scores
    log(f"  Critic (putaran {round_no + 1}): rata-rata {review.average:.1f}, hook {s.hook}"
        + (" — lolos" if review.passed else f" — lemah: {', '.join(review.weak()) or 'rata-rata < 4'}"))
    return review


def revision_message(review: CriticReview) -> str:
    notes = review.output.revision_notes or [f"Perbaiki aspek: {', '.join(review.weak())}."]
    scores = ", ".join(f"{LABELS[k]} {v}" for k, v in review.output.scores.model_dump().items())
    return (
        f"Critic menilai EDL di atas (skor 1–5: {scores}; rata-rata {review.average:.1f}). Catatan revisi:\n- "
        + "\n- ".join(notes)
        + "\n\nRevisi EDL sesuai catatan tersebut. Tetap patuhi SEMUA aturan sebelumnya (durasi, hook ≤ 3 dtk, "
          "hanya scene_id yang tersedia, tanpa mengarang fakta). Kirim ulang EDL lengkap (JSON saja)."
    )


def markdown(reviews: list[CriticReview], chosen: int | None) -> str:
    """Tabel skor tiap putaran untuk report.md."""
    if not reviews:
        return "Critic tidak berjalan."
    head = "| Aspek | " + " | ".join(f"Putaran {r.round + 1}" + (" ✔" if r.round == chosen else "")
                                     for r in reviews) + " |"
    rows = [head, "|---|" + "---|" * len(reviews)]
    for k, label in LABELS.items():
        rows.append(f"| {label} | " + " | ".join(str(getattr(r.output.scores, k)) for r in reviews) + " |")
    rows.append("| **Rata-rata** | " + " | ".join(f"**{r.average:.1f}**" for r in reviews) + " |")
    final = next((r for r in reviews if r.round == chosen), reviews[-1])
    lines = rows + ["", f"Ringkasan: {final.output.summary or '-'}"]
    if final.output.hook_comment:
        lines.append(f"Hook: {final.output.hook_comment}")
    if final.output.revision_notes:
        lines += ["", "Catatan tersisa:", *[f"- {n}" for n in final.output.revision_notes]]
    return "\n".join(lines)
