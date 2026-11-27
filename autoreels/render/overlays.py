"""Overlay: jadwal teks (hook, info per segmen, CTA) dan logo brand."""

from __future__ import annotations

from pathlib import Path

from autoreels.edl import EDL
from autoreels.render.cut import compare_split
from autoreels.render.reframe import OUT_H, OUT_W
from autoreels.render.text_ass import TextEvent

HOOK_MIN_SEC = 2.0
HOOK_MAX_SEC = 3.0
INFO_MIN_SEC = 1.2
LOGO_WIDTH = 150
LOGO_MARGIN_X = 48
LOGO_Y = int(OUT_H * 0.11)  # di bawah header UI Instagram


def segment_times(edl: EDL, fps: int = 30) -> list[tuple[float, float]]:
    """Waktu mulai/selesai tiap segmen di video akhir (presisi frame)."""
    out, t = [], 0.0
    for seg in edl.segments:
        d = max(1, round(seg.output_duration * fps)) / fps
        out.append((t, t + d))
        t += d
    return out


SUB_WORDS = 6  # kata per potongan subtitle voice over


def subtitle_chunks(timings: list[tuple[float, float, str]], total: float) -> list[TextEvent]:
    """Pecah tiap baris voice over jadi potongan ≤ 6 kata, waktunya dibagi rata menurut jumlah kata."""
    out: list[TextEvent] = []
    for start, end, text in timings:
        words = text.split()
        if not words or end - start < 0.2:
            continue
        chunks = [words[i:i + SUB_WORDS] for i in range(0, len(words), SUB_WORDS)]
        per_word = (min(end, total) - start) / len(words)
        t = start
        for ch in chunks:
            d = per_word * len(ch)
            out.append(TextEvent(round(t, 2), round(min(t + d, total), 2), "sub", " ".join(ch)))
            t += d
    return out


HOOK_CLEAR_MIN = 0.4  # sisa potongan subtitle setelah hook < 0,4 dtk → tidak ditampilkan


def clear_hook_zone(events: list[TextEvent], hook_end: float) -> list[TextEvent]:
    """Selama teks hook tampil, subtitle (karaoke/voice over) disembunyikan agar tidak bertabrakan.
    Potongan yang selesai sebelum hook hilang dibuang; yang melewatinya baru tampil setelah hook hilang
    (karaoke: disembunyikan lewat `reveal` agar waktu tiap kata tetap sinkron)."""
    out = []
    for ev in events:
        if ev.kind not in ("karaoke", "sub") or ev.start >= hook_end:
            out.append(ev)
            continue
        if ev.end - hook_end < HOOK_CLEAR_MIN:
            continue
        if ev.kind == "sub":
            ev.start = round(hook_end, 3)
        else:
            ev.reveal = round(hook_end - ev.start, 3)
        out.append(ev)
    return out


def text_events(edl: EDL, brand: dict, vo_timings: list[tuple[float, float, str]] | None = None,
                karaoke_words=None) -> list[TextEvent]:
    """Jadwal teks di layar. Bila ada voice over (vo_timings), teks info per segmen diganti subtitle VO;
    bila ada narasi (karaoke_words), diganti subtitle karaoke per kata."""
    times = segment_times(edl)
    total = times[-1][1]
    events: list[TextEvent] = []

    hook_end = min(HOOK_MAX_SEC, max(HOOK_MIN_SEC, times[0][1]))
    if edl.hook.overlay_text:
        events.append(TextEvent(0.0, hook_end, "hook", edl.hook.overlay_text))

    cta_start = edl.cta.at_sec if edl.cta else total
    if karaoke_words:
        from autoreels.render.text_ass import karaoke_events

        events.extend(karaoke_events(karaoke_words, total))
    elif vo_timings:
        events.extend(subtitle_chunks(vo_timings, total))
    if edl.hook.overlay_text:
        events = clear_hook_zone(events, hook_end)
    busy_until = hook_end + 0.15
    for seg, (s, e) in zip(edl.segments, [] if (vo_timings or karaoke_words) else times):
        if not seg.overlay_text or seg.index == 0:
            continue
        start = max(s, busy_until)
        end = min(max(e, start + INFO_MIN_SEC), cta_start - 0.1)
        if end - start < 0.9:
            continue
        events.append(TextEvent(start, end, "info", seg.overlay_text))
        busy_until = end + 0.1

    # before–after: label kecil "Sebelum" lalu "Sesudah" (berganti di tengah wipe)
    for seg, (s, e) in zip(edl.segments, times):
        if seg.compare is None:
            continue
        before_n, wipe_n = compare_split(round((e - s) * 30))
        switch = s + (before_n + wipe_n / 2) / 30
        events.append(TextEvent(s, switch, "badge", "Sebelum"))
        events.append(TextEvent(switch, e, "badge", "Sesudah"))

    if edl.cta:
        events.append(TextEvent(cta_start, total, "cta", edl.cta.text))
        wa = brand.get("whatsapp", {}).get("display")
        ig = instagram_for(brand, edl.pillar.value)
        show_wa = wa and wa not in edl.cta.text
        sub = " • ".join(x for x in [f"WA {wa}" if show_wa else None, ig] if x)
        if sub:
            events.append(TextEvent(cta_start + 0.25, total, "cta_sub", sub))
    return events


