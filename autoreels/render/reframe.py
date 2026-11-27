"""Reframe ke 1080×1920: subject_track (crop mengikuti subjek, pan halus), center, blur_pad.

Crop dilakukan di resolusi sumber lalu di-scale (lebih cepat daripada scale dulu baru crop).
"""

from __future__ import annotations

OUT_W, OUT_H = 1080, 1920
OUT_ASPECT = OUT_W / OUT_H


def _even(x: float) -> int:
    return int(round(x / 2) * 2)


MAX_KNOTS = 24  # titik jalur crop per segmen (ekspresi ffmpeg bersarang tetap pendek)


def path_expr(points: list[tuple[float, float]]) -> str:
    """Ekspresi x(t) linear sepotong-sepotong dari [(t, x)] (t = detik keluaran segmen)."""
    if len(points) > MAX_KNOTS:
        step = (len(points) - 1) / (MAX_KNOTS - 1)
        points = [points[round(i * step)] for i in range(MAX_KNOTS)]
    expr = f"{points[-1][1]:.1f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(points, points[1:]))):
        seg = f"{x0:.1f}+({x1 - x0:.1f})*(t-{t0:.3f})/{max(t1 - t0, 1e-3):.3f}"
        expr = f"if(lt(t,{t1:.3f}),{seg},{expr})"
    return f"if(lt(t,{points[0][0]:.3f}),{points[0][1]:.1f},{expr})"


def crop_filter(src_w: int, src_h: int, cx0: float, cx1: float, duration: float,
                path: list | None = None, start: float = 0.0, speed: float = 1.0) -> str:
    """Crop 9:16 dengan pusat bergerak cx0 → cx1 (0–1 relatif lebar) selama `duration` detik.
    path: jalur pusat crop adegan [[detik sumber, cx], …] (Scene.crop_path) → crop mengikuti subjek; `start` &
    `speed` memetakan detik sumber ke detik keluaran segmen."""
    src_aspect = src_w / src_h
    if src_aspect <= OUT_ASPECT:  # sumber sudah potret/lebih sempit: crop vertikal di tengah
        crop_h = _even(src_w / OUT_ASPECT)
        return f"crop={src_w}:{crop_h}:0:(ih-{crop_h})/2,scale={OUT_W}:{OUT_H}:flags=lanczos"
    crop_w = _even(src_h * OUT_ASPECT)
    max_x = src_w - crop_w
    x0 = min(max_x, max(0, cx0 * src_w - crop_w / 2))
    x1 = min(max_x, max(0, cx1 * src_w - crop_w / 2))
    span = duration * speed
    pts = [((t - start) / speed, min(max_x, max(0.0, cx * src_w - crop_w / 2)))
           for t, cx in (path or []) if start - 0.5 <= t <= start + span + 0.5]
    if len(pts) >= 3 and max(x for _, x in pts) - min(x for _, x in pts) >= 2:
        return f"crop={crop_w}:{src_h}:x='{path_expr(pts)}':y=0,scale={OUT_W}:{OUT_H}:flags=lanczos"
    if abs(x1 - x0) < 2 or duration <= 0:
        x_expr = f"{x0:.1f}"
    else:
        x_expr = f"'{x0:.1f}+({x1 - x0:.1f})*min(1\\,t/{duration:.3f})'"
    return f"crop={crop_w}:{src_h}:{x_expr}:0,scale={OUT_W}:{OUT_H}:flags=lanczos"


def blur_pad_graph(inp: str, out: str) -> str:
    """Latar blur penuh + video utuh di tengah (untuk pemandangan lebar/drone)."""
    return (
        f"[{inp}]split=2[bp_a][bp_b];"
        f"[bp_a]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,crop={OUT_W}:{OUT_H},"
        f"boxblur=24:2,eq=brightness=-0.06:saturation=1.1[bp_bg];"
        f"[bp_b]scale={OUT_W}:-2:flags=lanczos[bp_fg];"
        f"[bp_bg][bp_fg]overlay=(W-w)/2:(H-h)/2[{out}]"
    )
