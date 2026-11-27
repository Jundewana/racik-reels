"""Tahap 3 — video bicara: video pembicara (1–3 menit) → Reel 30–45 dtk bersubtitle, dengan sisipan b-roll.

Memakai mesin alur "narasi dulu": suara pembicara (kalimat terpilih, tanpa jeda/kata pengisi/take ulang) menjadi
narasi; tiap frasa tahu posisinya di video asli (`Phrase.src_start`) sehingga segmen wajah pembicara selalu sinkron
bibir, dan frasa lain boleh ditutup b-roll.

Langkah: transkrip → kalimat → buang take ulang (versi terakhir yang utuh menang) → LLM memilih kalimat isi
(urutan asli; mode utuh: semua) → cold open: LLM memilih klausa 1,5–5 dtk paling menohok dari isi, diputar di depan
sebagai teaser lalu terdengar lagi di tempat aslinya → potong audio → frasa per rentang (tak melintasi titik potong).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from autoreels.edl import Narration, NarrationWord, Phrase

SENTENCE_END = (".", "?", "!")
SENTENCE_PAUSE = 0.6      # jeda lebih dari ini juga mengakhiri kalimat (Whisper kadang tanpa tanda baca)
SENTENCE_MAX = 12.0       # kalimat lebih panjang dipecah di jeda terbesar
RETAKE_PREFIX = 3         # kalimat diulang bila ≥ 3 kata awalnya sama dengan kalimat berikutnya
TARGET_MIN, TARGET_MAX = 30.0, 45.0   # Tahap 3: Reel 30–45 dtk
FULL_MAX_SEC = 180.0                   # mode utuh: batas panjang Reels Instagram (3 menit)
COLD_MIN, COLD_MAX = 1.5, 5.0          # cold open (teaser di depan): klausa 1,5–5 dtk
CLAUSE_GAP = 0.3                       # jeda antarkata ≥ ini (atau koma) = batas klausa
COLD_GAP_SEC = 8.0                     # teaser tidak diambil dari 8 dtk pertama isi (akan terdengar dua kali beruntun)


@dataclass
class Sentence:
    index: int
    words: list  # analyze.transcribe.Word (waktu di video asli)

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def text(self) -> str:
        return " ".join(w.text.strip() for w in self.words)


def _norm(t: str) -> str:
    return re.sub(r"[^\w]", "", t.lower())


def split_sentences(words: list) -> list[Sentence]:
    """Kata (tanpa pengisi) → kalimat: akhir di tanda baca atau jeda > SENTENCE_PAUSE; yang terlalu panjang dipecah."""
    spoken = [w for w in words if not getattr(w, "filler", False)]
    groups: list[list] = []
    for w in spoken:
        if groups and not (groups[-1][-1].text.rstrip().endswith(SENTENCE_END)
                           or w.start - groups[-1][-1].end > SENTENCE_PAUSE):
            groups[-1].append(w)
        else:
            groups.append([w])
    out: list[list] = []
    for g in groups:
        stack = [g]
        while stack:
            cur = stack.pop(0)
            if cur[-1].end - cur[0].start <= SENTENCE_MAX or len(cur) < 4:
                out.append(cur)
                continue
            gaps = [(cur[i].start - cur[i - 1].end + (0.2 if cur[i - 1].text.rstrip().endswith(",") else 0), i)
                    for i in range(2, len(cur) - 1)]
            _, cut = max(gaps)
            stack[:0] = [cur[:cut], cur[cut:]]
    return [Sentence(i, g) for i, g in enumerate(out)]


def drop_retakes(sentences: list[Sentence]) -> tuple[list[Sentence], list[Sentence]]:
    """Take ulang: kalimat yang awalnya diulang oleh kalimat berikutnya (≥ 3 kata sama) atau terpotong (kalimat
    berikutnya diawali seluruh isinya) dibuang — versi terakhir yang utuh menang. Kembalikan (dipakai, dibuang)."""
    keep, dropped = [], []
    for i, s in enumerate(sentences):
        nxt = sentences[i + 1] if i + 1 < len(sentences) else None
        if nxt is not None:
            a = [_norm(w.text) for w in s.words]
            b = [_norm(w.text) for w in nxt.words]
            n = min(len(a), len(b), RETAKE_PREFIX)
            same_start = n >= RETAKE_PREFIX and a[:n] == b[:n]
            cut_off = 1 <= len(a) < len(b) and b[:len(a)] == a
            if same_start or cut_off:
                dropped.append(s)
                continue
        keep.append(s)
    return keep, dropped


WEAK_STARTS = {"dan", "jadi", "nah", "itu", "tapi", "tetapi", "karena", "kalau", "lalu", "terus", "sehingga",
               "makanya", "ya", "baik", "oke", "nanti", "tadi", "yang", "ini", "itulah", "inilah", "begitu",
               "begitulah", "maka", "kemudian", "nah", "jadinya", "seperti", "contohnya", "misalnya",
               "bahwa", "sebagai", "dengan", "untuk", "atau", "serta", "udah", "sudah", "emang", "memang",
               "iya", "sih", "gitu", "kayak", "terus"}
HOOK_MAX_SEC = 6.0


def weak_hook(s: Sentence) -> str | None:
    """Alasan kalimat tidak layak jadi hook (diawali kata sambung/rujukan, atau terlalu panjang), atau None."""
    first = _norm(s.words[0].text)
    if first in WEAK_STARTS:
        return f"diawali kata \"{s.words[0].text.strip(',.')}\" (butuh konteks sebelumnya)"
    if s.duration > HOOK_MAX_SEC:
        return f"terlalu panjang ({s.duration:.1f} dtk, maks {HOOK_MAX_SEC:.0f})"
    return None


class _Selection(BaseModel):
    sentences: list[int] = Field(..., min_length=1)
    reason: str = ""


def select_sentences(sentences: list[Sentence], llm, model: str, *, brief: str, target: float,
                     reserve: float = 0.0, log=print) -> list[Sentence]:
    """LLM memilih kalimat isi untuk ±(target − reserve) dtk, dikembalikan dalam urutan asli agar alurnya nyambung.
    reserve = jatah dtk untuk cold open di depan. Gagal → kalimat awal berurutan."""
    import yaml

    from autoreels.config import load_prompt

    by_id = {s.index: s for s in sentences}
    target = min(max(target, TARGET_MIN), TARGET_MAX)
    limit = min(TARGET_MAX, target * 1.1) - reserve
    goal = target - reserve
    user = yaml.safe_dump({
        "instruksi": brief or "-", "target_durasi_detik": round(goal),
        "rentang_durasi_detik": [round(TARGET_MIN - reserve), round(limit, 1)],
        "kalimat": [f"S{s.index} | {s.duration:.1f} dtk | {s.text}" for s in sentences],
    }, allow_unicode=True, sort_keys=False, width=200)
    messages = [{"role": "system", "content": load_prompt("talk_select")}, {"role": "user", "content": user}]
    chosen: list[Sentence] = []
    try:
        out = llm.complete_structured(messages, _Selection, model=model, purpose="talk_select")
        chosen = sorted({i: by_id[i] for i in out.sentences if i in by_id}.values(), key=lambda x: x.index)
        if out.reason:
            log(f"  pilihan kalimat: {out.reason}")
    except Exception as e:  # noqa: BLE001 — pemilihan bersifat bantuan; cadangan deterministik di bawah
        log(f"  [peringatan] pemilihan kalimat oleh AI gagal: {e}")
    total = sum(s.duration for s in chosen)
    if not chosen or total < (TARGET_MIN - reserve) * 0.8:
        log("  [cadangan] memakai kalimat awal berurutan sampai durasi target")
        chosen, total = [], 0.0
        for s in sentences:
            if total + s.duration > limit:
                break
            chosen.append(s)
            total += s.duration
    while len(chosen) > 2 and sum(s.duration for s in chosen) > limit:
        chosen.pop(-2)  # kelebihan → buang kalimat isi terakhir; pembuka & penutup tetap
    return chosen


def hook_candidates(sentences: list[Sentence]) -> list[Sentence]:
    """Kandidat cold open: gabungan 1–3 klausa berurutan (dipecah di koma/titik koma/titik dua/jeda) berdurasi
    1,5–5 dtk, minimal 3 kata, tidak diawali kata sambung/rujukan. `index` = kalimat asalnya."""
    out: list[Sentence] = []
    seen: set[tuple[float, float]] = set()
    for s in sentences:
        clauses: list[list] = [[]]
        for k, w in enumerate(s.words):
            clauses[-1].append(w)
            nxt = s.words[k + 1] if k + 1 < len(s.words) else None
            if nxt is not None and (w.text.rstrip().endswith((",", ";", ":")) or nxt.start - w.end >= CLAUSE_GAP):
                clauses.append([])
        for a in range(len(clauses)):
            for b in range(a, min(a + 3, len(clauses))):
                words = [w for c in clauses[a:b + 1] for w in c]
                span = Sentence(index=s.index, words=words)
                if not (COLD_MIN <= span.duration <= COLD_MAX) or len(words) < 3:
                    continue
                if _norm(words[0].text) in WEAK_STARTS or (span.start, span.end) in seen:
                    continue
                seen.add((span.start, span.end))
                out.append(span)
    return out


class _ColdOpen(BaseModel):
    candidate: int  # nomor K; -1 = tidak ada yang layak
    reason: str = ""


def by_index(sentences: list[Sentence], index: int) -> Sentence:
    return next(s for s in sentences if s.index == index)


def pick_cold_open(body: list[Sentence], llm, model: str, *, brief: str, pool: list[Sentence] | None = None,
                   log=print) -> Sentence | None:
    """LLM memilih klausa paling menohok untuk diputar di depan. Kandidat dari isi (kecuali 8 dtk pertamanya)
    dan dari `pool` (kalimat lain yang tidak masuk isi → jadi hook pembuka saja). None bila tidak ada yang layak."""
    import yaml

    from autoreels.config import load_prompt

    offsets, t = {}, 0.0  # posisi tiap kalimat di Reel (perkiraan, sebelum jeda dibuang)
    for s in body:
        offsets[s.index] = t
        t += s.duration
    cands = [c for c in hook_candidates(body)
             if offsets[c.index] + (c.start - by_index(body, c.index).start) >= COLD_GAP_SEC]
    cands += hook_candidates([s for s in pool or [] if s.index not in offsets])
    if not cands:
        log("  cold open: tidak ada klausa 1,5–5 dtk yang berdiri sendiri, dilewati")
        return None
    user = yaml.safe_dump({
        "instruksi": brief or "-",
        "kandidat": [f"K{i} | {c.duration:.1f} dtk | {c.text.rstrip(',;:')}" for i, c in enumerate(cands)],
    }, allow_unicode=True, sort_keys=False, width=200)
    try:
        out = llm.complete_structured([{"role": "system", "content": load_prompt("talk_hook")},
                                       {"role": "user", "content": user}], _ColdOpen, model=model,
                                      purpose="talk_cold_open")
    except Exception as e:  # noqa: BLE001 — cold open hanya penguat; tanpa itu Reel tetap utuh
        log(f"  [peringatan] cold open dilewati: {e}")
        return None
    if not 0 <= out.candidate < len(cands):
        log("  cold open: AI menilai tidak ada klausa yang cukup kuat, dilewati")
        return None
    pick = cands[out.candidate]
    log(f"  cold open ({pick.duration:.1f} dtk): \"{pick.text.rstrip(',;:')}\" — {out.reason}")
    return pick


def _phrases_in_ranges(words_tl: list, ranges: list[tuple[float, float]]) -> list[Phrase]:
    """Frasa per rentang potong (tidak pernah melintasi titik potong) + src_start untuk sinkron bibir."""
    from autoreels.narration import build_phrases

    phrases: list[Phrase] = []
    offset = 0.0
    for a, b in ranges:
        length = b - a
        local = [NarrationWord(start=round(w.start - offset, 3), end=round(w.end - offset, 3), text=w.text)
                 for w in words_tl if offset - 0.01 <= w.start < offset + length - 0.01]
        for p in build_phrases(local, round(length, 3)):
            phrases.append(Phrase(start=round(p.start + offset, 3), end=round(p.end + offset, 3), text=p.text,
                                  src_start=round(a + p.start, 3)))
        offset += length
    return phrases


def prepare_talk(source: Path, out_dir: Path, *, speaker_clip: str, llm, model: str, brief: str = "",
                 target: float = 40.0, full: bool = False, cold_open: bool = True, log=print) -> Narration:
    """Video pembicara → Narration (narasi.wav = ucapan terpilih & bersih; frasa dengan src_start)."""
    from autoreels.analyze.transcribe import (AudioEnvelope, Transcript, keep_ranges, remap_words,
                                              repair_squeezed, transcribe)
    from autoreels.render.audio_mix import cut_audio

    tr = transcribe(source, log=log)
    try:
        env = AudioEnvelope.from_file(source)
    except Exception as e:  # noqa: BLE001 — tanpa envelope tetap jalan (semua jeda panjang dipotong)
        log(f"  [peringatan] envelope audio gagal dibaca ({e}); jeda dipotong tanpa cek suara")
        env = None
    words, n_fixed = repair_squeezed(tr.words, env)
    if n_fixed:
        log(f"  waktu {n_fixed} kata dari Whisper dimampatkan (bagian bermusik) → disebar ulang mengikuti suara")
        tr = Transcript(path=tr.path, model=tr.model, language=tr.language, duration=tr.duration, words=words)
    sentences = split_sentences(tr.words)
    if not sentences:
        raise RuntimeError(f"Tidak ada ucapan yang terdeteksi di {source.name}.")
    kept, dropped = drop_retakes(sentences)
    log(f"  video bicara: {tr.duration:.0f} dtk · {len(sentences)} kalimat · {len(dropped)} take ulang dibuang")
    for s in dropped:
        log(f"    take ulang: {s.text[:70]}")
    if full:  # utuh: seluruh isi video (jeda, kata pengisi & take ulang tetap dibuang), urutan asli
        chosen = kept
        total_est = sum(s.duration for s in chosen)
        if total_est > FULL_MAX_SEC:
            raise RuntimeError(f"Isi ucapan ±{total_est:.0f} dtk melebihi {FULL_MAX_SEC:.0f} dtk (batas Reels). "
                               "Pilih durasi 'Ringkas' atau potong videonya lebih pendek.")
        log(f"  mode utuh: {len(chosen)} kalimat, ±{total_est:.0f} dtk (tanpa diringkas AI)")
    else:
        chosen = select_sentences(kept, llm, model, brief=brief, target=target,
                                  reserve=COLD_MAX if cold_open else 0.0, log=log)
    teaser = pick_cold_open(chosen, llm, model, brief=brief, pool=kept, log=log) if cold_open else None
    if teaser is not None and abs(teaser.start - chosen[0].start) < 0.05:
        teaser = None  # Reel memang sudah dibuka dengan klausa itu
    if teaser is not None and full and sum(s.duration for s in chosen) + teaser.duration > FULL_MAX_SEC:
        log("  cold open dilewati: Reel akan melebihi 3 menit")
        teaser = None
    sequence = ([teaser] if teaser is not None else []) + chosen
    n_teaser_ranges = 0
    ranges: list[tuple[float, float]] = []
    # kalimat yang bersebelahan di video asli digabung, agar suara di antaranya yang tak tertranskrip
    # ("yee", tawa, sahutan) tidak ikut terbuang — hanya jeda yang benar-benar hening yang dipotong
    blocks: list[list[Sentence]] = []
    for s in sequence:
        if blocks and blocks[-1][-1] is not teaser and s is not teaser and s.index == blocks[-1][-1].index + 1:
            blocks[-1].append(s)
        else:
            blocks.append([s])
    for blk in blocks:  # urutan tampil: cold open, lalu isi urutan asli; jeda hening & kata pengisi dibuang
        a, b = blk[0].start, blk[-1].end
        sub = Transcript(path=tr.path, model=tr.model, language=tr.language, duration=tr.duration,
                         words=[w for w in tr.words if a - 0.01 <= w.start and w.end <= b + 0.01])
        ranges += keep_ranges(sub, envelope=env)
        if blk[0] is teaser:
            n_teaser_ranges = len(ranges)
    out_dir.mkdir(parents=True, exist_ok=True)
    cut_audio(source, ranges, out_dir / "narasi.wav")
    sel = Transcript(path=tr.path, model=tr.model, language=tr.language, duration=tr.duration,
                     words=list({id(w): w for s in sequence for w in s.words}.values()))
    words_tl = remap_words(sel, ranges)
    total = round(sum(b - a for a, b in ranges), 3)
    phrases = _phrases_in_ranges(words_tl, ranges)
    log(f"  dipilih {len(chosen)} kalimat → {total:.1f} dtk · {len(phrases)} frasa · pembuka: \"{sequence[0].text[:60]}\"")
    return Narration(file="narasi.wav", source=str(source), duration=total, speaker_clip=speaker_clip,
                     words=[NarrationWord(start=w.start, end=w.end, text=w.text) for w in words_tl],
                     phrases=phrases, cold_open_sec=round(sum(b - a for a, b in ranges[:n_teaser_ranges]), 3))


# --- Sisipan b-roll: frasa yang menyebut sesuatu yang ada di adegan lain (mis. "motor" ↔ adegan motor) -------------
_STOP = set("""yang untuk dengan sangat kalau karena juga saja sudah bisa akan atau tidak nggak enggak kita kami
kalian saya mereka adalah dari pada dalam lebih seperti sama banyak semua harus punya buat jadi lagi masih emang
memang gitu begitu kayak banget tapi terus udah pakai pake hari waktu orang yaitu ini itu ada mau gue lo lu aja
nih deh dong kan cuma bikin tahu tau lihat liat sini situ sana mana apa siapa kapan gimana bagaimana kenapa
mengapa boleh baru bagus besar kecil tanpa antara sampai setelah sebelum pernah selalu sering kadang""".split())
BROLL_MIN_SEC = 0.8   # frasa lebih pendek dari ini tidak disarankan b-roll (kedipan gambar mengganggu)


def _keys(text: str) -> set[str]:
    """Kata kunci kasar: kata ≥ 4 huruf, bukan kata umum, dipotong 5 huruf (motornya → motor, proyeknya → proye)."""
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4 and w not in _STOP}


def broll_suggestions(phrases, scenes, descriptions: dict, speaker_clip: str, *, cold_open_sec: float = 0.0,
                      limit: int = 15) -> list[str]:
    """Saran b-roll per frasa untuk Director: 'P5 → K2-3, K2-1 (cocok: motor)'. Frasa hook/cold open/terakhir &
    frasa yang terlalu pendek dilewati (wajib pembicara). Kosong bila tidak ada adegan lain yang cocok."""
    pool = []
    for sc in scenes:
        d = descriptions.get(sc.scene_id)
        if sc.source_file == speaker_clip or d is None:
            continue
        keys = _keys(" ".join(x for x in [d.subject, d.action, d.setting, d.suggested_text or ""] if x))
        if keys:
            pool.append((sc.scene_id, keys, sc.duration))
    out = []
    for i, p in enumerate(phrases):
        if i == 0 or i == len(phrases) - 1 or p.start < cold_open_sec - 0.01 or p.duration < BROLL_MIN_SEC:
            continue
        words = _keys(p.text)
        ranked = sorted(((len(words & k), sid, k) for sid, k, dur in pool if dur >= p.duration and words & k),
                        key=lambda x: -x[0])
        if ranked:
            hit = sorted(words & ranked[0][2])
            out.append(f"P{i + 1} → {', '.join(sid for _, sid, _ in ranked[:2])} (cocok: {', '.join(hit)})")
    return out[:limit]
