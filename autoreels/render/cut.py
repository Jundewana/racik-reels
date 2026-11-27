"""Potong satu segmen dari file sumber → klip antara 1080×1920 30 fps (tanpa audio), durasi presisi frame.

Segmen dengan `compare` (mode before–after) dibuka dengan adegan "sebelum", lalu wipe ke adegan segmen ("sesudah").
"""

from __future__ import annotations

from pathlib import Path

from autoreels.analyze.models import ClipInfo, Scene
from autoreels.edl import Reframe, Segment
from autoreels.media import run_ffmpeg
from autoreels.render.reframe import blur_pad_graph, crop_filter
from autoreels.render.transitions import entry_effect

FPS = 30

# Color grade per style preset (`color_grade` di config/styles/*.yaml) — membuat tiap gaya terasa berbeda.
GRADES = {
    "punchy": "eq=contrast=1.08:saturation=1.22:gamma=0.98",                       # energik: warna tegas
    "warm": "colorbalance=rs=0.06:gs=0.01:bs=-0.06:rm=0.04:bm=-0.04,"              # sinematik: hangat,
            "eq=contrast=1.04:saturation=1.05,vignette=angle=PI/5",                #   tepi sedikit gelap
    "clean": "eq=contrast=1.05:saturation=0.92:brightness=0.01",                   # profesional: netral, rapi
    "none": "",
}

STAB_SMOOTHING = 12    # frame perataan gerak kamera (makin besar makin halus)
STAB_ZOOM = 4          # % zoom agar tepi kosong hasil stabilisasi tidak terlihat
BEFORE_SHARE = 0.45   # porsi segmen untuk adegan "sebelum"
WIPE_FRAMES = 12      # ±0,4 dtk


def frames_for(seconds: float) -> int:
    return max(1, round(seconds * FPS))