def instagram_for(brand: dict, pillar: str | None) -> str | None:
    """Handle IG yang ditampilkan di video: akun rental untuk pilar rental, selain itu akun utama."""
    ig = brand.get("instagram", {})
    return (ig.get("rental") if pillar == "rental" else None) or ig.get("main")


def logo_file_for(brand: dict, pillar: str | None) -> Path:
    """Logo khusus pilar (mis. Rental Motor untuk pilar rental) atau logo utama Brand."""
    from autoreels.config import PATHS

    logo = brand.get("logo", {})
    rel = (logo.get("per_pillar") or {}).get(pillar or "") or logo.get("file", "assets/logo/logo.png")
    return PATHS["config"].parent / rel


def prepare_logo(src: Path, dst: Path, width: int = LOGO_WIDTH) -> Path:
    """Potong ruang kosong logo, taruh di kartu putih bersudut bulat (PNG RGBA)."""
    import cv2
    import numpy as np

    img = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Logo tidak terbaca: {src}")
    if img.shape[2] == 4:
        rgb, alpha = img[:, :, :3], img[:, :, 3]
        mask = alpha > 20
    else:
        rgb = img
        alpha = None
        mask = (rgb < 235).any(axis=2)
    ys, xs = np.where(mask)
    if len(xs):
        pad = int(0.06 * max(np.ptp(xs), np.ptp(ys)))
        x0, x1 = max(0, xs.min() - pad), min(rgb.shape[1], xs.max() + pad)
        y0, y1 = max(0, ys.min() - pad), min(rgb.shape[0], ys.max() + pad)
        rgb = rgb[y0:y1, x0:x1]
        if alpha is not None:
            alpha = alpha[y0:y1, x0:x1]
    h = int(rgb.shape[0] * width / rgb.shape[1])
    rgb = cv2.resize(rgb, (width, h), interpolation=cv2.INTER_AREA)
    if alpha is not None:
        alpha = cv2.resize(alpha, (width, h), interpolation=cv2.INTER_AREA)
    card = np.full((h, width, 4), 255, dtype=np.uint8)
    card[:, :, :3] = rgb if alpha is None else (
        rgb * (alpha[..., None] / 255) + 255 * (1 - alpha[..., None] / 255)).astype(np.uint8)
    radius = max(6, width // 8)
    rmask = np.zeros((h, width), dtype=np.uint8)
    cv2.rectangle(rmask, (radius, 0), (width - radius, h), 255, -1)
    cv2.rectangle(rmask, (0, radius), (width, h - radius), 255, -1)
    for cx, cy in [(radius, radius), (width - radius - 1, radius), (radius, h - radius - 1),
                   (width - radius - 1, h - radius - 1)]:
        cv2.circle(rmask, (cx, cy), radius, 255, -1)
    card[:, :, 3] = (rmask * 0.92).astype(np.uint8)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dst), card)
    return dst


def logo_position(position: str, logo_w: int, logo_h: int) -> tuple[int, int]:
    right = OUT_W - logo_w - LOGO_MARGIN_X
    bottom = int(OUT_H * 0.78) - logo_h
    return {
        "top_left": (LOGO_MARGIN_X, LOGO_Y),
        "top_right": (right, LOGO_Y),
        "bottom_left": (LOGO_MARGIN_X, bottom),
        "bottom_right": (right, bottom),
    }.get(position, (right, LOGO_Y))
