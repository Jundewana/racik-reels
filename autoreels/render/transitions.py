"""Transisi antar segmen.

- cut: potong langsung.
- zoom_punch: efek masuk di awal segmen (zoom cepat 1.14× → 1×), tanpa tumpang tindih.
- fade / slide_left / whip: `xfade` FFmpeg. Segmen SEBELUMNYA dirender lebih panjang sebesar durasi transisi,
  lalu segmen berikutnya masuk tepat di titik potong (offset = waktu mulai segmen). Akibatnya titik potong tetap
  jatuh di ketukan musik dan durasi total video tidak berubah.
"""

from __future__ import annotations

from autoreels.edl import Transition
from autoreels.render.reframe import OUT_H, OUT_W

FPS = 30
ZOOM_AMOUNT = 0.14
ZOOM_SEC = 0.28

# transisi → (nama xfade FFmpeg, durasi maksimum detik)
XFADE = {
    Transition.fade: ("fade", 0.40),
    Transition.slide_left: ("slideleft", 0.35),
    Transition.whip: ("smoothleft", 0.22),  # sapuan cepat
}
# transisi tidak boleh memakan lebih dari porsi ini dari segmen yang dimasukinya
MAX_SHARE = 0.45


def entry_effect(transition: Transition) -> str | None:
    if transition == Transition.zoom_punch:
        return (
            f"scale=w='trunc({OUT_W}*(1+{ZOOM_AMOUNT}*max(0\\,1-t/{ZOOM_SEC}))/2)*2':h=-2:eval=frame,"
            f"crop={OUT_W}:{OUT_H}"
        )
    return None


def xfade_frames(transition: Transition, next_frames: int) -> int:
    """Jumlah frame tumpang tindih untuk transisi masuk ke segmen berdurasi `next_frames` (0 = bukan xfade)."""
    spec = XFADE.get(transition)
    if not spec or next_frames < 4:
        return 0
    return max(2, min(round(spec[1] * FPS), int(next_frames * MAX_SHARE)))


def join_graph(frames: list[int], transitions: list[Transition]) -> tuple[str, str]:
    """Filter_complex untuk menggabung segmen (input 0..n-1).

    frames[i] = jumlah frame slot segmen i di video akhir (tanpa ekor transisi).
    Segmen i yang diikuti xfade sudah dirender dengan ekor `xfade_frames(...)` frame.
    Kembalikan (graph, label keluaran).
    """
    parts = [f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[s{i}]" for i in range(len(frames))]
    acc = "s0"
    start_frames = 0
    for i in range(1, len(frames)):
        start_frames += frames[i - 1]
        out = f"j{i}"
        d = xfade_frames(transitions[i], frames[i])
        if d:
            name = XFADE[transitions[i]][0]
            parts.append(f"[{acc}][s{i}]xfade=transition={name}:duration={d / FPS:.4f}:"
                         f"offset={start_frames / FPS:.4f}[{out}]")
        else:
            parts.append(f"[{acc}][s{i}]concat=n=2:v=1:a=0[{out}]")
        acc = out
    return ";".join(parts), acc
