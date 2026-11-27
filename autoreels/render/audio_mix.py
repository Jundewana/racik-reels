"""Musik latar: potong dari titik mulai terbaik, fade, dan normalisasi loudness 2-pass (≈ −14 LUFS).

Ducking di bawah ucapan (sidechaincompress) menyusul di Tahap 2–3 saat ada audio asli/ucapan.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from autoreels.media import run_ffmpeg

TARGET_LUFS = -14.0
TRUE_PEAK = -2.0  # margin: encoding AAC bisa menaikkan puncak ±1 dB
LRA = 11.0


def loudnorm_filter(input_args: list[str], base: str = "") -> str:
    """Pass 1 loudnorm: ukur audio dari `input_args` (mis. ["-i", file]) lalu kembalikan
    filter loudnorm linear (pass 2) yang menghasilkan ≈ −14 LUFS."""
    chain = f"{base}," if base else ""
    proc = run_ffmpeg([
        *input_args, "-vn",
        "-af", f"{chain}loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA={LRA}:print_format=json",
        "-f", "null", "-",
    ])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.S)
    if not m:
        return f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA={LRA}"
    meas = json.loads(m.group(0))
    if meas.get("input_i") in ("-inf", "inf"):  # audio senyap: tidak perlu dinormalisasi
        return "anull"
    return (f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA={LRA}:"
            f"measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:"
            f"measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:"
            f"offset={meas['target_offset']}:linear=true")


def render_music_bed(music_path: str, start: float, duration: float, out: Path) -> Path:
    fade_out = min(1.5, duration / 4)
    base = (f"atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d=0.04,afade=t=out:st={duration - fade_out:.3f}:d={fade_out:.3f}")
    norm = loudnorm_filter(["-ss", f"{start:.3f}", "-i", music_path], base)
    # pass 2: terapkan
    run_ffmpeg([
        "-ss", f"{start:.3f}", "-i", music_path,
        "-af", f"{base},{norm},aresample=48000",
        "-ac", "2", "-c:a", "pcm_s16le", str(out),
    ])
    return out


MUSIC_GAIN_INFO_DB = -9.0   # video informasi (kuliah/edukasi): musik ±35% — latar tipis
MUSIC_GAIN_TALK_DB = -6.0   # video bicara promosi: musik ±50%


def mix_voice(music_wav: Path, voice_wav: Path, out: Path, duration: float, music_gain_db: float = 0.0) -> Path:
    """Musik + voice over: musik diturunkan otomatis saat ada suara (sidechain ducking), lalu −14 LUFS.
    music_gain_db: penurunan tambahan volume musik (mis. video informasi/bicara)."""
    graph = (
        f"[0:a]aresample=48000,aformat=channel_layouts=stereo,volume={-4.0 + music_gain_db:g}dB[m];"
        "[1:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v1][v2];"
        "[m][v1]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=400[duck];"
        f"[duck][v2]amix=inputs=2:normalize=0:duration=first,atrim=0:{duration:.3f}[mix]"
    )
    pre = out.with_name("mix_pre.wav")
    run_ffmpeg(["-i", str(music_wav), "-i", str(voice_wav), "-filter_complex", graph, "-map", "[mix]",
                "-c:a", "pcm_s16le", str(pre)])
    norm = loudnorm_filter(["-i", str(pre)])
    run_ffmpeg(["-i", str(pre), "-af", f"{norm},aresample=48000", "-ac", "2", "-c:a", "pcm_s16le", str(out)])
    return out


def measure_audio(path: Path) -> tuple[float | None, float | None]:
    """(loudness terintegrasi LUFS, true peak dBTP) dari audio file, diukur dengan ebur128."""
    from autoreels.media import run_ffmpeg_stderr

    err = run_ffmpeg_stderr(["-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    return (float(lufs[-1]) if lufs else None, float(peak[-1]) if peak else None)


PEAK_CEILING = -1.0   # batas checklist (≤ −1 dBTP)
PEAK_TARGET = -1.5    # target setelah koreksi

# True-peak limiter sebelum encoding AAC. Encoding AAC menaikkan puncak (teruji 2026-11-20: WAV −1,9 → AAC
# −0,6 dBTP), dan meng-encode ulang AAC justru menaikkannya lagi. Jadi puncak dibatasi di PCM: oversampling 4×
# (192 kHz) agar puncak antar-sampel ikut tertangkap, batas −3 dBTP (0,708), level=0 = tanpa menaikkan volume.
PEAK_GUARD = "aresample=192000,alimiter=limit=0.708:attack=1:release=50:level=0,aresample=48000"


def peak_guard_wav(src: Path, dst: Path, fade_out: tuple[float, float] | None = None) -> Path:
    """Terapkan PEAK_GUARD ke file audio PCM sebelum di-mux & di-encode ke AAC.
    fade_out: (mulai, durasi) — audio memudar di akhir video, seiring video memudar ke hitam."""
    chain = PEAK_GUARD
    if fade_out:
        chain = f"afade=t=out:st={fade_out[0]:.3f}:d={fade_out[1]:.3f},{chain}"
    run_ffmpeg(["-i", str(src), "-af", chain, "-ac", "2", "-c:a", "pcm_s16le", str(dst)])
    return dst


def fix_true_peak(video: Path, pcm: Path | None = None, log=print, max_passes: int = 2) -> float | None:
    """Pengaman terakhir: ukur true peak video jadi. Bila > −1 dBTP dan sumber PCM tersedia, encode ulang audio
    SEKALI dari PCM (bukan dari AAC) dengan volume diturunkan; video disalin tanpa render ulang.
    Kembalikan true peak akhir (checklist tetap menilai hasilnya)."""
    _, peak = measure_audio(video)
    reduce_db = 0.0
    for _ in range(max_passes):
        if peak is None or peak <= PEAK_CEILING:
            return peak
        if pcm is None or not pcm.exists():
            log(f"  [peringatan] audio: true peak {peak:+.1f} dBTP (> {PEAK_CEILING}); tanpa sumber PCM untuk koreksi")
            return peak
        reduce_db = round(reduce_db + peak - PEAK_TARGET, 2)
        log(f"  audio: true peak {peak:+.1f} dBTP setelah encoding AAC → encode ulang dari PCM, −{reduce_db} dB")
        tmp = video.with_name(video.stem + ".tp.mp4")
        run_ffmpeg(["-i", str(video), "-i", str(pcm), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", f"volume=-{reduce_db}dB", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", str(tmp)])
        tmp.replace(video)
        _, peak = measure_audio(video)
    return peak


CUT_FADE = 0.03  # fade 30 ms di tiap potongan agar tidak terdengar "klik" (praktik video-use)


def cut_audio(src: str | Path, ranges: list[tuple[float, float]], out: Path) -> Path:
    """Ambil rentang-rentang audio lalu sambung berurutan (mis. ucapan tanpa jeda & kata pengisi)."""
    parts, labels = [], []
    for i, (a, b) in enumerate(ranges):
        d = b - a
        f = min(CUT_FADE, d / 4)
        parts.append(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d={f:.3f},afade=t=out:st={d - f:.3f}:d={f:.3f}[a{i}]")
        labels.append(f"[a{i}]")
    graph = ";".join(parts) + f";{''.join(labels)}concat=n={len(labels)}:v=0:a=1[out]"
    run_ffmpeg(["-i", str(src), "-filter_complex", graph, "-map", "[out]", "-ar", "48000", "-ac", "2",
                "-c:a", "pcm_s16le", str(out)])
    return out


def render_silence(duration: float, out: Path) -> Path:
    run_ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{duration:.3f}",
                "-c:a", "pcm_s16le", str(out)])
    return out
