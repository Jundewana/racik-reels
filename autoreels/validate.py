"""[5] Validate — aturan keras (bukan LLM): sumber, adegan layak, hook, style, durasi, snap ke beat.

`validate_edl` memperbaiki hal yang aman diperbaiki otomatis (mencatatnya sebagai `fixes`) dan
mengembalikan `errors` untuk hal yang harus direvisi Director.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field

from autoreels.analyze.models import Analysis, MusicInfo, Scene
from autoreels.edl import CTA, EDL, Compare, MusicMood, Purpose, Reframe, SegmentRole, Transition

FPS = 30
HOOK_MAX_SEC = 3.0
CAPTION_MIN_CHARS = 40
HOOK_MAX_WORDS = 5
HOOK_MAX_CHARS = 28
MIN_SEG_SEC = 0.4
CTA_MIN_SEC = 2.5
DURATION_TOLERANCE = 0.10
BEAT_TOLERANCE = 0.12
PLACEHOLDER_RE = re.compile(r"\[(?:HARGA|ISI|N|[A-Z ]{2,})\]")

# Semua transisi EDL bisa dirender (cut, zoom_punch, dan xfade: fade/slide_left/whip — Tahap 2).
RENDERABLE_TRANSITIONS = set(Transition)


@dataclass
class ValidationResult:
    edl: EDL
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


HOOK_MIN_SIZE = 90  # px — sama dengan butir checklist "Teks hook cukup besar"


def _hook_fits_big(text: str) -> bool:
    """Syarat keterbacaan hook yang sebenarnya: ≤ 2 baris dengan ukuran huruf ≥ HOOK_MIN_SIZE."""
    from autoreels.render.text_ass import HOOK_SIZE, fit_text

    lines, size = fit_text(text, HOOK_SIZE, 14)
    return len(lines) <= 2 and size >= HOOK_MIN_SIZE and _words(text) <= HOOK_MAX_WORDS + 2


def _q(x: float) -> float:
    """Bulatkan ke kelipatan frame (30 fps)."""
    return round(round(x * FPS) / FPS, 4)


def _words(text: str | None) -> int:
    return len((text or "").split())


def _find_scene(analysis: Analysis, seg) -> Scene | None:
    if seg.scene_id:
        sc = next((s for s in analysis.scenes if s.scene_id == seg.scene_id), None)
        if sc and sc.source_file == seg.source_file:
            return sc
    mid = (seg.start + seg.end) / 2
    return next((s for s in analysis.scenes
                 if s.source_file == seg.source_file and s.start <= mid < s.end), None)


def _enforce_pace_and_fill(edl: EDL, analysis: Analysis, descriptions: dict, pace_min: float,
                           pace_max: float, allowed_tr: set, style: dict, F) -> None:
    """Pangkas/perpanjang segmen isi ke tempo style, lalu isi kekurangan durasi dengan adegan terbaik
    yang belum dipakai. Hook (segmen 0) dan CTA (segmen terakhir) tidak diubah di sini."""
    target = edl.target_duration_sec
    avg = (pace_min + pace_max) / 2
    middle = edl.segments[1:-1] if len(edl.segments) > 2 else []

    for seg in middle:
        scene = _find_scene(analysis, seg)
        if scene is None or not scene.usable:
            continue
        dur = seg.output_duration
        if dur > pace_max * 1.4:
            new_end = seg.start + pace_max * seg.speed
            F(f"segmen {seg.index}: {dur:.2f} dtk terlalu panjang untuk tempo style → {pace_max:.2f} dtk.")
            seg.end = round(new_end, 3)
        elif dur < pace_min * 0.75:
            new_end = min(scene.end, seg.start + avg * seg.speed)
            if new_end - seg.start < pace_min * 0.75 * seg.speed:  # mepet akhir adegan → geser mulai
                seg.start = round(max(scene.start, scene.end - avg * seg.speed), 3)
                new_end = scene.end
            F(f"segmen {seg.index}: {dur:.2f} dtk terlalu pendek → {(new_end - seg.start) / seg.speed:.2f} dtk.")
            seg.end = round(new_end, 3)

    def total() -> float:
        return sum(s.output_duration for s in edl.segments)

    if total() >= target * 0.97 or len(edl.segments) < 2:
        return

    used = {s.scene_id for s in edl.segments}

    def score(sc: Scene) -> float:
        d = descriptions.get(sc.scene_id)
        rel = getattr(d, "relevance_rental", 2) if d else 2
        hook = getattr(d, "hook_potential", 2) if d else 2
        return rel * 2 + hook + min(sc.motion, 5) * 0.2

    candidates = sorted((s for s in analysis.usable_scenes() if s.scene_id not in used and s.duration >= pace_min),
                        key=score, reverse=True)
    # adegan yang sudah dipakai boleh dipakai lagi di bagian lain bila stok habis
    reuse = sorted((s for s in analysis.usable_scenes() if s.scene_id in used and s.duration >= 3 * avg),
                   key=score, reverse=True)
    trs = [Transition(t) for t in style.get("transitions", ["cut"]) if Transition(t) in RENDERABLE_TRANSITIONS]
    added = 0
    pool = [(s, False) for s in candidates] + [(s, True) for s in reuse]
    while total() < target * 0.97 and pool:
        scene, is_reuse = pool.pop(0)
        need = min(avg, max(pace_min, target - total()))
        if is_reuse:
            start = scene.end - need - 0.2  # ambil bagian akhir adegan (berbeda dari yang sudah dipakai)
        else:
            start = scene.start + max(0.0, (scene.duration - need) / 2)
        cta = edl.segments[-1]
        tr = Transition.zoom_punch if (style.get("zoom_punch_on_emphasis") and Transition.zoom_punch in trs
                                       and added % 3 == 1) else Transition.cut
        new = cta.model_copy(update={
            "index": cta.index, "source_file": scene.source_file, "scene_id": scene.scene_id,
            "start": round(start, 3), "end": round(start + need, 3), "role": SegmentRole.isi, "speed": 1.0,
            "reason": "ditambahkan otomatis oleh validator (durasi kurang)", "overlay_text": None,
            "transition_in": tr, "keep_original_audio": False,
        })
        edl.segments.insert(len(edl.segments) - 1, new)
        added += 1
    if added:
        F(f"{added} segmen ditambahkan otomatis dari adegan terbaik yang belum dipakai "
          f"(durasi jadi {total():.1f} dtk).")
    for i, seg in enumerate(edl.segments):
        seg.index = i


COMPARE_MIN_SEC = 1.0  # adegan "sebelum" minimal ini (±45% durasi hook + wipe)


def _stage(descriptions: dict, scene_id: str | None) -> str | None:
    d = descriptions.get(scene_id) if scene_id else None
    return getattr(d, "stage", None) if d is not None else None


def _check_compare(edl: EDL, analysis: Analysis, descriptions: dict, F, W) -> None:
    """Rapikan `compare` (adegan "sebelum"): terjemahkan kode klip, paskan ke adegan layak, buang bila tidak valid.
    Hook before–after di pilar konstruksi tanpa `compare` → isi otomatis dengan adegan tahap "awal" terbaik."""
    for seg in edl.segments:
        cmp = seg.compare
        if cmp is None:
            continue
        if cmp.scene_id:
            m = re.search(r"K\d+-\d+", cmp.scene_id.upper())
            cmp.scene_id = m.group(0) if m else cmp.scene_id
        if analysis.clip(cmp.source_file) is None:
            sc = next((s for s in analysis.scenes if s.scene_id == cmp.scene_id), None)
            if sc is None and cmp.source_file:
                sc = next((s for s in analysis.scenes if s.scene_id.startswith(cmp.source_file.strip() + "-")), None)
            if sc is not None:
                cmp.source_file = sc.source_file
        scene = _find_scene(analysis, cmp) if analysis.clip(cmp.source_file) else None
        if scene is None or not scene.usable or scene.scene_id == seg.scene_id:
            why = "tidak ditemukan" if scene is None else "tidak layak" if not scene.usable else "sama dengan adegan sesudah"
            F(f"segmen {seg.index}: adegan 'sebelum' {why} → before–after dibatalkan.")
            seg.compare = None
            continue
        cmp.scene_id = scene.scene_id
        clip = analysis.clip(cmp.source_file)
        lo, hi = scene.start, min(scene.end, clip.duration - 1 / FPS)
        if hi - lo < COMPARE_MIN_SEC:
            F(f"segmen {seg.index}: adegan 'sebelum' {scene.scene_id} terlalu pendek → before–after dibatalkan.")
            seg.compare = None
            continue
        start = min(max(cmp.start, lo), hi - COMPARE_MIN_SEC)
        end = min(max(cmp.end, start + COMPARE_MIN_SEC), hi)
        if (round(start, 3), round(end, 3)) != (round(cmp.start, 3), round(cmp.end, 3)):
            F(f"segmen {seg.index}: rentang 'sebelum' dipaskan ke adegan {scene.scene_id}.")
        cmp.start, cmp.end = round(start, 3), round(end, 3)
        if _stage(descriptions, scene.scene_id) == "hasil" and _stage(descriptions, seg.scene_id) == "awal":
            W(f"segmen {seg.index}: adegan 'sebelum' bertahap hasil dan 'sesudah' bertahap awal — mungkin tertukar.")

    first = edl.segments[0]
    speaker_hook = edl.narration is not None and edl.narration.speaker_clip == first.source_file
    if edl.hook.type.value == "before_after" and first.compare is None and not speaker_hook:
        before = sorted(
            (s for s in analysis.usable_scenes()
             if _stage(descriptions, s.scene_id) == "awal" and s.scene_id != first.scene_id
             and s.duration >= COMPARE_MIN_SEC),
            key=lambda s: (getattr(descriptions.get(s.scene_id), "hook_potential", 0), s.sharpness), reverse=True)
        if before:
            sc = before[0]
            first.compare = Compare(source_file=sc.source_file, scene_id=sc.scene_id,
                                    start=round(sc.start, 3), end=round(min(sc.end, sc.start + 2.5), 3))
            F(f"hook before–after: adegan 'sebelum' diisi otomatis = {sc.scene_id} (tahap awal).")
        else:
            W("hook before–after tanpa adegan 'sebelum' (tidak ada adegan bertahap awal) — tampil sebagai hook biasa.")


def _phrase_frames(phrases) -> list[int]:
    """Jumlah frame tiap frasa dari batas kumulatif (tanpa geser: total frame = durasi narasi)."""
    bounds = [round(p.start * FPS) for p in phrases] + [round(phrases[-1].end * FPS)]
    return [max(1, b - a) for a, b in zip(bounds, bounds[1:])]


MOMENT_GAIN = 0.08   # geser hanya bila momen terbaik ≥ 0,08 (skala 0–1) lebih baik dari pilihan Director


def _snap_to_moments(edl: EDL, analysis: Analysis, F) -> None:
    """Potongan b-roll yang skornya jauh di bawah momen terbaik adegannya digeser ke momen itu (durasi tetap, tetap
    di dalam adegan, tidak menimpa rentang segmen lain dari file yang sama). Pembicara & before–after tidak disentuh."""
    from autoreels.analyze.moments import best_window, window_score

    speaker = edl.narration.speaker_clip if edl.narration is not None else None
    for seg in edl.segments:
        if seg.source_file == speaker or seg.compare is not None:
            continue
        scene = _find_scene(analysis, seg)
        clip = analysis.clip(seg.source_file)
        if scene is None or clip is None or not scene.moment_curve:
            continue
        span = seg.end - seg.start
        now = window_score(scene.moment_curve, seg.start, seg.end)
        others = [(s.start, s.end) for s in edl.segments if s is not seg and s.source_file == seg.source_file]
        found = best_window(scene.moment_curve, scene.start, min(scene.end, clip.duration - 1 / FPS), span, others)
        if now is None or found is None or found[1] - now < MOMENT_GAIN:
            continue
        F(f"segmen {seg.index}: digeser ke momen terbaik adegan {seg.scene_id} "
          f"({seg.start:.1f} → {found[0]:.1f} dtk, skor {now:.2f} → {found[1]:.2f}).")
        seg.start, seg.end = found[0], round(found[0] + span, 3)


SPEAKER_MIN_SHARE = 0.6   # video bicara: pembicara tampil ≥ 60% durasi
MAX_BROLL_RUN = 2         # maks segmen b-roll berurutan


def _enforce_talk_layout(edl: EDL, F) -> None:
    """Video bicara: hook, cold open & segmen terakhir = pembicara; b-roll maks 2 berurutan; pembicara ≥ 60%.
    Pelanggaran → segmen b-roll dikembalikan ke pembicara (waktunya dikunci ke ucapan oleh _fit_to_phrases)."""
    nar = edl.narration
    speaker, segs, phrases = nar.speaker_clip, edl.segments, nar.phrases

    def to_speaker(i: int, why: str) -> None:
        s = segs[i]
        F(f"segmen {i}: b-roll {s.scene_id or s.source_file} → pembicara ({why}).")
        s.source_file, s.scene_id, s.speed = speaker, None, 1.0
        s.reframe = Reframe.subject_track
        s.compare = None

    must = {0, len(segs) - 1} | {i for i, p in enumerate(phrases) if p.start < nar.cold_open_sec - 0.01}
    for i in sorted(must):
        if i < len(segs) and segs[i].source_file != speaker:
            to_speaker(i, "hook/cold open/penutup wajib wajah pembicara")
    run = 0
    for i, s in enumerate(segs):
        run = run + 1 if s.source_file != speaker else 0
        if run > MAX_BROLL_RUN:
            to_speaker(i, f"maks {MAX_BROLL_RUN} b-roll berurutan")
            run = 0
    total = sum(p.duration for p in phrases) or 1.0
    broll = sorted((i for i, s in enumerate(segs) if s.source_file != speaker), key=lambda i: -phrases[i].duration)
    shown = sum(phrases[i].duration for i, s in enumerate(segs) if s.source_file == speaker)
    for i in broll:
        if shown / total >= SPEAKER_MIN_SHARE:
            break
        to_speaker(i, f"pembicara harus tampil ≥ {SPEAKER_MIN_SHARE:.0%}")
        shown += phrases[i].duration


def _fit_to_phrases(edl: EDL, analysis: Analysis, descriptions: dict, F, E) -> None:
    """Alur narasi: segmen i ↔ frasa i, durasi tampil = durasi frasa (presisi frame). Adegan yang terlalu
    pendek untuk frasanya diganti otomatis dengan adegan layak yang cukup panjang (dicatat sebagai perbaikan)."""
    phrases = edl.narration.phrases
    n = len(phrases)
    if len(edl.segments) > n:
        extra = edl.segments[n - 1:-1]  # pertahankan segmen terakhir (CTA)
        edl.segments = edl.segments[: n - 1] + edl.segments[-1:]
        F(f"{len(extra)} segmen berlebih dibuang (harus satu segmen per frasa: {n}).")
    if len(edl.segments) < n:
        E(f"jumlah segmen {len(edl.segments)} ≠ jumlah frasa narasi {n}. Buat tepat {n} segmen, satu per frasa.")
        return
    if edl.narration.speaker_clip:
        _enforce_talk_layout(edl, F)
    used = {s.scene_id for s in edl.segments}

    def score(sc: Scene) -> float:
        d = descriptions.get(sc.scene_id)
        return (getattr(d, "relevance_rental", 0) * 2 + getattr(d, "hook_potential", 0)) if d else 0.0

    speaker = edl.narration.speaker_clip
    for i, (seg, frames) in enumerate(zip(edl.segments, _phrase_frames(phrases))):
        want = frames / FPS
        ph = phrases[i]
        if speaker and ph.src_start is not None and seg.source_file == speaker:
            # video bicara: gambar pembicara dikunci ke waktu aslinya agar bibir sinkron dengan suara
            seg.speed = 1.0
            seg.start = ph.src_start
            seg.end = round(ph.src_start + want, 3)
            sc = next((s for s in analysis.scenes if s.source_file == speaker and s.start - 1e-3 <= seg.start < s.end),
                      None)
            if sc is not None:
                seg.scene_id = sc.scene_id
            # pembicara → pembicara: cukup cut (satu video yang sama; transisi berulang memusingkan)
            if i > 0 and edl.segments[i - 1].source_file == speaker and seg.transition_in != Transition.cut:
                F(f"segmen {i}: transisi '{seg.transition_in.value}' antar potongan pembicara → cut.")
                seg.transition_in = Transition.cut
            continue
        span = want * seg.speed
        scene = _find_scene(analysis, seg)
        clip = analysis.clip(seg.source_file)
        if scene is not None and clip is not None:
            hi = min(scene.end, clip.duration - 1 / FPS)
            if hi - scene.start >= span:
                if hi - seg.start < span:  # geser mulai agar muat di adegan
                    seg.start = round(hi - span, 3)
                seg.end = round(seg.start + span, 3)
                continue
        prev_id = edl.segments[i - 1].scene_id if i else None
        pool = [sc for sc in analysis.usable_scenes()
                if sc.duration >= want and sc.scene_id != prev_id]
        if not pool:
            E(f"segmen {i}: tidak ada adegan layak sepanjang {want:.1f} dtk untuk frasa P{i + 1}.")
            continue
        pool.sort(key=lambda sc: (sc.scene_id in used, -score(sc)))
        sc = pool[0]
        F(f"segmen {i}: adegan {seg.scene_id or '?'} terlalu pendek untuk frasa P{i + 1} ({want:.1f} dtk) "
          f"→ diganti {sc.scene_id}.")
        seg.source_file, seg.scene_id, seg.speed = sc.source_file, sc.scene_id, 1.0
        seg.start = round(sc.start, 3)
        seg.end = round(sc.start + want, 3)
        used.add(sc.scene_id)


SPEED_MIN_USEFUL = 2.0   # di bawah ini speed-up tidak terasa sebagai timelapse
SPEED_MAX_MOTION = 3.0   # adegan lebih dinamis dari ini (mis. percikan gerinda) tidak dipercepat


def _auto_speed_progress(edl: EDL, analysis: Analysis, descriptions: dict, style: dict, F) -> None:
    """Gaya dengan `default_speed_progress` (mis. proyek_profesional): segmen isi bertahap "proses" yang lambat
    dipercepat (timelapse). Durasi tampil tetap — rentang sumber diperpanjang — jadi tempo & beat tidak berubah."""
    default = style.get("default_speed_progress")
    if not default:
        return
    speed_max = style.get("speed_range", [1.0, default])[1]
    changed = []
    for seg in edl.segments:
        if seg.role not in (SegmentRole.isi, SegmentRole.bukti) or seg.speed > 1.01 or seg.compare is not None:
            continue
        if _stage(descriptions, seg.scene_id) != "proses":
            continue
        scene = _find_scene(analysis, seg)
        clip = analysis.clip(seg.source_file)
        if scene is None or clip is None or scene.motion > SPEED_MAX_MOTION:
            continue
        out = seg.output_duration
        avail = min(scene.end, clip.duration - 1 / FPS) - seg.start
        speed = min(float(default), float(speed_max), avail / out if out > 0 else 0)
        if speed < SPEED_MIN_USEFUL:
            continue
        seg.speed = round(speed, 2)
        seg.end = round(seg.start + out * seg.speed, 3)
        changed.append(f"{seg.index} ({seg.speed:g}×)")
    if changed:
        F(f"speed-up adegan proses (timelapse): segmen {', '.join(changed)}.")


def validate_edl(
    edl: EDL,
    analysis: Analysis,
    style: dict,
    music: MusicInfo | None,
    brand: dict,
    pillar_hashtags: list[str] | None = None,
    descriptions: dict | None = None,
) -> ValidationResult:
    edl = EDL.model_validate(edl.model_dump(mode="json"))  # salinan bersih & tervalidasi ulang
    r = ValidationResult(edl)
    E, W, F = r.errors.append, r.warnings.append, r.fixes.append
    target = edl.target_duration_sec

    # --- 1. sumber & adegan -------------------------------------------------------
    pace_min, pace_max = style.get("cut_pace_sec", [0.5, 3.0])
    speed_min, speed_max = style.get("speed_range", [1.0, 1.5])
    allowed_tr = {Transition(t) for t in style.get("transitions", ["cut"])}
    used_ranges: dict[str, list[tuple[float, float]]] = {}

    for seg in edl.segments:
        if seg.scene_id:
            m = re.search(r"K\d+-\d+", seg.scene_id.upper())
            seg.scene_id = m.group(0) if m else seg.scene_id
        clip = analysis.clip(seg.source_file)
        if clip is None:
            # Director memakai kode klip ("K4") — terjemahkan lewat scene_id
            sc = next((s for s in analysis.scenes if s.scene_id == seg.scene_id), None)
            if sc is None and seg.source_file:
                prefix = seg.source_file.strip() + "-"
                sc = next((s for s in analysis.scenes if s.scene_id.startswith(prefix)), None)
            if sc is not None:
                seg.source_file = sc.source_file
                clip = analysis.clip(seg.source_file)
        if clip is None:
            E(f"segmen {seg.index}: source_file '{seg.source_file}' tidak ada di footage.")
            continue
        if edl.narration is not None and edl.narration.speaker_clip == seg.source_file:
            # video bicara: rentang wajah pembicara diatur _fit_to_phrases (sinkron bibir); suara dari narasi
            if seg.transition_in not in allowed_tr:
                F(f"segmen {seg.index}: transisi '{seg.transition_in.value}' tidak ada di style → cut.")
                seg.transition_in = Transition.cut
            seg.keep_original_audio = False
            continue
        scene = _find_scene(analysis, seg)
        if scene is None:
            E(f"segmen {seg.index}: rentang {seg.start:.2f}–{seg.end:.2f} tidak cocok dengan adegan mana pun.")
            continue
        if not scene.usable:
            E(f"segmen {seg.index}: memakai adegan {scene.scene_id} yang tidak layak ({'; '.join(scene.reasons)}).")
            continue
        seg.scene_id = scene.scene_id
        lo, hi = scene.start, min(scene.end, clip.duration - 1 / FPS)
        if seg.start < lo - 0.01 or seg.end > hi + 0.01:
            new_start = min(max(seg.start, lo), hi - MIN_SEG_SEC)
            new_end = min(max(seg.end, new_start + MIN_SEG_SEC), hi)
            F(f"segmen {seg.index}: rentang dipaskan ke adegan {scene.scene_id} "
              f"({seg.start:.2f}–{seg.end:.2f} → {new_start:.2f}–{new_end:.2f}).")
            seg.start, seg.end = round(new_start, 3), round(new_end, 3)
        if not speed_min <= seg.speed <= speed_max:
            new_speed = min(max(seg.speed, speed_min), speed_max)
            F(f"segmen {seg.index}: speed {seg.speed} → {new_speed} (batas style {speed_min}–{speed_max}).")
            seg.speed = new_speed
        if seg.transition_in not in allowed_tr:
            F(f"segmen {seg.index}: transisi '{seg.transition_in.value}' tidak ada di style → cut.")
            seg.transition_in = Transition.cut
        if seg.keep_original_audio and not clip.has_audio:
            seg.keep_original_audio = False
        for a, b in used_ranges.get(seg.source_file, []):
            overlap = min(b, seg.end) - max(a, seg.start)
            if overlap > 0.5:
                W(f"segmen {seg.index}: memakai ulang bagian yang sama ({overlap:.1f} dtk tumpang tindih).")
        used_ranges.setdefault(seg.source_file, []).append((seg.start, seg.end))

    # --- 1b. before–after (compare) ------------------------------------------------
    _check_compare(edl, analysis, descriptions or {}, F, W)

    # --- 1c. speed-up kronologis (konstruksi) ---------------------------------------
    narr = edl.narration is not None
    if not narr:
        _auto_speed_progress(edl, analysis, descriptions or {}, style, F)
    else:  # --- 1d. alur narasi: satu segmen per frasa, durasi = durasi frasa ---------------
        _fit_to_phrases(edl, analysis, descriptions or {}, F, E)

    # --- 2. hook ------------------------------------------------------------------
    first = edl.segments[0]
    if first.role != SegmentRole.hook:
        F("segmen 0 dijadikan role 'hook'.")
        first.role = SegmentRole.hook
    if edl.hook.source_segment_index != 0:
        F("hook.source_segment_index → 0 (hook harus segmen pertama).")
        edl.hook.source_segment_index = 0
    if first.output_duration > HOOK_MAX_SEC:
        new_end = first.start + HOOK_MAX_SEC * first.speed
        F(f"segmen hook dipangkas {first.output_duration:.2f} → {HOOK_MAX_SEC:.2f} dtk.")
        first.end = round(new_end, 3)
    hook_text = (edl.hook.overlay_text or "").strip()
    if not hook_text:
        E("hook.overlay_text kosong — teks hook wajib ada.")
    elif (_words(hook_text) > HOOK_MAX_WORDS or len(hook_text) > HOOK_MAX_CHARS) and _hook_fits_big(hook_text):
        # sedikit melewati batas kata/huruf tetapi tetap tampil besar dalam ≤ 2 baris (syarat sebenarnya)
        W(f"hook.overlay_text '{hook_text}' melewati {HOOK_MAX_WORDS} kata/{HOOK_MAX_CHARS} huruf, "
          "tetapi masih tampil besar dalam 2 baris.")
    elif _words(hook_text) > HOOK_MAX_WORDS or len(hook_text) > HOOK_MAX_CHARS:
        E(f"hook.overlay_text terlalu panjang ('{hook_text}': {_words(hook_text)} kata, {len(hook_text)} huruf). "
          f"Maks {HOOK_MAX_WORDS} kata & {HOOK_MAX_CHARS} huruf agar teks hook tampil BESAR. Persingkat & buat lebih menohok.")

    # --- 2b. tempo & durasi: perbaikan deterministik (tidak bergantung kepatuhan LLM) ----
    if not narr:  # alur narasi: tempo mengikuti frasa, bukan style
        _enforce_pace_and_fill(edl, analysis, descriptions or {}, pace_min, pace_max, allowed_tr, style, F)

    # --- 2c. zoom-punch wajib bila style memintanya (Director kadang hanya memakai cut) ----------
    if style.get("zoom_punch_on_emphasis") and Transition.zoom_punch in allowed_tr \
            and not any(s.transition_in == Transition.zoom_punch for s in edl.segments):
        middle = [s for s in edl.segments[1:-1] if s.role in (SegmentRole.isi, SegmentRole.bukti)]
        picks = [s for s in middle if s.output_duration >= MIN_SEG_SEC * 1.5][1::3][:3] or middle[:1]
        for s in picks:
            s.transition_in = Transition.zoom_punch
        if picks:
            F(f"zoom-punch ditambahkan di segmen {', '.join(str(s.index) for s in picks)} (wajib di style ini).")

    # --- 2d. momen terbaik: b-roll digeser ke bagian adegan yang paling layak (sebelum snap beat) ----
    _snap_to_moments(edl, analysis, F)

    # --- 3. musik sesuai style ----------------------------------------------------
    style_mood = style.get("music_mood_default", "upbeat")
    no_music = edl.music.mood == MusicMood.none and music is None  # pilihan pengguna: tanpa musik
    if no_music:
        edl.music.cut_on_beat = False
    elif edl.music.mood.value != style_mood:
        F(f"music.mood '{edl.music.mood.value}' → '{style_mood}' (sesuai style preset).")
        edl.music.mood = MusicMood(style_mood)

    # --- 4. snap potongan ke beat --------------------------------------------------
    on_beat = 0
    boundaries = 0
    if music and music.beats and edl.music.cut_on_beat and not narr:  # narasi: potongan di batas frasa
        beats = sorted(b for b in music.beats if b > 0)
        # posisi dihitung dalam frame kumulatif (sama seperti render), agar pembulatan frame per segmen
        # tidak menumpuk menjadi pergeseran dari beat pada video dengan banyak potongan pendek
        cursor_f = 0
        for i, seg in enumerate(edl.segments):
            cursor = cursor_f / FPS
            scene = _find_scene(analysis, seg)
            clip = analysis.clip(seg.source_file)
            if scene is None or clip is None:
                cursor_f += round(seg.output_duration * FPS)
                continue
            max_end_src = min(scene.end, clip.duration - 1 / FPS)
            want = cursor + seg.output_duration
            limit = cursor + (max_end_src - seg.start) / seg.speed
            if i == 0:
                limit = min(limit, HOOK_MAX_SEC)
            j = bisect.bisect_left(beats, want)
            candidates = [b for b in beats[max(0, j - 2): j + 2]
                          if b - cursor >= MIN_SEG_SEC and b <= limit + 1e-6]
            if candidates:
                best = min(candidates, key=lambda b: abs(b - want))
                n = round(best * FPS) - cursor_f
                if seg.start + n / FPS * seg.speed > max_end_src + 1e-6 or (i == 0 and n / FPS > HOOK_MAX_SEC):
                    n -= 1  # pembulatan ke frame terdekat tidak boleh melewati batas adegan / batas hook
                seg.end = round(seg.start + n / FPS * seg.speed, 3)
            cursor_f += round(seg.output_duration * FPS)
        # hitung ketepatan beat (setelah kuantisasi frame)
        t = 0.0
        for seg in edl.segments[:-1]:
            t += _q(seg.output_duration)
            boundaries += 1
            k = bisect.bisect_left(beats, t)
            near = min((abs(beats[m] - t) for m in (k - 1, k) if 0 <= m < len(beats)), default=9)
            on_beat += near <= BEAT_TOLERANCE

    # --- 5. durasi total ------------------------------------------------------------
    total = sum(_q(s.output_duration) for s in edl.segments)
    if total > target * (1 + DURATION_TOLERANCE):
        # pangkas segmen tengah (bukan hook & CTA) dari belakang
        while total > target * (1 + DURATION_TOLERANCE) and len(edl.segments) > 3:
            dropped = edl.segments.pop(-2)
            total -= _q(dropped.output_duration)
            F(f"segmen {dropped.index} dibuang agar durasi tidak melebihi target.")
    if total < target * (1 - DURATION_TOLERANCE):
        E(f"durasi total {total:.1f} dtk terlalu pendek (target {target} dtk ±10%). Tambah/perpanjang segmen.")
    elif total > target * (1 + DURATION_TOLERANCE):
        E(f"durasi total {total:.1f} dtk terlalu panjang (target {target} dtk ±10%).")

    # --- 6. tempo potongan sesuai style -------------------------------------------
    middle = [s for s in edl.segments[1:-1]]
    in_pace = [s for s in middle if pace_min * 0.75 <= s.output_duration <= pace_max * 1.4]
    pace_ratio = 1.0 if narr else (len(in_pace) / len(middle) if middle else 1.0)
    if middle and pace_ratio < 0.6:
        durs = ", ".join(f"{s.output_duration:.1f}" for s in middle)
        E(f"tempo potongan tidak sesuai style: hanya {pace_ratio:.0%} segmen isi dalam rentang "
          f"{pace_min}–{pace_max} dtk (durasi sekarang: {durs}).")

    last = edl.segments[-1]
    promo = edl.purpose == Purpose.promosi
    if promo and last.role != SegmentRole.cta:
        F(f"segmen terakhir ({last.index}) dijadikan role 'cta'.")
        last.role = SegmentRole.cta
    if promo and last.output_duration < CTA_MIN_SEC - 0.05:
        W(f"segmen CTA hanya {last.output_duration:.1f} dtk (disarankan ≥ {CTA_MIN_SEC} dtk).")

    # --- 7. CTA ---------------------------------------------------------------------
    default_cta = brand.get("default_cta", {}).get(edl.pillar.value, "Hubungi kami via WhatsApp!")
    if not promo:  # video informasi: tanpa CTA jualan (keputusan Director / pengguna)
        if edl.cta is not None:
            F("video informasi → CTA dihapus.")
        edl.cta = None
        if last.role == SegmentRole.cta:
            last.role = SegmentRole.isi
    elif edl.cta is None or not edl.cta.text.strip():
        edl.cta = CTA(text=default_cta, at_sec=max(0.0, total - 3.0))
        F("CTA kosong → memakai CTA default brand.")
    if edl.cta is not None and not (total - 4.5 <= edl.cta.at_sec <= total - 1.5):
        new_at = round(max(0.0, total - 3.0), 2)
        F(f"cta.at_sec {edl.cta.at_sec} → {new_at} (CTA harus tampil ±3 dtk terakhir).")
        edl.cta.at_sec = new_at

    # --- 8. teks: panjang & placeholder --------------------------------------------
    texts = {"hook": edl.hook.overlay_text, "cta": edl.cta.text if edl.cta else "",
             "caption": edl.caption_suggestion}
    for seg in edl.segments:
        if seg.overlay_text:
            texts[f"segmen {seg.index}"] = seg.overlay_text
            if _words(seg.overlay_text) > 8:
                E(f"overlay_text segmen {seg.index} terlalu panjang ({_words(seg.overlay_text)} kata, maks 6).")
    for where, text in texts.items():
        if text and PLACEHOLDER_RE.search(text):
            E(f"{where} masih berisi placeholder {PLACEHOLDER_RE.search(text).group(0)} — "
              "jangan pakai placeholder; hilangkan info yang tidak diketahui.")

    if len((edl.caption_suggestion or "").strip()) < CAPTION_MIN_CHARS:
        E(f"caption_suggestion kosong/terlalu pendek (min {CAPTION_MIN_CHARS} huruf) — tulis caption Instagram "
          "2–4 kalimat + ajakan WhatsApp.")

    # --- 9. hashtag ------------------------------------------------------------------
    merged: list[str] = []
    for tag in [*(pillar_hashtags or []), *edl.hashtags]:
        tag = "#" + re.sub(r"[^0-9a-zA-Z_]", "", tag.lstrip("#")).lower()
        if len(tag) > 1 and tag not in merged:
            merged.append(tag)
    edl.hashtags = merged[:12]

    # --- 10. rapikan index -------------------------------------------------------------
    for i, seg in enumerate(edl.segments):
        seg.index = i

    r.stats = {
        "total_duration": round(total, 2),
        "target_duration": target,
        "segments": len(edl.segments),
        "hook_duration": round(_q(edl.segments[0].output_duration), 2),
        "beat_accuracy": round(on_beat / boundaries, 3) if boundaries else None,
        "pace_ratio": round(pace_ratio, 3),
        "flow": "narasi" if narr else "video",
        "phrases": len(edl.narration.phrases) if narr else None,
    }
    r.edl = EDL.model_validate(edl.model_dump())
    return r
