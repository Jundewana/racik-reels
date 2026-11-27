"""[4] Director — LLM menyusun EDL dari analisis + deskripsi + instruksi + pilar + style + hook + brand + tren.

Hasil divalidasi `validate.py`; bila ada error, Director diminta merevisi (maks 2 putaran).
Lalu [6] Critic menilai EDL dengan rubrik; skor rendah → Director merevisi (maks 2 putaran).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import yaml

from autoreels.analyze.moments import top_moments
from autoreels.analyze.models import Analysis, MusicInfo
from autoreels.critic import CriticReview, critique, revision_message
from autoreels.config import PATHS, load_brand, load_hooks, load_pillars, load_prompt, load_trend_brief
from autoreels.describe import SceneDescription
from autoreels.edl import EDL
from autoreels.llm import LLMClient
from autoreels.render.overlays import instagram_for
from autoreels.validate import ValidationResult, validate_edl

MAX_REVISIONS = 2        # revisi karena validasi gagal
MAX_CRITIC_ROUNDS = 2    # revisi atas catatan Critic


def build_messages(
    *,
    analysis: Analysis,
    descriptions: dict[str, SceneDescription],
    music: MusicInfo | None,
    brief: str,
    pillar: str,
    style_name: str,
    style: dict,
    duration: float,
    narration=None,
) -> list[dict]:
    """narration (edl.Narration): alur "narasi dulu" — satu segmen per frasa, prompt director_narasi."""
    pillar_key = pillar
    system = (
        load_prompt("director_narasi" if narration else "director")
        .replace("{{pillar_template}}", load_prompt(f"pillars/{pillar_key}"))
        .replace("{{edl_schema}}", load_prompt("edl_example"))
    )
    brand = load_brand()
    # satu baris per adegan (hemat token)
    scenes = []
    for s in analysis.usable_scenes():
        d = descriptions.get(s.scene_id)
        motion = "dinamis" if s.motion > 3 else "pelan" if s.motion > 0.7 else "diam"
        desc = "; ".join(x for x in [d.subject, d.action, d.setting, d.mood] if x) if d else "tidak diketahui"
        hook = d.hook_potential if d else 0
        rel = d.relevance_rental if d else 0
        text = f" | teks: {d.suggested_text}" if d and d.suggested_text else ""
        stage = f" | tahap={d.stage}" if d and d.stage else ""
        best = top_moments(s.moment_curve, s.start, s.end)
        moment = f" | momen terbaik={best}" if best else ""
        scenes.append(f"{s.scene_id} | {s.start:.2f}–{s.end:.2f} | {motion} | {desc} | hook={hook} | relevan={rel}"
                      f"{stage}{moment}{text}")
    trend = load_trend_brief()
    has_trend = any(line.strip().startswith("-") and "[ISI" not in line for line in trend.splitlines())
    context = {
        "instruksi": brief,
        "pilar": pillar,
        "target_durasi_detik": duration,
        "style_preset": {"nama": style_name, **style},
        "musik": {
            "mood": music.mood if music else "none",
            "tempo_bpm": music.tempo if music else None,
            "interval_beat_detik": round(music.beat_interval, 3) if music else None,
        },
        "adegan_tersedia": scenes,
        "pustaka_hook": [f"{h['type']}: {h['text']}" for h in load_hooks().get(pillar, [])],
        "brand": {
            "nama": brand.get("company_name"),
            "instagram": instagram_for(brand, pillar),
            "whatsapp": brand.get("whatsapp", {}).get("display"),
            "gaya_bahasa": brand.get("language_style"),
            "boleh_sisipan_sunda": brand.get("allow_sundanese_light", False),
            "harga_sewa_per_hari": brand.get("pricing", {}).get("rental_per_day"),
            "layanan_rental_terkonfirmasi": brand.get("rental_services") if pillar == "rental" else None,
            "cta_default": brand.get("default_cta", {}).get(pillar),
        },
        "brief_tren": trend if has_trend else "(belum diisi minggu ini — abaikan tren)",
    }
    keywords = load_pillars().get(pillar, {}).get("keywords") or []
    if keywords:
        context["keyword_seo_caption"] = keywords
    from autoreels.preferences import for_director

    prefs = for_director()
    if prefs:
        context["preferensi_pemilik"] = prefs
    guide_file = PATHS["config"] / "caption_guide.md"
    if guide_file.exists() and guide_file.read_text(encoding="utf-8").strip():
        context["panduan_caption"] = guide_file.read_text(encoding="utf-8")
    pace = style.get("cut_pace_sec", [1.0, 2.0])
    avg = (pace[0] + pace[1]) / 2
    n_mid = max(3, round((duration - 2.5 - 3.0) / avg))
    context["panduan_jumlah_segmen"] = (
        f"Sekitar {n_mid + 2} segmen: 1 hook (±2 dtk) + ±{n_mid} segmen isi (±{avg:.1f} dtk) + 1 CTA (±3 dtk). "
        f"Jumlah durasi tampil semua segmen HARUS ≈ {duration} dtk."
    )
    style_ctx = {k: v for k, v in style.items() if k in (
        "cut_pace_sec", "transitions", "zoom_punch_on_emphasis", "music_mood_default", "speed_range",
        "default_speed_progress")}
    context["style_preset"] = {"nama": style_name, **style_ctx}
    if narration is not None:  # tempo mengikuti narasi, bukan ketukan musik / panduan jumlah segmen
        context.pop("panduan_jumlah_segmen", None)
        context["musik"] = {"mood": music.mood if music else "none", "catatan": "diturunkan di bawah narasi"}
        context["target_durasi_detik"] = round(narration.duration, 2)
        context["jumlah_segmen_wajib"] = len(narration.phrases)
        if narration.speaker_clip:  # video bicara: segmen pembicara dikunci kode ke waktu ucapan aslinya
            code = next((s.scene_id.split("-")[0] for s in analysis.scenes
                         if s.source_file == narration.speaker_clip), "?")
            context["video_bicara"] = {
                "klip_pembicara": code,
                "aturan": (f"Narasi = suara pembicara di klip {code}. Untuk menampilkan wajahnya, isi segmen dengan "
                           f"source_file \"{code}\" dan scene_id klip itu (start/end diatur kode agar bibir sinkron). "
                           "Minimal 60% segmen menampilkan pembicara, termasuk hook (P1) dan segmen terakhir. "
                           "Sisipkan b-roll (adegan klip lain) hanya pada frasa yang isinya bisa digambarkan "
                           "b-roll itu, maks 2 segmen berurutan. Tanpa b-roll yang cocok → semua segmen pembicara."),
            }
            from autoreels.talk import broll_suggestions

            saran = broll_suggestions(narration.phrases, analysis.usable_scenes(), descriptions,
                                      narration.speaker_clip, cold_open_sec=narration.cold_open_sec)
            context["video_bicara"]["saran_broll"] = saran or (
                "tidak ada adegan lain yang cocok dengan ucapan → semua segmen menampilkan pembicara")
            if saran:
                context["video_bicara"]["aturan"] += (
                    " `saran_broll` = frasa yang menyebut hal yang terlihat di adegan lain (dicocokkan kode dari kata "
                    "yang sama); pakai bila memang menggambarkan ucapannya. Jangan sisipkan b-roll di frasa lain.")
            if narration.cold_open_sec > 0:
                n = sum(1 for p in narration.phrases if p.start < narration.cold_open_sec - 0.01)
                context["video_bicara"]["cold_open"] = (
                    f"P1–P{n} (0–{narration.cold_open_sec:.1f} dtk) = cold open: ucapan paling menohok yang diputar "
                    "di depan lalu terdengar lagi di tempat aslinya. Teks hook di layar harus MELENGKAPI ucapan ini "
                    "(topik/janji isi video, mis. pertanyaan pemancing), bukan mengulang kata-katanya.")
        context["narasi_frasa"] = [f"P{i + 1} | {p.start:.2f}–{p.end:.2f} ({p.duration:.2f} dtk) | {p.text}"
                                    for i, p in enumerate(narration.phrases)]
    user = "Buat EDL untuk data berikut.\n\n" + yaml.safe_dump(context, allow_unicode=True, sort_keys=False)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


@dataclass
class DirectorResult:
    validation: ValidationResult          # EDL terpilih (lolos validasi bila memungkinkan)
    revisions: int                        # revisi karena validasi gagal (EDL awal)
    reviews: list[CriticReview] = field(default_factory=list)  # penilaian Critic tiap putaran
    chosen_round: int | None = None       # putaran Critic yang EDL-nya dipakai
    critic_revisions: int = 0             # revisi yang diminta Critic

    @property
    def review(self) -> CriticReview | None:
        return next((r for r in self.reviews if r.round == self.chosen_round), None)

    def critic_dict(self) -> dict | None:
        if not self.reviews:
            return None
        return {"chosen_round": self.chosen_round, "critic_revisions": self.critic_revisions,
                "final": self.review.to_dict() if self.review else None,
                "rounds": [r.to_dict() for r in self.reviews]}


def _director_loop(
    *, llm: LLMClient, model: str, messages: list[dict], analysis: Analysis, descriptions: dict,
    music: MusicInfo | None, style: dict, brand: dict, hashtags: list[str], narration, log, progress,
    label: str, purpose: str, attempts: int = MAX_REVISIONS + 1,
) -> tuple[ValidationResult, int, list[dict]]:
    """Minta EDL lalu validasi; bila gagal, kirim error ke Director (sampai `attempts` kali).
    Kembalikan (hasil validasi terakhir, jumlah revisi, percakapan sebelum EDL terakhir)."""
    result: ValidationResult | None = None
    attempt = 0
    for attempt in range(attempts):
        if progress:
            progress.update(attempt, attempts, label if attempt == 0 else f"{label} (perbaikan ke-{attempt})")
        edl = llm.complete_structured(messages, EDL, model=model, purpose=f"{purpose}#{attempt + 1}")
        if narration is not None:  # data narasi selalu dari kode, bukan dari LLM
            edl.narration = narration.model_copy(deep=True)
            edl.target_duration_sec = round(narration.duration, 2)
        result = validate_edl(edl, analysis, style, music, brand, hashtags, descriptions)
        if result.ok:
            break
        log(f"  validasi gagal ({len(result.errors)} masalah), minta revisi ke Director …")
        for e in result.errors:
            log(f"    - {e}")
        if attempt < attempts - 1:
            messages = messages + [
                {"role": "assistant", "content": edl.model_dump_json(exclude={"narration"})},
                {"role": "user", "content": (
                    "EDL di atas melanggar aturan berikut. Perbaiki SEMUA dan kirim ulang EDL lengkap (JSON saja):\n- "
                    + "\n- ".join(result.errors)
                    + (f"\n\nInfo: interval beat {music.beat_interval:.3f} dtk." if music else "")
                )},
            ]
    assert result is not None
    return result, attempt, messages


def direct(
    *,
    llm: LLMClient,
    model: str,
    analysis: Analysis,
    descriptions: dict[str, SceneDescription],
    music: MusicInfo | None,
    brief: str,
    pillar: str,
    style_name: str,
    style: dict,
    duration: float,
    log=print,
    progress=None,
    narration=None,
    critic_rounds: int = MAX_CRITIC_ROUNDS,
    critic_model: str | None = None,
) -> DirectorResult:
    """Director menyusun EDL (+ revisi validasi), lalu Critic menilai dan Director merevisi maks `critic_rounds`
    kali. EDL dengan skor Critic tertinggi yang lolos validasi dipakai. narration → alur "narasi dulu"."""
    messages = build_messages(
        analysis=analysis, descriptions=descriptions, music=music, brief=brief,
        pillar=pillar, style_name=style_name, style=style, duration=duration, narration=narration,
    )
    brand = load_brand()
    hashtags = load_pillars().get(pillar, {}).get("hashtags", [])
    common = dict(llm=llm, model=model, analysis=analysis, descriptions=descriptions, music=music, style=style,
                  brand=brand, hashtags=hashtags, narration=narration, log=log, progress=progress)
    result, revisions, messages = _director_loop(messages=messages, label="menyusun EDL", purpose="director",
                                                 **common)
    out = DirectorResult(validation=result, revisions=revisions)
    if critic_rounds < 0 or not result.ok:  # -1 = Critic mati; 0 = nilai saja (tanpa revisi)
        return out  # EDL yang belum lolos aturan keras tidak dinilai (dicatat sebagai error validasi)

    versions: dict[int, ValidationResult] = {0: result}
    for rnd in range(critic_rounds + 1):
        if progress:
            progress.update(rnd, critic_rounds + 1, f"Critic menilai edit (putaran {rnd + 1})")
        review = critique(llm=llm, model=critic_model or model, edl=result.edl, descriptions=descriptions, stats=result.stats,
                          brief=brief, pillar=pillar, style_name=style_name, style=style, brand=brand,
                          round_no=rnd, log=log)
        if review is None:
            break
        out.reviews.append(review)
        if review.passed or rnd == critic_rounds:
            break
        log(f"  Director merevisi sesuai catatan Critic (revisi ke-{rnd + 1}) …")
        msgs = messages + [
            {"role": "assistant", "content": result.edl.model_dump_json(exclude={"narration"})},
            {"role": "user", "content": revision_message(review)},
        ]
        new, _, new_msgs = _director_loop(messages=msgs, label=f"revisi dari Critic ke-{rnd + 1}",
                                          purpose=f"director_critic{rnd + 1}", attempts=2, **common)
        out.critic_revisions += 1
        if not new.ok:
            log("  [peringatan] revisi dari Critic melanggar aturan keras — versi sebelumnya dipakai.")
            break
        result, messages = new, new_msgs
        versions[rnd + 1] = new

    if out.reviews:  # pilih versi terbaik: lolos dulu, lalu skor hook, lalu rata-rata
        best = max(out.reviews, key=lambda r: (r.passed, r.hook, r.average, r.round))
        out.chosen_round = best.round
        out.validation = versions[best.round]
        if best.round != out.reviews[-1].round:
            log(f"  dipakai EDL putaran {best.round + 1} (skor Critic tertinggi).")
    return out


def dump_descriptions(descriptions: dict[str, SceneDescription]) -> str:
    return json.dumps({k: v.model_dump() for k, v in descriptions.items()}, ensure_ascii=False, indent=2)