def compare_split(slot_frames: int) -> tuple[int, int]:
    """(frame adegan 'sebelum', frame wipe) untuk segmen before–after sepanjang `slot_frames`."""
    before = max(8, round(slot_frames * BEFORE_SHARE))
    wipe = max(4, min(WIPE_FRAMES, (slot_frames - before) // 2))
    return before, wipe


def _interp(scene: Scene | None, t: float) -> float:
    if scene is None or scene.duration <= 0:
        return 0.5
    k = min(1.0, max(0.0, (t - scene.start) / scene.duration))
    return scene.crop_cx_start + (scene.crop_cx_end - scene.crop_cx_start) * k


def _source_chain(idx: int, start: float, end: float, speed: float, reframe: Reframe, clip: ClipInfo,
                  scene: Scene | None, dur: float, label: str, box=None, stab: str | None = None) -> str:
    """Filter: input `idx` → 1080×1920 30 fps berlabel `label` (speed, reframe, tanpa grade).
    box: CropBox (render/speaker.py) — crop statis ke wajah pembicara, menggantikan crop geser."""
    # tpad: bila sumber habis sebelum frame target, ulang frame terakhir (durasi tetap presisi)
    base = f"setpts=(PTS-STARTPTS)/{speed:g},fps={FPS},tpad=stop_mode=clone:stop_duration=0.5"
    if stab:  # stabilisasi (vidstab pass 2) pada frame sumber, sebelum speed & crop 9:16
        base = (f"vidstabtransform=input={stab}:smoothing={STAB_SMOOTHING}:zoom={STAB_ZOOM}:optzoom=0:"
                f"interpol=bilinear,{base}")
    if box is not None:  # CropBox, atau [(detik relatif, CropBox)] bila kamera berganti shot di tengah segmen
        shots = box if isinstance(box, list) else [(0.0, box)]
        w, h = shots[0][1].w, shots[0][1].h
        x_expr, y_expr = str(shots[-1][1].x), str(shots[-1][1].y)
        for k in range(len(shots) - 2, -1, -1):  # bangun ekspresi bersarang dari shot terakhir ke pertama
            b, nxt = shots[k][1], shots[k + 1][0]
            x_expr = f"if(lt(t,{nxt:.3f}),{b.x},{x_expr})"
            y_expr = f"if(lt(t,{nxt:.3f}),{b.y},{y_expr})"
        return (f"[{idx}:v]{base},crop={w}:{h}:x='{x_expr}':y='{y_expr}',"
                f"scale=1080:1920:flags=lanczos,setsar=1[{label}]")
    if reframe == Reframe.blur_pad:
        return f"[{idx}:v]{base}[b{idx}];" + blur_pad_graph(f"b{idx}", label)
    if reframe == Reframe.center:
        cx0 = cx1 = 0.5
    else:
        cx0, cx1 = _interp(scene, start), _interp(scene, end)
    path = scene.crop_path if scene is not None and reframe == Reframe.subject_track else None
    return f"[{idx}:v]{base},{crop_filter(clip.width, clip.height, cx0, cx1, dur, path, start, speed)}[{label}]"


def render_segment(seg: Segment, clip: ClipInfo, scene: Scene | None, out: Path, preview: bool = False,
                   tail_frames: int = 0, grade: str | None = None,
                   compare_clip: ClipInfo | None = None, compare_scene: Scene | None = None, box=None,
                   color: str = "", stabilize: bool = False) -> Path:
    """tail_frames: frame tambahan di akhir segmen untuk tumpang tindih transisi xfade ke segmen berikutnya.
    grade: kunci GRADES (dari style preset). compare_*: adegan "sebelum" (mode before–after).
    color: filter penyeragam warna klip ini (render/color.py), dipasang sebelum look gaya.
    stabilize: footage goyang → vidstab 2 tahap (deteksi gerak, lalu transformasi dengan sedikit zoom)."""
    out_dur = seg.output_duration
    slot = frames_for(out_dur)
    n_frames = slot + tail_frames
    use_compare = seg.compare is not None and compare_clip is not None

    if use_compare:
        before_n, wipe_n = compare_split(slot)
        after_n = n_frames - before_n
        cmp = seg.compare
        before_span = (before_n + wipe_n) / FPS + 0.2
        inputs = ["-ss", f"{seg.start:.3f}", "-t", f"{after_n / FPS * seg.speed + 0.2:.3f}",
                  "-i", str(Path(clip.path).resolve()),
                  "-ss", f"{cmp.start:.3f}", "-t", f"{before_span:.3f}", "-i", str(Path(compare_clip.path).resolve())]
        graph = (
            _source_chain(0, seg.start, seg.end, seg.speed, seg.reframe, clip, scene, after_n / FPS, "sa") + ";"
            + _source_chain(1, cmp.start, cmp.end, 1.0, Reframe.subject_track, compare_clip, compare_scene,
                            (before_n + wipe_n) / FPS, "sb") + ";"
            f"[sb]trim=end_frame={before_n + wipe_n},setpts=PTS-STARTPTS,settb=AVTB[sb2];"
            f"[sa]trim=end_frame={after_n},setpts=PTS-STARTPTS,settb=AVTB[sa2];"
            f"[sb2][sa2]xfade=transition=wiperight:duration={wipe_n / FPS:.4f}:offset={before_n / FPS:.4f}[rf]"
        )
    else:
        span = (n_frames / FPS) * seg.speed + 0.2
        inputs = ["-ss", f"{seg.start:.3f}", "-t", f"{span:.3f}", "-i", str(Path(clip.path).resolve())]
        stab = None
        if stabilize and box is None:
            stab = f"{out.stem}.trf"  # nama relatif (cwd = folder render): path Windows "C:" merusak sintaks filter
            run_ffmpeg([*inputs, "-vf", f"vidstabdetect=shakiness=8:accuracy=9:result={stab}", "-f", "null", "-"],
                       cwd=out.parent)
        graph = _source_chain(0, seg.start, seg.end, seg.speed, seg.reframe, clip, scene, out_dur, "rf", box=box,
                              stab=stab)

    effect = entry_effect(seg.transition_in)
    post = f"{effect}," if effect else ""
    if color:
        post += color + ","
    if GRADES.get(grade or "none"):  # setelah crop 9:16: lebih ringan & vignette tepat di tepi layar
        post += GRADES[grade] + ","
    graph += f";[rf]{post}setsar=1,format=yuv420p[v]"

    run_ffmpeg([
        *inputs,
        "-filter_complex", graph, "-map", "[v]", "-an",
        "-frames:v", str(n_frames), "-r", str(FPS),
        "-c:v", "libx264", "-preset", "ultrafast" if preview else "veryfast", "-crf", "17",
        str(out.resolve()),
    ], cwd=out.parent)
    return out
