"""Cari cuplikan: video bicara panjang (podcast, kuliah, wawancara) → 3–5 kandidat cuplikan 1–3 menit yang
berdiri sendiri, untuk dijadikan Reel masing-masing lewat alur video bicara.

Langkah: transkrip (di-cache) → kalimat → LLM mengusulkan rentang kalimat (prompts/highlight_find.md) → kode
merapikan (batas kalimat, durasi 60–180 dtk, tanpa tumpang tindih) → pengguna memilih → potong ke
footage/<folder>/cuplikan/<judul>.mp4.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from autoreels.talk import Sentence, split_sentences, weak_hook

MIN_SEC, MAX_SEC = 60.0, 180.0    # Tahap 3: video bicara 1–3 menit → Reel 30–45 dtk
EDGE_PAD = 0.3                    # napas di awal/akhir potongan (tidak memotong kata)
MAX_OVERLAP = 0.25                # kandidat yang tumpang tindih > 25% dengan yang lebih bagus dibuang
GROQ_SAFE_TOKENS = 6000           # transkrip panjang melebihi batas TPM Groq gratis → pakai model cadangan (Gemini)


@dataclass
class Candidate:
    rank: int
    title: str
    reason: str
    score: int
    start: float        # detik di video sumber
    end: float
    first: int          # indeks kalimat awal/akhir
    last: int
    hook: str
    preview: str

    @property
    def duration(self) -> float:
        return self.end - self.start


class _Pick(BaseModel):
    start: int
    end: int
    title: str = ""
    reason: str = ""
    score: int = Field(3, ge=1, le=5)


class _Span(BaseModel):
    start: int
    end: int
    title: str = ""


class _Picks(BaseModel):
    topic: _Span | None = None   # rentang lengkap topik yang diminta `instruksi` (None bila tidak ada topik)
    candidates: list[_Pick]


TOPIC_MAX_PARTS = 8     # topik panjang dipecah maks 8 bagian berurutan
TOPIC_MIN_GAP = 20.0    # celah topik yang belum tercakup ≥ 20 dtk → dibuat bagian tambahan
TOPIC_MIN_PART = 30.0   # bagian topik boleh lebih pendek dari MIN_SEC (sisa topik), asal ≥ 30 dtk


def _clock(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def transcript_lines(sentences: list[Sentence]) -> list[str]:
    """Satu baris per kalimat; awalan '~' = kalimat lemah sebagai pembuka (butuh konteks sebelumnya)."""
    return [f"{'~' if weak_hook(s) else ''}S{s.index} [{_clock(s.start)}] {s.text}" for s in sentences]


TERMINAL = (".", "?", "!")
SNAP_SENTENCES = 4    # geser batas maks 4 potongan kalimat


def _ends_sentence(s: Sentence) -> bool:
    return s.text.rstrip().endswith(TERMINAL)


def _true_start(sentences: list[Sentence], k: int) -> bool:
    """Awal kalimat sungguhan: kalimat sebelumnya berakhir tanda baca akhir atau ada jeda panjang (> 1 dtk).
    (Transkrip juga memecah di jeda napas, jadi tidak setiap potongan adalah awal kalimat.)"""
    return k == 0 or _ends_sentence(sentences[k - 1]) or sentences[k].start - sentences[k - 1].end > 1.0


def _snap_start(sentences: list[Sentence], a: int, b: int) -> int:
    """Mundur (lalu maju) ke awal kalimat sungguhan yang layak membuka, agar cuplikan tidak mulai di tengah kalimat."""
    for k in range(a, max(-1, a - SNAP_SENTENCES - 1), -1):
        if _true_start(sentences, k) and not weak_hook(sentences[k]):
            return k
    for k in range(a + 1, min(b, a + SNAP_SENTENCES + 1)):
        if _true_start(sentences, k) and not weak_hook(sentences[k]):
            return k
    for k in range(a, max(-1, a - SNAP_SENTENCES - 1), -1):  # setidaknya awal kalimat, walau pembukanya lemah
        if _true_start(sentences, k):
            return k
    return a


def _snap_end(sentences: list[Sentence], b: int) -> int:
    """Maju ke akhir kalimat sungguhan (bertanda baca akhir)."""
    for k in range(b, min(len(sentences), b + SNAP_SENTENCES + 1)):
        if _ends_sentence(sentences[k]):
            return k
    return b


def _make(sentences: list[Sentence], a: int, b: int, title: str, reason: str, score: int) -> Candidate:
    start, end = max(0.0, sentences[a].start - EDGE_PAD), sentences[b].end + EDGE_PAD
    words = " ".join(s.text for s in sentences[a:b + 1]).split()
    return Candidate(rank=0, title=(title or sentences[a].text)[:80], reason=reason, score=score,
                     start=round(start, 2), end=round(end, 2), first=a, last=b, hook=sentences[a].text,
                     preview=" ".join(words[:40]) + (" …" if len(words) > 40 else ""))


def _chunks(sentences: list[Sentence], a: int, b: int) -> list[tuple[int, int]]:
    """Pecah kalimat a..b menjadi potongan berurutan ≤ MAX_SEC, batas di akhir kalimat sungguhan."""
    out = []
    while a <= b:
        e = a
        while e < b and sentences[e + 1].end - sentences[a].start <= MAX_SEC:
            e += 1
        if e < b:  # mundur ke akhir kalimat sungguhan bila masih ≥ MIN_SEC
            k = e
            while k > a and not _ends_sentence(sentences[k]):
                k -= 1
            if k > a and sentences[k].end - sentences[a].start >= MIN_SEC:
                e = k
        out.append((a, e))
        a = e + 1
    if len(out) > 1 and sentences[out[-1][1]].end - sentences[out[-1][0]].start < TOPIC_MIN_PART:
        last = out.pop()  # sisa terlalu pendek → gabung ke bagian sebelumnya bila tetap ≤ MAX_SEC (batas Reels)
        prev = out.pop()
        a, b = prev[0], last[1]
        if sentences[b].end - sentences[a].start <= MAX_SEC:
            out.append((a, b))
        else:  # bagi dua sama panjang agar sisa topik tidak terbuang
            half = sentences[a].start + (sentences[b].end - sentences[a].start) / 2
            m = next(k for k in range(a, b) if sentences[k].end >= half)
            out += [(a, m), (m + 1, b)]
    return out


def cover_topic(cands: list[Candidate], topic: _Span, sentences: list[Sentence]) -> list[Candidate]:
    """Topik yang diminta harus tercakup utuh: celah di dalam rentang topik yang tidak masuk cuplikan mana pun
    dijadikan bagian tambahan. Hasil: bagian topik urut waktu + diberi nomor "(bagian i/k)", lalu kandidat lain."""
    last_i = len(sentences) - 1
    a0, b0 = max(0, min(topic.start, last_i)), max(0, min(topic.end, last_i))
    if b0 < a0:
        a0, b0 = b0, a0
    a0, b0 = _snap_start(sentences, a0, b0), _snap_end(sentences, b0)
    t0, t1 = sentences[a0].start, sentences[b0].end
    inside = [c for c in cands if c.end > t0 and c.start < t1]
    others = [c for c in cands if c not in inside]
    covered = sorted((c.first, c.last) for c in inside)
    gaps, cur = [], a0
    for f, l in covered:
        if f > cur:
            gaps.append((cur, f - 1))
        cur = max(cur, l + 1)
    if cur <= b0:
        gaps.append((cur, b0))
    title = topic.title or (inside[0].title if inside else sentences[a0].text)
    for ga, gb in gaps:
        if sentences[gb].end - sentences[ga].start < TOPIC_MIN_GAP:
            continue
        for ca, cb in _chunks(sentences, ga, gb):
            if sentences[cb].end - sentences[ca].start >= TOPIC_MIN_PART:
                inside.append(_make(sentences, ca, cb, title, "lanjutan topik yang diminta (agar tidak ada yang terlewat)", 4))
    inside.sort(key=lambda c: c.start)
    inside = inside[:TOPIC_MAX_PARTS]
    if len(inside) > 1:
        for i, c in enumerate(inside, 1):
            c.title = f"{c.title[:64]} (bagian {i}/{len(inside)})"
    return inside + others


def tidy(picks: list[_Pick], sentences: list[Sentence], n: int) -> list[Candidate]:
    """Rapikan usulan LLM: indeks valid, mulai di kalimat yang layak membuka, durasi 60–180 dtk, tanpa tumpang
    tindih (yang skornya lebih tinggi menang), maks n kandidat."""
    if not sentences:
        return []
    last_i = len(sentences) - 1
    out: list[Candidate] = []
    for p in sorted(picks, key=lambda p: -p.score):
        a, b = max(0, min(p.start, last_i)), max(0, min(p.end, last_i))
        if b < a:
            a, b = b, a
        a = _snap_start(sentences, a, b)
        while b < last_i and sentences[b].end - sentences[a].start < MIN_SEC:
            b += 1
        b = _snap_end(sentences, b)
        while b > a and sentences[b].end - sentences[a].start > MAX_SEC:
            b -= 1
            while b > a and not _ends_sentence(sentences[b]) and sentences[b].end - sentences[a].start > MIN_SEC:
                b -= 1
        dur = sentences[b].end - sentences[a].start
        if dur < MIN_SEC * 0.75:
            continue
        start, end = max(0.0, sentences[a].start - EDGE_PAD), sentences[b].end + EDGE_PAD
        if any(min(end, c.end) - max(start, c.start) > MAX_OVERLAP * min(end - start, c.duration) for c in out):
            continue
        out.append(_make(sentences, a, b, p.title, p.reason, p.score))
        if len(out) >= n:
            break
    for i, c in enumerate(out):
        c.rank = i + 1
    return out


MAX_ALL = 20            # "semua yang menarik": batas atas jumlah cuplikan (n=0)
MIN_SCORE_ALL = 3       # mode semua: usulan skor < 3 dibuang
EXCLUDE_OVERLAP = 0.5   # "Cari ulang": kandidat yang ≥ 50% sama dengan yang sudah ditampilkan dibuang


def target_all(duration: float) -> int:
    """Mode semua: target jumlah usulan ±1 per 4 menit video (5–20), agar model tidak berhenti di 5."""
    return max(5, min(MAX_ALL, round(duration / 240)))


def drop_seen(cands: list[Candidate], exclude: list[tuple[float, float, str]]) -> list[Candidate]:
    out = [c for c in cands if not any(min(c.end, b) - max(c.start, a) > EXCLUDE_OVERLAP * min(c.duration, b - a)
                                       for a, b, _ in exclude if b > a)]
    for i, c in enumerate(out):
        c.rank = i + 1
    return out


def find_highlights(video: Path, *, llm, model: str, fallback_model: str | None = None, brief: str = "",
                    n: int = 5, log=print, on_progress=None,
                    exclude: list[tuple[float, float, str]] | None = None) -> list[Candidate]:
    """exclude: cuplikan yang sudah ditampilkan ("Cari ulang") → AI diminta mengusulkan bagian lain.
    n=0: semua bagian yang layak jadi Reel (skor ≥ MIN_SCORE_ALL, maks MAX_ALL)."""
    all_mode = n <= 0
    n = MAX_ALL if all_mode else n
    """Transkrip video (cache) lalu minta LLM mengusulkan cuplikan. on_progress(frac, detail)."""
    import yaml

    from autoreels.analyze.transcribe import transcribe
    from autoreels.config import load_prompt

    def prog(frac: float, detail: str) -> None:
        if on_progress:
            on_progress(frac, detail)

    prog(0.0, "transkripsi video (sekali, lalu disimpan)")
    tr = transcribe(video, log=log, on_progress=lambda f: prog(0.9 * f, f"transkripsi {f:.0%}"))
    from autoreels.analyze.transcribe import AudioEnvelope, repair_squeezed

    try:
        words, n_fixed = repair_squeezed(tr.words, AudioEnvelope.from_file(video))
    except Exception:  # noqa: BLE001 — tanpa perbaikan tetap jalan
        words, n_fixed = tr.words, 0
    if n_fixed:
        log(f"  waktu {n_fixed} kata dari Whisper dimampatkan (bagian bermusik) → disebar ulang mengikuti suara")
    sentences = split_sentences(words)
    if not sentences:
        raise RuntimeError(f"Tidak ada ucapan yang terdeteksi di {video.name}.")
    prog(0.9, f"AI membaca {len(sentences)} kalimat dan memilih cuplikan")
    user = yaml.safe_dump({
        "instruksi": brief or "-", "jumlah_cuplikan": (f"semua yang layak, sekitar {target_all(tr.duration)}" if all_mode else n), "durasi_cuplikan_detik": [MIN_SEC, MAX_SEC],
        "durasi_video": _clock(tr.duration),
        **({"sudah_ditampilkan": [f"{_clock(a)}–{_clock(b)} {t}" for a, b, t in exclude]} if exclude else {}),
        "transkrip": transcript_lines(sentences),
    }, allow_unicode=True, sort_keys=False, width=10_000)
    messages = [{"role": "system", "content": load_prompt("highlight_find")}, {"role": "user", "content": user}]
    use = model
    if model.startswith("groq/") and len(user) / 3.5 > GROQ_SAFE_TOKENS:
        # batas token Groq gratis terlalu kecil → model cadangan pertama yang bukan Groq (sisa rantai tetap berlaku)
        alt = next((m for m in llm.fallback_chain(model) if not m.startswith("groq/")), None)
        if alt:
            log(f"  transkrip panjang (±{len(user) / 3.5 / 1000:.0f}K token) → {alt}")
            use = alt
    result = llm.complete_structured(messages, _Picks, model=use, purpose="highlight_find")
    log(f"  AI mengusulkan {len(result.candidates)} bagian")
    topic = result.topic if brief.strip() else None
    cands = tidy(result.candidates, sentences, TOPIC_MAX_PARTS if topic else n)
    if topic is not None:
        before = len(cands)
        cands = cover_topic(cands, topic, sentences)
        n_topic = sum(1 for c in cands if "(bagian " in c.title) or 1
        cands = cands[:max(n, n_topic)]
        if len(cands) > before:
            log(f"  topik \"{topic.title or brief}\" panjang → {len(cands) - before} bagian ditambah agar tidak terlewat")
        log(f"  topik yang diminta: S{topic.start}–S{topic.end} "
            f"({_clock(sentences[min(topic.end, len(sentences) - 1)].end - sentences[min(topic.start, len(sentences) - 1)].start)})")
    if all_mode:
        cands = [c for c in cands if c.score >= MIN_SCORE_ALL or "(bagian " in c.title]
    if exclude:
        before = len(cands)
        cands = drop_seen(cands, exclude)
        if len(cands) < before:
            log(f"  {before - len(cands)} usulan sama dengan yang sudah ditampilkan → dibuang")
    for i, c in enumerate(cands):
        c.rank = i + 1
    log(f"  {len(cands)} cuplikan ditemukan dari {_clock(tr.duration)} video")
    prog(1.0, f"{len(cands)} cuplikan ditemukan")
    return cands


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "cuplikan"


def cut_candidate(video: Path, cand: Candidate, out_dir: Path, *, reencode: bool = False) -> Path:
    """Potong cuplikan → out_dir/cuplikan-<judul>.mp4 (tidak menimpa). Bawaan: salin aliran (detik, tanpa encode);
    awal bisa maju ±1–2 dtk ke keyframe — tidak masalah karena alur video bicara mentranskrip & memilih ulang
    kalimatnya. reencode=True untuk potongan presisi frame."""
    from autoreels.media import run_ffmpeg

    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"cuplikan-{slugify(cand.title)}"
    out, k = out_dir / f"{base}.mp4", 2
    while out.exists():
        out, k = out_dir / f"{base}-{k}.mp4", k + 1
    codec = (["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "192k"] if reencode
             else ["-c", "copy", "-avoid_negative_ts", "make_zero"])
    run_ffmpeg(["-ss", f"{cand.start:.3f}", "-i", str(video), "-t", f"{cand.duration:.3f}", *codec,
                "-movflags", "+faststart", str(out)])
    return out


def save_candidates(path: Path, video: Path, cands: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"video": str(video), "candidates": [asdict(c) for c in cands]},
                               ensure_ascii=False, indent=1), encoding="utf-8")


def load_candidates(path: Path) -> tuple[Path, list[Candidate]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return Path(data["video"]), [Candidate(**c) for c in data["candidates"]]
