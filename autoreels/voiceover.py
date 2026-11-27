"""Voice over: naskah (ditulis AI, ditinjau manusia), suara AI (Gemini TTS), atau rekaman manusia.

Hasil akhirnya satu track `vo.wav` sepanjang video + waktu tiap baris (untuk subtitle), yang
kemudian di-mix dengan musik (musik turun otomatis saat ada suara).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel

from autoreels.config import load_prompt, load_trend_brief
from autoreels.edl import EDL, VoiceLine, VoiceOverMode
from autoreels.media import probe, run_ffmpeg, run_ffmpeg_stderr
from autoreels.render.audio_mix import loudnorm_filter
from autoreels.render.overlays import segment_times

WORDS_PER_SEC = 2.5          # kecepatan bicara bahasa Indonesia yang nyaman
MAX_TEMPO = 1.25             # suara AI boleh dipercepat maks 25% agar muat di slotnya
GAP_SEC = 0.08               # jeda minimal antar baris
# Suara Gemini TTS yang ditawarkan di UI (deskripsi karakter, bukan jenis kelamin).
VOICES = {
    "Puck": "ceria & bersemangat",
    "Kore": "tegas & jelas",
    "Zephyr": "cerah & ramah",
    "Charon": "tenang & informatif",
    "Aoede": "santai",
    "Fenrir": "antusias",
}


class VoiceScript(BaseModel):
    lines: list[VoiceLine]


@dataclass
class VoiceTrack:
    path: Path | None                        # vo.wav (None bila belum ada suara, mis. menunggu rekaman)
    mode: str
    timings: list[tuple[float, float, str]] = field(default_factory=list)  # (mulai, selesai, teks) untuk subtitle
    warnings: list[str] = field(default_factory=list)
    loudness: float | None = None            # LUFS track suara (cek tidak senyap)


def word_count(text: str) -> int:
    return len(text.split())


def estimate_sec(text: str) -> float:
    return word_count(text) / WORDS_PER_SEC + 0.3


def total_duration(edl: EDL) -> float:
    return segment_times(edl)[-1][1]


def clean_script(lines: list[VoiceLine], total: float) -> tuple[list[VoiceLine], list[str]]:
    """Urutkan, batasi waktu ke dalam video, dan beri peringatan bila baris terlalu panjang untuk slotnya."""
    warnings: list[str] = []
    out: list[VoiceLine] = []
    for ln in sorted(lines, key=lambda x: x.at_sec):
        text = " ".join(ln.text.split())
        if not text:
            continue
        at = round(min(max(0.0, ln.at_sec), max(0.0, total - 0.8)), 2)
        if out and at <= out[-1].at_sec:
            at = round(out[-1].at_sec + 0.1, 2)
        out.append(VoiceLine(at_sec=at, text=text))
    for i, ln in enumerate(out):
        slot = (out[i + 1].at_sec if i + 1 < len(out) else total) - ln.at_sec
        need = estimate_sec(ln.text)
        if need > slot * MAX_TEMPO:
            warnings.append(f"Baris {i + 1} ('{ln.text[:40]}…') butuh ±{need:.1f} dtk, slotnya {slot:.1f} dtk — persingkat.")
    return out, warnings


def write_script(*, edl: EDL, descriptions: dict, brand: dict, brief: str, llm, model: str,
                 log=print) -> list[VoiceLine]:
    """AI menulis naskah VO berdasarkan urutan segmen final (waktu sudah pasti)."""
    times = segment_times(edl)
    total = times[-1][1]
    segments = []
    for seg, (s, e) in zip(edl.segments, times):
        d = descriptions.get(seg.scene_id) if seg.scene_id else None
        visual = "; ".join(x for x in [getattr(d, "subject", ""), getattr(d, "action", "")] if x) if d else seg.reason
        segments.append({"mulai": round(s, 2), "selesai": round(e, 2), "peran": seg.role.value,
                         "visual": visual or "", "teks_layar": seg.overlay_text})
    pillar = edl.pillar.value
    trend = load_trend_brief()
    context = {
        "instruksi": brief,
        "pilar": pillar,
        "durasi_detik": round(total, 2),
        "maks_kata_total": int(total * WORDS_PER_SEC * 0.9),
        "teks_hook_di_layar": edl.hook.overlay_text,
        "teks_cta_di_layar": edl.cta.text if edl.cta else None,
        "cta_mulai": edl.cta.at_sec if edl.cta else round(total - 3, 2),
        "gaya_bahasa": brand.get("language_style"),
        "boleh_sisipan_sunda": bool(brand.get("allow_sundanese_light")),
        "layanan_terkonfirmasi": brand.get("rental_services") if pillar == "rental" else None,
        "harga_sewa_per_hari": brand.get("pricing", {}).get("rental_per_day"),
        "catatan_tren": trend if "[ISI" not in trend else None,
        "segmen": segments,
    }
    cta_at = context["cta_mulai"]
    context["maks_kata_cta"] = max(3, int((total - 0.3 - cta_at) * WORDS_PER_SEC))
    messages = [{"role": "system", "content": load_prompt("voiceover")},
                {"role": "user", "content": yaml.safe_dump(context, allow_unicode=True, sort_keys=False)}]
    script = llm.complete_structured(messages, VoiceScript, model=model, purpose="voiceover-naskah")
    lines, warnings = clean_script(script.lines, total)
    if warnings:  # satu kali revisi: minta AI memendekkan baris yang tidak muat
        log("  naskah VO kepanjangan → minta AI memendekkan")
        messages = messages + [
            {"role": "assistant", "content": script.model_dump_json()},
            {"role": "user", "content": "Naskah terlalu panjang untuk waktunya (±2,5 kata/detik):\n- "
             + "\n- ".join(warnings) + "\nPersingkat baris tersebut, pertahankan at_sec. Kirim ulang JSON lengkap."},
        ]
        script = llm.complete_structured(messages, VoiceScript, model=model, purpose="voiceover-naskah-revisi")
        lines, warnings = clean_script(script.lines, total)
    for w in warnings:
        log(f"  [naskah VO] {w}")
    log(f"  naskah VO: {len(lines)} baris, {sum(word_count(x.text) for x in lines)} kata untuk {total:.1f} dtk")
    return lines


def _loudness(path: Path) -> float | None:
    import re

    err = run_ffmpeg_stderr(["-i", str(path), "-af", "ebur128", "-f", "null", "-"])
    vals = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(vals[-1]) if vals else None


def _normalize_voice(src: Path, dst: Path, pre: str = "") -> Path:
    """Bersihkan & normalkan suara (high-pass, kompresi ringan, ≈ −14 LUFS)."""
    base = "aresample=48000,aformat=channel_layouts=mono,highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=10:release=200"
    chain = f"{pre},{base}" if pre else base
    norm = loudnorm_filter(["-i", str(src)], chain)
    run_ffmpeg(["-i", str(src), "-af", f"{chain},{norm},aresample=48000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)])
    return dst


_SPOKEN = {"&": " dan ", "+": " plus ", "%": " persen", "/": " atau ", "@": " at "}


def speakable(text: str) -> str:
    """Ubah simbol jadi kata bahasa Indonesia sebelum dibacakan TTS ('&' terbukti dibaca 'and')."""
    t = text
    for sym, word in _SPOKEN.items():
        t = t.replace(sym, word)
    return " ".join(t.split())


def _with_period(text: str) -> str:
    t = speakable(text).strip()
    return t if t[-1:] in ".!?" else f"{t}."


def _silences(wav: Path) -> list[tuple[float, float]]:
    import re

    err = run_ffmpeg_stderr(["-i", str(wav), "-af", "silencedetect=noise=-38dB:d=0.15", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends))


def split_by_pauses(wav: Path, texts: list[str], rdir: Path) -> list[Path]:
    """Potong satu rekaman TTS menjadi N bagian (satu per baris naskah) di jeda antarkalimat.
    Cadangan: bila jeda tidak cocok, potong menurut proporsi jumlah kata."""
    n = len(texts)
    if n == 1:
        return [wav]
    dur = probe(wav).duration
    inner = [(s, e) for s, e in _silences(wav) if s > 0.05 and e < dur - 0.05]
    words = [max(1, word_count(t)) for t in texts]
    expected = [sum(words[: i + 1]) / sum(words) for i in range(n - 1)]  # posisi batas relatif (0–1)
    cuts: list[float] | None = None
    if len(inner) >= n - 1:
        longest = sorted(sorted(inner, key=lambda x: x[1] - x[0], reverse=True)[: n - 1])
        cand = [(s + e) / 2 for s, e in longest]
        # masuk akal bila tiap batas dekat dengan perkiraan dari jumlah kata (toleransi 20% durasi)
        if all(abs(c / dur - x) < 0.2 for c, x in zip(cand, expected)):
            cuts = cand
    if cuts is None:
        cuts = [x * dur for x in expected]
    bounds = [0.0, *cuts, dur]
    trim = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
            "silenceremove=start_periods=1:start_threshold=-45dB,areverse")
    out = []
    for i in range(n):
        piece = rdir / f"vo_line_{i:02d}.wav"
        run_ffmpeg(["-i", str(wav), "-af", f"atrim={bounds[i]:.3f}:{bounds[i + 1]:.3f},asetpts=PTS-STARTPTS,{trim}",
                    "-c:a", "pcm_s16le", str(piece)])
        out.append(piece)
    return out


def _place(wanted: list[float], lengths: list[float], end_limit: float) -> list[float]:
    """Maju: tidak saling tumpang tindih. Mundur: baris yang lewat batas akhir digeser lebih awal ke celah kosong."""
    starts = []
    for i, (w, ln) in enumerate(zip(wanted, lengths)):
        s = w if i == 0 else max(w, starts[-1] + lengths[i - 1] + GAP_SEC)
        starts.append(s)
    limit = end_limit
    for i in range(len(starts) - 1, -1, -1):
        if starts[i] + lengths[i] > limit:
            starts[i] = limit - lengths[i]
        limit = starts[i] - GAP_SEC
    return starts


def schedule_lines(wanted: list[float], durs: list[float], total: float) -> tuple[list[float], float]:
    """Atur waktu mulai tiap baris agar muat di video; bila perlu percepat semua suara (maks 25%).
    Mengembalikan (waktu_mulai, tempo)."""
    end_limit = total - 0.15
    for tempo in (1.0, 1.05, 1.1, 1.15, 1.2, MAX_TEMPO):
        lengths = [d / tempo for d in durs]
        starts = _place(wanted, lengths, end_limit)
        if starts and starts[0] >= -1e-6:
            return [round(max(0.0, s), 3) for s in starts], tempo
    lengths = [d / MAX_TEMPO for d in durs]  # tetap tidak muat: mulai dari 0, sisanya terpotong (diberi peringatan)
    starts = _place([0.0] + wanted[1:], lengths, float("inf"))
    return [round(max(0.0, s), 3) for s in starts], MAX_TEMPO


def build_tts_track(lines: list[VoiceLine], total: float, voice: str, llm, rdir: Path, log=print) -> VoiceTrack:
    track = VoiceTrack(path=None, mode="gemini")
    if not lines:
        track.warnings.append("Naskah voice over kosong.")
        return track
    # Satu permintaan TTS untuk seluruh naskah (hemat kuota: free tier hanya 10 permintaan/hari/model),
    # lalu dipotong per baris di jeda antarkalimat.
    full_text = "\n".join(_with_period(ln.text) for ln in lines)
    log(f"  suara AI: {len(lines)} baris dalam 1 permintaan")
    full = llm.synthesize_speech(full_text, voice=voice, purpose="voiceover-tts")
    wavs = split_by_pauses(full, [ln.text for ln in lines], rdir)
    durs = [probe(w).duration for w in wavs]

    starts, tempo = schedule_lines([ln.at_sec for ln in lines], durs, total)
    if tempo > 1.001:
        log(f"  suara dipercepat {round((tempo - 1) * 100)}% agar muat di durasi video")
    clips = [(wav, start, tempo) for wav, start in zip(wavs, starts)]
    end_last = 0.0
    for ln, start, dur in zip(lines, starts, durs):
        end = start + dur / tempo
        track.timings.append((start, min(end, total), ln.text))
        end_last = max(end_last, end)
    if end_last > total + 0.05:
        track.warnings.append(f"Voice over selesai di {end_last:.1f} dtk, melewati akhir video ({total:.1f} dtk) "
                              "— persingkat naskah.")

    inputs: list[str] = []
    parts = []
    for k, (wav, start, tempo) in enumerate(clips):
        inputs += ["-i", str(wav)]
        tempo_f = f"atempo={tempo:.3f}," if tempo > 1.001 else ""
        ms = int(round(start * 1000))
        parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,{tempo_f}adelay={ms}:all=1[c{k}]")
    mix = "".join(f"[c{k}]" for k in range(len(clips)))
    graph = ";".join(parts) + f";{mix}amix=inputs={len(clips)}:normalize=0:duration=longest,apad,atrim=0:{total:.3f}[vo]"
    raw = rdir / "vo_raw.wav"
    run_ffmpeg([*inputs, "-filter_complex", graph, "-map", "[vo]", "-ac", "1", "-c:a", "pcm_s16le", str(raw)])
    track.path = _normalize_voice(raw, rdir / "vo.wav")
    track.loudness = _loudness(track.path)
    return track


def build_recording_track(rec: Path, lines: list[VoiceLine], total: float, offset: float, rdir: Path) -> VoiceTrack:
    """Rekaman manusia (direkam sambil video diputar, atau diunggah) → track sepanjang video."""
    track = VoiceTrack(path=None, mode="rekam")
    if offset >= 0:
        pre = f"adelay={int(round(offset * 1000))}:all=1" if offset > 0 else ""
    else:
        pre = f"atrim=start={-offset:.3f},asetpts=PTS-STARTPTS"
    clean = rdir / "vo_rec_clean.wav"
    _normalize_voice(rec, clean, pre=pre)
    rec_dur = probe(clean).duration
    run_ffmpeg(["-i", str(clean), "-af", f"apad,atrim=0:{total:.3f}", "-ac", "1", "-c:a", "pcm_s16le",
                str(rdir / "vo.wav")])
    track.path = rdir / "vo.wav"
    track.loudness = _loudness(track.path)
    if rec_dur > total + 0.5:
        track.warnings.append(f"Rekaman {rec_dur:.1f} dtk lebih panjang dari video ({total:.1f} dtk) — bagian akhir terpotong.")
    # waktu subtitle diperkirakan dari naskah (rekaman dibaca mengikuti teleprompter)
    for i, ln in enumerate(lines):
        nxt = lines[i + 1].at_sec if i + 1 < len(lines) else total
        track.timings.append((ln.at_sec + max(0.0, offset), min(nxt, ln.at_sec + estimate_sec(ln.text)), ln.text))
    return track


def prepare_voiceover(edl: EDL, out_dir: Path, rdir: Path, total: float, llm, log=print) -> VoiceTrack | None:
    vo = edl.voiceover
    if vo.mode == VoiceOverMode.none:
        return None
    if vo.mode == VoiceOverMode.gemini:
        log(f"  voice over: suara AI '{vo.voice}' ({len(vo.lines)} baris)")
        return build_tts_track(vo.lines, total, vo.voice, llm, rdir, log)
    rec = out_dir / vo.recording if vo.recording else None
    if rec is None or not rec.exists():
        log("  voice over: menunggu rekaman suara (rekam/unggah di halaman Hasil)")
        return VoiceTrack(path=None, mode="rekam", warnings=["Rekaman voice over belum ada."])
    log(f"  voice over: rekaman {rec.name} (geser {vo.offset_sec:+.2f} dtk)")
    return build_recording_track(rec, vo.lines, total, vo.offset_sec, rdir)
