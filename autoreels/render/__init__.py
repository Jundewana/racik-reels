"""[7] Render — eksekusi EDL secara deterministik dengan ffmpeg.

Urutan: segmen → concat → voice over → teks .ass (+ subtitle VO) + logo → musik (+ ducking VO, loudnorm)
→ reel.mp4 + cover.jpg. Semua file antara di work/<job_id>/render/; ffmpeg dijalankan dengan cwd di sana
agar path subtitle/font relatif (menghindari masalah escape path Windows).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoreels.analyze.models import Analysis
from autoreels.config import PATHS
from autoreels.edl import EDL, Reframe

FADE_OUT_SEC = 0.6  # video & audio memudar di akhir (masukan pemilik 2026-11-24: akhir tidak polos)
from autoreels.media import run_ffmpeg
from autoreels.render.audio_mix import fix_true_peak, mix_voice, peak_guard_wav, render_music_bed, render_silence
from autoreels.render.cut import render_segment
from autoreels.render.overlays import logo_file_for, logo_position, prepare_logo, segment_times, text_events
from autoreels.render.reframe import OUT_H
from autoreels.render.text_ass import build_ass, font_full_name
from autoreels.render.transitions import FPS, XFADE, join_graph, xfade_frames

STABILIZE_SHAKE = 1.0  # jitter adegan (px, proxy 480p) mulai dari sini distabilkan; > 6 sudah dibuang (unusable)
HOOK_AVOID_SEC = 3.0  # segmen pembicara yang mulai di detik hook ikut dihindari teks hook


@dataclass
class RenderOutput:
    reel: Path
    cover: Path
    duration: float
    font_name: str
    font_file: Path
    voice: Any = None  # VoiceTrack (autoreels.voiceover) bila voice over aktif
    privacy: Any = None  # PrivacyStats (autoreels.render.privacy) bila blur wajah/pelat aktif


def _scene(analysis: Analysis, seg):
    return next((s for s in analysis.scenes if s.scene_id == seg.scene_id), None)


def _compare_inputs(analysis: Analysis, seg):
    """(klip, adegan) untuk adegan 'sebelum' segmen before–after; (None, None) bila tidak ada."""
    if seg.compare is None:
        return None, None
    clip = analysis.clip(seg.compare.source_file)
    if clip is None or not Path(clip.path).exists():
        return None, None
    return clip, next((s for s in analysis.scenes if s.scene_id == seg.compare.scene_id), None)



def _color_key(edl: EDL, analysis: Analysis, seg) -> tuple[str, str, float, float] | None:
    """(kunci, path, mulai, selesai) sumber yang diukur: klip pembicara sekali per klip, b-roll per adegan."""
    clip = analysis.clip(seg.source_file)
    if clip is None:
        return None
    if edl.narration is not None and edl.narration.speaker_clip == seg.source_file:
        return clip.name, clip.path, 0.1, max(0.2, clip.duration - 0.1)
    sc = _scene(analysis, seg)
    if sc is not None:
        return sc.scene_id, clip.path, sc.start, sc.end
    return f"{clip.name}@{seg.start:.1f}", clip.path, seg.start, seg.end


def _plan_color(edl: EDL, analysis: Analysis, style: dict, log) -> dict[int, str]:
    """Filter penyeragam warna per indeks segmen (render/color.py); kosong bila `color_match` = 0."""
    from autoreels.render.color import DEFAULT_STRENGTH, measure, plan_corrections

    strength = float(style.get("color_match", DEFAULT_STRENGTH) or 0)
    keys = {seg.index: _color_key(edl, analysis, seg) for seg in edl.segments}
    sources = {k[0]: k for k in keys.values() if k is not None}
    if strength <= 0 or len(sources) < 2:  # satu sumber saja: tidak ada yang perlu diseragamkan
        return {}
    stats = {}
    for key, (_, path, a, b) in sources.items():
        st = measure(path, a, b)
        if st is not None:
            stats[key] = st
    plan = {key: c.filter() for key, c in plan_corrections(stats, strength).items()}
    fixed = sum(1 for f in plan.values() if f)
    log(f"  warna diseragamkan: {fixed} dari {len(sources)} sumber dikoreksi (kekuatan {strength:g})")
    return {i: plan.get(k[0], "") for i, k in keys.items() if k is not None}


def render_reel(
    edl: EDL,
    analysis: Analysis,
    style: dict,
    brand: dict,
    work_dir: Path,
    out_dir: Path,
    log=print,
    preview: bool = False,
    progress=None,
    llm=None,
) -> RenderOutput:
    def tick(done: float, detail: str) -> None:
        if progress:
            progress.update(done, len(edl.segments) + 4, detail)

    rdir = work_dir / "render"
    if rdir.exists():
        shutil.rmtree(rdir)
    (rdir / "fonts").mkdir(parents=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. segmen (segmen yang diikuti transisi xfade diberi ekor agar bisa tumpang tindih)
    times = segment_times(edl)
    hook_heads: list[tuple[int, int]] = []
    color_fix = _plan_color(edl, analysis, style, log)
    slot_frames = [round((b - a) * FPS) for a, b in times]
    trans = [s.transition_in for s in edl.segments]
    tails = [xfade_frames(trans[i + 1], slot_frames[i + 1]) if i + 1 < len(trans) else 0
             for i in range(len(trans))]
    seg_files = []
    last_box = None  # crop pembicara sebelumnya (dipakai ulang bila mirip agar tidak goyang)
    for seg in edl.segments:
        clip = analysis.clip(seg.source_file)
        if clip is None:
            raise FileNotFoundError(f"Klip sumber '{seg.source_file}' tidak ada di analisis job.")
        if not Path(clip.path).exists():
            raise FileNotFoundError(f"File sumber hilang: {clip.path}")
        out = rdir / f"seg_{seg.index:03d}.mp4"
        tick(seg.index, f"segmen {seg.index + 1}/{len(edl.segments)}")
        log(f"  segmen {seg.index + 1}/{len(edl.segments)}: {seg.source_file} "
            f"{seg.start:.2f}–{seg.end:.2f} ({seg.output_duration:.2f} dtk, {seg.transition_in.value})")
        cmp_clip, cmp_scene = _compare_inputs(analysis, seg)
        if cmp_clip is not None:
            log(f"    before–after: sebelum = {seg.compare.source_file} {seg.compare.start:.2f} dtk → wipe")
        box = None
        if (edl.narration is not None and edl.narration.speaker_clip == seg.source_file
                and seg.reframe != Reframe.blur_pad and seg.compare is None):
            from autoreels.render.speaker import speaker_crops, stable_box

            cuts = [s.start for s in analysis.scenes if s.source_file == seg.source_file]
            shots = speaker_crops(Path(clip.path), seg.start, seg.end, clip.width, clip.height, cuts)
            if shots:
                first = stable_box(last_box, shots[0][1])
                if first is not shots[0][1] and first.w == shots[0][1].w:
                    shots[0] = (0.0, first)
                last_box = shots[-1][1]
                box = shots if len(shots) > 1 else shots[0][1]
            else:
                box = last_box = None
            log("    fokus pembicara: " + (f"{len(shots)} shot, crop {shots[0][1].w}×{shots[0][1].h}" if shots
                                           else "tidak tampak → crop biasa"))
        if box is not None and times[seg.index][0] < HOOK_AVOID_SEC:  # kepala di detik hook → teks hook menghindar
            for _, b in (box if isinstance(box, list) else [(0.0, box)]):
                head = b.face_out(OUT_H)
                if head is not None:
                    hook_heads.append(head)
        sc = _scene(analysis, seg)
        stab = (style.get("stabilize", True) and box is None and seg.compare is None and sc is not None
                and sc.shake >= STABILIZE_SHAKE)
        if stab:
            log(f"    stabilisasi: goyang {sc.shake:.1f} px → vidstab")
        render_segment(seg, clip, sc, out, preview=preview, tail_frames=tails[seg.index],
                       grade=style.get("color_grade"), compare_clip=cmp_clip, compare_scene=cmp_scene, box=box,
                       color=color_fix.get(seg.index, ""), stabilize=stab)
        seg_files.append(out)

    # 2. gabung: tanpa xfade → concat stream copy; dengan xfade → filter xfade (titik potong & durasi tetap)
    if not any(tails):
        (rdir / "concat.txt").write_text("".join(f"file '{f.name}'\n" for f in seg_files), encoding="utf-8")
        run_ffmpeg(["-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "video.mp4"], cwd=rdir)
    else:
        n_x = sum(1 for t in tails if t)
        log(f"  transisi: {n_x} xfade ({', '.join(sorted({t.value for t in trans if t in XFADE}))})")
        graph, last = join_graph(slot_frames, trans)
        inputs = [a for f in seg_files for a in ("-i", f.name)]
        run_ffmpeg([*inputs, "-filter_complex", f"{graph};[{last}]format=yuv420p[v]", "-map", "[v]",
                    "-r", str(FPS), "-c:v", "libx264", "-preset", "ultrafast" if preview else "veryfast",
                    "-crf", "17", "video.mp4"], cwd=rdir)
    total = times[-1][1]

    # 2b. blur privasi (wajah/pelat) — sebelum teks & logo ditempel agar teks tidak ikut buram
    privacy = None
    if edl.privacy.blur_faces or edl.privacy.blur_plates:
        from autoreels.render.privacy import blur_video

        what = " & ".join(x for x, on in (("wajah", edl.privacy.blur_faces),
                                          ("pelat nomor", edl.privacy.blur_plates)) if on)
        tick(len(edl.segments), f"menyamarkan {what}")
        log(f"  privasi: menyamarkan {what} …")
        privacy = blur_video(rdir / "video.mp4", rdir / "video_privasi.mp4", faces=edl.privacy.blur_faces,
                             plates=edl.privacy.blur_plates, preview=preview, log=log)
        (rdir / "video_privasi.mp4").replace(rdir / "video.mp4")
        log(f"  privasi: wajah di {privacy.face_frames} frame, pelat di {privacy.plate_frames} frame "
            f"(dari {privacy.frames})")

    # 3. voice over (dibuat sebelum teks: subtitle mengikuti waktu suara)
    voice = None
    if edl.voiceover.mode.value != "none":
        from autoreels.llm import LLMClient
        from autoreels.voiceover import prepare_voiceover

        tick(len(edl.segments), "voice over")
        voice = prepare_voiceover(edl, out_dir, rdir, total, llm or LLMClient(log=log), log=log)
        for w in voice.warnings if voice else []:
            log(f"  [voice over] {w}")

    # 3b. narasi (alur "narasi dulu"): suara utama sudah jadi & sejajar dengan segmen
    narration_path = None
    if edl.narration is not None:
        narration_path = out_dir / edl.narration.file
        if not narration_path.exists():
            raise FileNotFoundError(f"File narasi hilang: {narration_path}")
        log(f"  narasi: {edl.narration.file} ({edl.narration.duration:.1f} dtk, {len(edl.narration.phrases)} frasa)")

    # 4. teks .ass + font (dengan subtitle voice over bila ada suara)
    font_rel = style.get("font") or brand.get("fonts", {}).get("heading")
    font_file = PATHS["fonts"] / font_rel
    if not font_file.exists():
        raise FileNotFoundError(f"Font style tidak ditemukan: {font_file}")
    shutil.copy(font_file, rdir / "fonts" / font_file.name)
    font_name = font_full_name(font_file)
    vo_timings = voice.timings if voice and voice.path else None
    karaoke = edl.narration.words if edl.narration is not None else None
    events = text_events(edl, brand, vo_timings, karaoke)
    for ev in events:
        if ev.kind == "hook" and hook_heads:
            ev.avoid = hook_heads
            log(f"  teks hook menghindari wajah pembicara (kepala di y {min(a for a, _ in hook_heads)}–"
                f"{max(b for _, b in hook_heads)} px)")
    behind_plan, behind_end = None, 0.0
    hook_ev = next((ev for ev in events if ev.kind == "hook"), None)
    if style.get("hook_behind") and hook_ev is not None:
        from autoreels.render import behind

        if not behind.available():
            log(f"  [peringatan] hook di belakang orang dilewati: model {behind.MODEL.name} tidak ada")
        else:
            masks = behind.hook_masks(rdir / "video.mp4", hook_ev.end)
            behind_plan = behind.plan_behind(masks, hook_ev.text)
            if behind_plan is None:
                log("  hook di belakang orang: tidak ada posisi yang pas (orang tidak terdeteksi / terlalu tinggi)"
                    " → hook biasa")
            else:
                hook_ev.place, behind_end = (behind_plan.y, behind_plan.size), hook_ev.end
                behind.write_mask_video(masks, rdir / "mask_hook.mkv")
                log(f"  hook di belakang orang: y {behind_plan.y}, {behind_plan.size} px, "
                    f"{behind_plan.cover:.0%} teks tertutup orang")
    (rdir / "text.ass").write_text(build_ass(events, style, font_name), encoding="utf-8")

    # 5. musik (+ voice over dengan ducking)
    tick(len(edl.segments) + 1, "musik & loudness")
    music = analysis.music
    if music and edl.music.mood.value != "none" and Path(music.path).exists():
        log(f"  musik: {Path(music.path).name} (mulai {music.start_offset:.1f} dtk)")
        render_music_bed(music.path, music.start_offset, total, rdir / "music.wav")
    else:
        log("  musik: tidak ada (senyap)")
        render_silence(total, rdir / "music.wav")
    audio_file = "music.wav"
    if narration_path is not None:
        from autoreels.render.audio_mix import MUSIC_GAIN_INFO_DB, MUSIC_GAIN_TALK_DB

        gain = (MUSIC_GAIN_INFO_DB if edl.purpose.value == "informasi"
                else MUSIC_GAIN_TALK_DB if edl.narration.speaker_clip else 0.0)
        if edl.music.mood.value == "none":
            log("  audio: suara narasi/pembicara saja (tanpa musik)")
        else:
            log("  mix narasi + musik (musik turun saat ada suara"
                + (f", volume musik {10 ** (gain / 20):.0%})" if gain else ")"))
        mix_voice(rdir / "music.wav", narration_path, rdir / "audio.wav", total, music_gain_db=gain)
        audio_file = "audio.wav"
    elif voice and voice.path:
        log("  mix voice over + musik (musik turun saat ada suara)")
        mix_voice(rdir / "music.wav", voice.path, rdir / "audio.wav", total)
        audio_file = "audio.wav"
    if style.get("sfx_db") is not None:  # efek suara transisi (render/sfx.py), sebelum pembatas puncak
        from autoreels.render.sfx import render_sfx_track, sfx_cues

        cues = sfx_cues(edl, times)
        if cues:
            render_sfx_track(cues, total, float(style["sfx_db"]), PATHS["assets"] / "sfx", rdir / "sfx.wav")
            run_ffmpeg(["-i", audio_file, "-i", "sfx.wav", "-filter_complex",
                        "[0:a][1:a]amix=inputs=2:normalize=0:duration=first[a]", "-map", "[a]",
                        "-c:a", "pcm_s16le", "with_sfx.wav"], cwd=rdir)
            audio_file = "with_sfx.wav"
            log(f"  efek suara: {len(cues)} ({', '.join(sorted({n for _, n in cues}))}), {style['sfx_db']} dB")
    # batasi puncak di PCM sebelum encoding AAC (AAC menaikkan puncak ±1–1,5 dB)
    fade = (max(0.0, total - FADE_OUT_SEC), FADE_OUT_SEC)  # akhir video memudar (tidak berhenti mendadak)
    peak_guard_wav(rdir / audio_file, rdir / "final_audio.wav", fade_out=fade)
    audio_file = "final_audio.wav"

    # 6. komposisi akhir
    tick(len(edl.segments) + 2, "komposisi akhir: teks, logo, audio")
    inputs = ["-i", "video.mp4", "-i", audio_file]
    graph = "[0:v]subtitles=text.ass:fontsdir=fonts[vt]"
    vout = "vt"
    if behind_plan is not None:  # piksel orang dari video asli ditempel di atas teks selama hook
        inputs += ["-i", "mask_hook.mkv"]
        mi = len(inputs) // 2 - 1
        graph = (f"[0:v]split[vb][vp];[vb]subtitles=text.ass:fontsdir=fonts[vs];"
                 f"[{mi}:v]format=gray[mk];[vp][mk]alphamerge[pp];"
                 f"[vs][pp]overlay=0:0:enable='lt(t,{behind_end:.3f})':eof_action=pass:format=auto[vt]")
    logo_src = logo_file_for(brand, edl.pillar.value)
    logo_xy = None
    if edl.branding.logo and logo_src.exists():
        logo = prepare_logo(logo_src, rdir / "logo.png")
        import cv2
        lh, lw = cv2.imread(str(logo), cv2.IMREAD_UNCHANGED).shape[:2]
        x, y = logo_position(edl.branding.position.value, lw, lh)
        logo_xy = (x, y)
        inputs += ["-i", "logo.png"]
        graph += f";[{len(inputs) // 2 - 1}:v]format=rgba[lg];[vt][lg]overlay={x}:{y}:format=auto[vl]"
        vout = "vl"
    graph += f";[{vout}]fade=t=out:st={fade[0]:.3f}:d={fade[1]:.3f},format=yuv420p[v]"
    reel = out_dir / "reel.mp4"
    run_ffmpeg([
        *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast" if preview else "veryfast", "-crf", "20",
        "-r", "30", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{total:.3f}", "-movflags", "+faststart", str(reel.resolve()),
    ], cwd=rdir)
    fix_true_peak(reel, pcm=rdir / audio_file, log=log)  # pengaman terakhir bila puncak masih > −1 dBTP

    # 7. cover: frame hook dari video SEBELUM teks + teks hook diam (tanpa subtitle/CTA) + logo.
    #    Teks hook berada di dalam area tengah 3:4 (y 240–1680) agar tetap utuh di grid profil Instagram.
    cover = out_dir / "cover.jpg"
    cover_at = f"{min(1.0, total / 2):.2f}"
    cover_events = []
    if edl.hook.overlay_text:
        from autoreels.render.text_ass import TextEvent

        cover_events.append(TextEvent(0.0, 10.0, "cover", edl.hook.overlay_text, avoid=hook_heads or None,
                                      place=(behind_plan.y, behind_plan.size) if behind_plan else None))
    (rdir / "cover.ass").write_text(build_ass(cover_events, style, font_name), encoding="utf-8")
    cgraph = "[0:v]subtitles=cover.ass:fontsdir=fonts[ct]"
    cinputs, cout = ["-ss", cover_at, "-i", "video.mp4"], "ct"
    if behind_plan is not None:
        from autoreels.render.behind import cover_mask

        if cover_mask(rdir / "video.mp4", float(cover_at), rdir / "mask_cover.png") is not None:
            cinputs += ["-i", "mask_cover.png"]
            cgraph = ("[0:v]split[cb][cp];[cb]subtitles=cover.ass:fontsdir=fonts[cs];"
                      "[1:v]format=gray[cm];[cp][cm]alphamerge[cpp];[cs][cpp]overlay=0:0:format=auto[ct]")
    if logo_xy is not None:
        cinputs += ["-i", "logo.png"]
        li = sum(1 for x in cinputs if x == "-i") - 1
        cgraph += f";[{li}:v]format=rgba[lg];[ct][lg]overlay={logo_xy[0]}:{logo_xy[1]}:format=auto[cl]"
        cout = "cl"
    run_ffmpeg([*cinputs, "-filter_complex", cgraph, "-map", f"[{cout}]", "-frames:v", "1", "-q:v", "2",
                str(cover.resolve())], cwd=rdir)
    return RenderOutput(reel=reel, cover=cover, duration=total, font_name=font_name, font_file=font_file,
                        voice=voice, privacy=privacy)
