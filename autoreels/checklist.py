"""Checklist Siap Unggah — dicek oleh kode terhadap hasil render & EDL (lihat CLAUDE.md bagian 1).

Status job: `siap_unggah` bila semua butir wajib lolos, selain itu `perlu_tinjau`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from autoreels.analyze.models import Analysis
from autoreels.edl import EDL, Transition
from autoreels.media import probe, run_ffmpeg_stderr
from autoreels.render.overlays import text_events
from autoreels.render.text_ass import HOOK_SIZE, fit_text
from autoreels.validate import PLACEHOLDER_RE, ValidationResult


@dataclass
class CheckItem:
    group: str
    name: str
    passed: bool
    detail: str = ""
    required: bool = True


@dataclass
class Checklist:
    items: list[CheckItem] = field(default_factory=list)

    def add(self, group: str, name: str, passed: bool, detail: str = "", required: bool = True) -> None:
        self.items.append(CheckItem(group, name, bool(passed), detail, required))

    @property
    def status(self) -> str:
        return "siap_unggah" if all(i.passed for i in self.items if i.required) else "perlu_tinjau"

    def failed(self) -> list[CheckItem]:
        return [i for i in self.items if i.required and not i.passed]

    def markdown(self) -> str:
        rows = ["| Aspek | Butir | Hasil | Detail |", "|---|---|---|---|"]
        for i in self.items:
            mark = "✅" if i.passed else ("❌" if i.required else "⚠️")
            rows.append(f"| {i.group} | {i.name} | {mark} | {i.detail} |")
        return "\n".join(rows)


def add_video_checks(c: Checklist, reel: Path, target: float | None, silent_ok: bool = False) -> None:
    """Butir 'Video jadi'. target=None → cukup cek durasi wajar untuk Reels (3–90 dtk)."""
    info = probe(reel)
    c.add("Video jadi", "Resolusi 1080×1920", (info.width, info.height) == (1080, 1920), f"{info.width}×{info.height}")
    c.add("Video jadi", "30 fps", abs(info.fps - 30) < 0.1, f"{info.fps} fps")
    c.add("Video jadi", "Ada audio (AAC)", info.has_audio, "ada" if info.has_audio else "tidak ada")
    if target:
        ok_dur = abs(info.duration - target) <= target * 0.10
        c.add("Video jadi", "Durasi target ±10%", ok_dur, f"{info.duration:.1f} dtk (target {target:.0f})")
    else:
        c.add("Video jadi", "Durasi wajar untuk Reels (3–90 dtk)", 3 <= info.duration <= 90,
              f"{info.duration:.1f} dtk")

    err = run_ffmpeg_stderr(["-i", str(reel), "-vf", "blackdetect=d=0.4:pix_th=0.08", "-an", "-f", "null", "-"])
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)
    c.add("Video jadi", "Tanpa frame hitam", not blacks,
          "tidak ada" if not blacks else ", ".join(f"{float(a):.1f}–{float(b):.1f}s" for a, b in blacks))

    err = run_ffmpeg_stderr(["-i", str(reel), "-vf", "freezedetect=n=0.0005:d=2", "-an", "-f", "null", "-"])
    freezes = re.findall(r"freeze_start: ([\d.]+)", err)
    c.add("Video jadi", "Tanpa video beku > 2 dtk", not freezes,
          "tidak ada" if not freezes else f"beku mulai {', '.join(freezes)} dtk")

    err = run_ffmpeg_stderr(["-i", str(reel), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    i_val = float(lufs[-1]) if lufs else None
    p_val = float(peak[-1]) if peak else None
    if silent_ok:  # video senyap disengaja (tanpa musik, tanpa suara): loudness tidak berlaku
        c.add("Video jadi", "Audio senyap (tanpa musik dipilih)", True, "tambahkan musik/audio trending saat unggah",
              required=False)
    else:
        c.add("Video jadi", "Loudness ≈ −14 LUFS", i_val is not None and -16.0 <= i_val <= -12.0,
              f"{i_val} LUFS" if i_val is not None else "tidak terukur")
    c.add("Video jadi", "Tanpa clipping (true peak ≤ −1 dBTP)", p_val is not None and p_val <= -0.9,
          f"{p_val} dBTP" if p_val is not None else "tidak terukur")


def add_voice_checks(c: Checklist, edl: EDL, voice) -> None:
    """Butir 'Voice over' (hanya bila voice over diaktifkan di EDL)."""
    mode = edl.voiceover.mode.value
    if mode == "none":
        return
    label = "rekaman suara" if mode == "rekam" else "suara AI"
    has = bool(voice and voice.path)
    detail = f"{label}, {len(edl.voiceover.lines)} baris naskah" if has else (
        "menunggu rekaman — rekam/unggah di halaman Hasil" if mode == "rekam" else "suara AI gagal dibuat")
    c.add("Voice over", "Voice over tersedia", has, detail)
    if not has:
        return
    loud = voice.loudness
    c.add("Voice over", "Suara terdengar (tidak senyap)", loud is not None and loud > -35,
          f"{loud:.1f} LUFS" if loud is not None else "tidak terukur")
    over = next((w for w in voice.warnings if "melewati akhir" in w), None)
    c.add("Voice over", "Selesai sebelum video habis", over is None,
          "ok" if over is None else over.replace("Voice over ", "").rstrip("."))
    if voice.warnings:
        c.add("Voice over", "Catatan naskah/rekaman", False, "; ".join(voice.warnings)[:200], required=False)


def add_privacy_checks(c: Checklist, edl: EDL, privacy) -> None:
    """Blur privasi bersifat bantuan: dicatat (tidak wajib) agar peninjau memeriksa ulang secara manual."""
    p = edl.privacy
    if not (p.blur_faces or p.blur_plates):
        return
    if privacy is None:
        c.add("Privasi", "Blur privasi dijalankan", False, "tidak berjalan (model/video tidak tersedia)", required=False)
        return
    if p.blur_faces:
        c.add("Privasi", "Wajah disamarkan", True,
              f"terdeteksi di {privacy.face_frames} dari {privacy.frames} frame — periksa manual", required=False)
    if p.blur_plates:
        c.add("Privasi", "Pelat nomor disamarkan", True,
              f"terdeteksi di {privacy.plate_frames} dari {privacy.frames} frame — periksa manual (pelat kecil/miring "
              "bisa terlewat)", required=False)


def add_critic_checks(c: Checklist, critic: dict | None) -> None:
    """Skor hook Critic ≥ 4 wajib (CLAUDE.md). Bila Critic tidak berjalan, dicatat sebagai catatan (tidak memblokir)."""
    from autoreels.critic import LABELS, PASS_AVERAGE, PASS_HOOK

    final = (critic or {}).get("final")
    if not final:
        c.add("Hook benar", "Skor hook dari Critic ≥ 4", False,
              "Critic tidak berjalan (dilewati atau gagal) — nilai hook secara manual", required=False)
        return
    c.add("Hook benar", "Skor hook dari Critic ≥ 4", final["hook"] >= PASS_HOOK,
          f"{final['hook']}/5" + (f" — {final['hook_comment']}" if final.get("hook_comment") else ""))
    weak = [f"{LABELS.get(k, k)} {v}" for k, v in final.get("scores", {}).items() if v < PASS_HOOK and k != "hook"]
    c.add("Kualitas edit (Critic)", f"Rata-rata skor Critic ≥ {PASS_AVERAGE:g}", final["average"] >= PASS_AVERAGE,
          f"{final['average']:.1f}/5" + (f" — lemah: {', '.join(weak)}" if weak else ""), required=False)


def build_checklist(
    *,
    edl: EDL,
    analysis: Analysis,
    validation: ValidationResult,
    style: dict,
    brand: dict,
    reel: Path,
    descriptions: dict,
    caption_file: Path,
    cover: Path,
    font_file: Path,
    voice=None,
    privacy=None,
    critic: dict | None = None,
) -> Checklist:
    c = Checklist()
    silent = (edl.music.mood.value == "none" and edl.narration is None and edl.voiceover.mode.value == "none"
              and not any(s.keep_original_audio for s in edl.segments))
    add_video_checks(c, reel, edl.target_duration_sec, silent_ok=silent)
    add_privacy_checks(c, edl, privacy)
    unusable = {s.scene_id for s in analysis.scenes if not s.usable}
    speaker = edl.narration.speaker_clip if edl.narration is not None else None
    used_bad = [s.scene_id for s in edl.segments if s.scene_id in unusable and s.source_file != speaker]
    c.add("Video jadi", "Tanpa adegan unusable", not used_bad, ", ".join(used_bad) or "bersih")
    if speaker:  # video bicara: ucapan tidak bisa dilewati, jadi kualitas gambar pembicara hanya dicatat
        weak = sorted({s.scene_id for s in edl.segments if s.scene_id in unusable and s.source_file == speaker})
        if weak:
            c.add("Video jadi", "Gambar pembicara cukup tajam/terang", False,
                  f"adegan {', '.join(weak)} di bawah ambang kualitas — periksa manual", required=False)

    # --- hook ---
    hook_seg = edl.segments[0]
    events = text_events(edl, brand)
    hook_ev = next((e for e in events if e.kind == "hook"), None)
    c.add("Hook benar", "Segmen pertama ≤ 3 dtk", hook_seg.output_duration <= 3.0 + 1e-3,
          f"{hook_seg.output_duration:.2f} dtk")
    c.add("Hook benar", "Teks hook muncul di detik 0", bool(hook_ev and hook_ev.start == 0), edl.hook.overlay_text or "-")
    c.add("Hook benar", "Teks hook terbaca ≥ 1,5 dtk", bool(hook_ev and hook_ev.end - hook_ev.start >= 1.5),
          f"{(hook_ev.end - hook_ev.start):.1f} dtk" if hook_ev else "-")
    hook_lines, hook_size = fit_text(edl.hook.overlay_text or "", HOOK_SIZE, 14)
    c.add("Hook benar", "Teks hook cukup besar (≥ 90 px, ≤ 2 baris)", hook_size >= 90 and len(hook_lines) <= 2,
          f"{hook_size} px, {len(hook_lines)} baris")
    potentials = {sid: getattr(d, "hook_potential", 0) for sid, d in descriptions.items()}
    best = max(potentials.values(), default=0)
    mine = potentials.get(hook_seg.scene_id, 0)
    if edl.narration is not None and edl.narration.speaker_clip == hook_seg.source_file:
        c.add("Hook benar", "Visual hook = pembicara (sinkron dengan ucapan pembuka)", True, "video bicara")
    else:
        c.add("Hook benar", "Visual hook = adegan hook_potential tertinggi", mine >= best - 1,
              f"adegan {hook_seg.scene_id}: {mine}/5 (tertinggi {best}/5)")
    add_critic_checks(c, critic)

    # --- style ---
    allowed = set(style.get("transitions", ["cut"]))
    bad_tr = [s.index for s in edl.segments if s.transition_in.value not in allowed]
    c.add("Style benar", "Transisi sesuai preset", not bad_tr, f"preset: {', '.join(sorted(allowed))}")
    from autoreels.validate import RENDERABLE_TRANSITIONS

    unsupported = [s.index for s in edl.segments if s.transition_in not in RENDERABLE_TRANSITIONS]
    c.add("Style benar", "Semua transisi bisa dirender", not unsupported,
          "ok" if not unsupported else f"segmen {unsupported} memakai transisi yang tidak dikenal", required=False)
    pace = validation.stats.get("pace_ratio", 0) or 0
    if edl.narration is not None:  # alur narasi: tempo = frasa narasi, bukan cut_pace_sec style
        n_ph, n_seg = len(edl.narration.phrases), len(edl.segments)
        c.add("Style benar", "Satu potongan per frasa narasi", n_ph == n_seg, f"{n_seg} segmen, {n_ph} frasa")
    else:
        c.add("Style benar", "Tempo potongan sesuai preset", pace >= 0.6,
              f"{pace:.0%} segmen dalam {style.get('cut_pace_sec')} dtk")
    if edl.music.mood.value == "none":
        c.add("Style benar", "Musik latar", True, "tanpa musik (pilihan pengguna)")
    else:
        c.add("Style benar", "Mood musik sesuai preset", edl.music.mood.value == style.get("music_mood_default"),
              edl.music.mood.value)
    music = analysis.music
    has_music = bool(music and Path(music.path).exists())
    if edl.music.mood.value != "none":
        c.add("Style benar", "Ada musik latar", has_music,
              Path(music.path).name if has_music else "tidak ada lagu di assets/music/ — tambahkan lagu bebas royalti")
        if has_music and music.mood != style.get("music_mood_default"):
            want = style.get("music_mood_default")
            c.add("Style benar", "Lagu dari folder mood style", False,
                  f"folder '{want}' kosong → pakai lagu '{music.mood}'; isi assets/music/{want}/", required=False)
    beat = validation.stats.get("beat_accuracy")
    if edl.narration is not None:
        nar = edl.narration
        c.add("Teks & brand", "Narasi & subtitle karaoke", bool(nar.words) and (reel.parent / nar.file).exists(),
              f"{len(nar.words)} kata, {nar.duration:.1f} dtk")
    elif edl.music.mood.value == "none":
        c.add("Style benar", "Potongan jatuh di beat", True, "tanpa musik — tempo mengikuti gaya", required=False)
    else:
        c.add("Style benar", "Potongan jatuh di beat (≥ 80%)", beat is not None and beat >= 0.8,
              f"{beat:.0%}" if beat is not None else ("ketukan musik tidak terdeteksi" if has_music else "tanpa musik"))
    c.add("Style benar", "Font preset tersedia", font_file.exists(), font_file.name)
    if style.get("zoom_punch_on_emphasis") and "zoom_punch" in style.get("transitions", []):
        zp = sum(s.transition_in == Transition.zoom_punch for s in edl.segments)
        c.add("Style benar", "Zoom-punch dipakai", zp > 0, f"{zp} kali")

    # --- voice over ---
    add_voice_checks(c, edl, voice)

    # --- teks & brand ---
    texts = [edl.hook.overlay_text or "", edl.cta.text if edl.cta else "", edl.caption_suggestion,
             *[s.overlay_text or "" for s in edl.segments]]
    ph = [t for t in texts if PLACEHOLDER_RE.search(t)]
    c.add("Teks & brand", "Tanpa placeholder tersisa", not ph, "; ".join(ph) or "bersih")
    wa = brand.get("whatsapp", {}).get("display", "")
    if edl.purpose.value == "promosi":
        c.add("Teks & brand", "CTA tampil", any(e.kind == "cta" for e in events), edl.cta.text if edl.cta else "-")
        c.add("Teks & brand", "Nomor WhatsApp di layar", any(wa and wa in e.text for e in events), wa)
    else:
        c.add("Teks & brand", "Video informasi: tanpa CTA jualan", not any(e.kind == "cta" for e in events),
              "penutup tanpa ajakan booking (tujuan: informasi)")
    if edl.branding.logo:
        c.add("Teks & brand", "Watermark tampil", True, edl.branding.position.value)
    else:
        c.add("Teks & brand", "Tanpa watermark", True, "dimatikan pengguna", required=False)

    # --- siap posting ---
    cap = caption_file.read_text(encoding="utf-8") if caption_file.exists() else ""
    cap_len = len((edl.caption_suggestion or "").strip())
    c.add("Siap posting", "Caption + hashtag tersedia", cap_len >= 40 and "#" in cap,
          f"caption {cap_len} huruf" if cap_len >= 40 else "caption kosong/terlalu pendek — tulis di caption.txt")
    c.add("Siap posting", "Cover tersedia", cover.exists(), cover.name)
    c.add("Siap posting", "Validasi EDL tanpa error", validation.ok,
          "ok" if validation.ok else f"{len(validation.errors)} error")
    return c
