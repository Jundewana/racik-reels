"""Alur "narasi dulu": narasi (rekaman/unggahan) → transkrip → bersihkan → pecah per frasa.

Frasa adalah unit potong: segmen video ke-i menampilkan b-roll untuk frasa ke-i, durasinya sama dengan lama frasa
diucapkan. Batas frasa jatuh di tengah jeda antar kata, jadi potongan gambar tidak pernah di tengah kata.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from autoreels.edl import Narration, NarrationWord, Phrase

PHRASE_MIN = 1.0     # frasa lebih pendek digabung (potongan < 1 dtk terasa tergesa untuk b-roll bernarasi)
PHRASE_MAX = 3.5     # frasa lebih panjang dipecah di batas kata
HOOK_MAX = 2.8       # frasa pertama = hook, wajib ≤ 3 dtk (beri ruang kuantisasi frame)
CTA_MIN = 2.0        # frasa terakhir (CTA) digabung dengan sebelumnya bila terlalu pendek
BREAK_GAP = 0.25     # jeda antar kata lebih dari ini = calon batas frasa
PUNCT = (".", ",", "?", "!", ";", ":")


def _split_long(group: list, limit: float) -> list[list]:
    """Pecah kelompok kata yang lebih panjang dari `limit` di batas kata dengan jeda terbesar."""
    if len(group) < 2 or group[-1].end - group[0].start <= limit:
        return [group]
    best_i, best_score = None, -1.0
    for i in range(1, len(group)):
        left, right = group[i - 1].end - group[0].start, group[-1].end - group[i].start
        if left < PHRASE_MIN * 0.8 or right < PHRASE_MIN * 0.8:
            continue
        gap = group[i].start - group[i - 1].end
        punct = 0.3 if group[i - 1].text.rstrip().endswith(PUNCT) else 0.0
        balance = 1 - abs(left - right) / (left + right)
        score = gap * 4 + punct + balance * 0.5
        if left <= limit and score > best_score:
            best_i, best_score = i, score
    if best_i is None:  # tidak ada titik yang menjaga kedua sisi ≥ minimum: potong sedekat mungkin ke batas
        best_i = max(1, next((i for i in range(1, len(group)) if group[i].end - group[0].start > limit), len(group) - 1))
    return _split_long(group[:best_i], limit) + _split_long(group[best_i:], limit)


def build_phrases(words: list, total: float) -> list[Phrase]:
    """Kata (sudah di timeline narasi bersih) → frasa bersambung dari 0 sampai `total`."""
    if not words:
        return [Phrase(start=0.0, end=round(total, 3), text="")]
    groups: list[list] = [[words[0]]]
    for prev, w in zip(words, words[1:]):
        g = groups[-1]
        dur = prev.end - g[0].start
        natural = prev.text.rstrip().endswith(PUNCT) or w.start - prev.end > BREAK_GAP
        if (natural and dur >= PHRASE_MIN) or w.end - g[0].start > PHRASE_MAX:
            groups.append([w])
        else:
            g.append(w)
    # pecah yang terlalu panjang, lalu gabungkan yang terlalu pendek ke tetangga terdekat
    groups = [part for g in groups for part in _split_long(g, PHRASE_MAX)]
    merged: list[list] = []
    for g in groups:
        if merged and (g[-1].end - g[0].start < PHRASE_MIN or merged[-1][-1].end - merged[-1][0].start < PHRASE_MIN) \
                and g[-1].end - merged[-1][0].start <= PHRASE_MAX + 0.5:
            merged[-1] = merged[-1] + g
        else:
            merged.append(g)
    # hook ≤ HOOK_MAX
    if merged and merged[0][-1].end - merged[0][0].start > HOOK_MAX:
        merged = _split_long(merged[0], HOOK_MAX) + merged[1:]
    # CTA tidak terlalu pendek
    if len(merged) > 2 and total - merged[-1][0].start < CTA_MIN:
        merged = merged[:-2] + [merged[-2] + merged[-1]]

    phrases: list[Phrase] = []
    for i, g in enumerate(merged):
        start = 0.0 if i == 0 else phrases[-1].end
        end = total if i == len(merged) - 1 else (g[-1].end + merged[i + 1][0].start) / 2
        if i == 0:
            end = min(end, 3.0)
        phrases.append(Phrase(start=round(start, 3), end=round(max(end, start + 0.4), 3),
                              text=" ".join(w.text.strip() for w in g)))
    return phrases


def prepare_narration(source: str | Path, out_dir: Path, log=print) -> Narration:
    """Transkrip narasi, buang jeda & kata pengisi, simpan `narasi.wav` di out_dir, pecah per frasa."""
    from autoreels.analyze.transcribe import cleanup_stats, keep_ranges, remap_words, transcribe
    from autoreels.render.audio_mix import cut_audio

    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"File narasi tidak ditemukan: {source}")
    tr = transcribe(source, log=log)
    ranges = keep_ranges(tr)
    if not ranges:
        raise RuntimeError(f"Tidak ada ucapan yang terdeteksi di {source.name}.")
    st = cleanup_stats(tr, ranges)
    out_dir.mkdir(parents=True, exist_ok=True)
    cut_audio(source, ranges, out_dir / "narasi.wav")
    words = remap_words(tr, ranges)
    total = round(sum(b - a for a, b in ranges), 3)
    phrases = build_phrases(words, total)
    log(f"  narasi: {st['duration']:.1f} → {total:.1f} dtk (dibuang {st['fillers']} kata pengisi, "
        f"{st['long_pauses']} jeda panjang) · {len(words)} kata · {len(phrases)} frasa")
    return Narration(file="narasi.wav", source=str(source), duration=total,
                     words=[NarrationWord(start=w.start, end=w.end, text=w.text) for w in words],
                     phrases=phrases)


# ---------------------------------------------------------------- koreksi & pemeriksaan transkrip
TRANSCRIPT_FIX_PROMPT = "transcript_fix"
DRAFT_ROOT_NAME = "_narasi"  # work/_narasi/<draft_id>/ : narasi.wav + draft.json (transkrip yang diperiksa)


def phrase_words(narration: Narration) -> list[list[NarrationWord]]:
    """Kata-kata milik tiap frasa (berdasarkan titik tengah kata)."""
    out: list[list[NarrationWord]] = [[] for _ in narration.phrases]
    i = 0
    for w in narration.words:
        mid = (w.start + w.end) / 2
        while i < len(narration.phrases) - 1 and mid >= narration.phrases[i].end:
            i += 1
        out[i].append(w)
    return out


def apply_texts(narration: Narration, texts: list[str]) -> Narration:
    """Ganti teks tiap frasa (hasil koreksi AI / edit manusia) tanpa mengubah waktu audio.
    Jumlah kata sama → waktu tiap kata dipertahankan; berbeda → rentang ucapan frasa dibagi rata per panjang kata."""
    if len(texts) != len(narration.phrases):
        raise ValueError(f"jumlah teks {len(texts)} ≠ jumlah frasa {len(narration.phrases)}")
    groups = phrase_words(narration)
    new_words: list[NarrationWord] = []
    new_phrases: list[Phrase] = []
    for p, old, text in zip(narration.phrases, groups, texts):
        tokens = " ".join(str(text).split()).split(" ") if str(text).strip() else []
        if not tokens:  # frasa dikosongkan → tetap tampil teks lama (audio tidak berubah)
            tokens = [w.text.strip() for w in old] or [""]
        if old and len(tokens) == len(old):
            new_words += [NarrationWord(start=w.start, end=w.end, text=t) for w, t in zip(old, tokens)]
        else:
            lo = old[0].start if old else p.start
            hi = old[-1].end if old else p.end
            weights = [len(t) + 1 for t in tokens]
            span, t0 = max(hi - lo, 0.05 * len(tokens)), lo
            for tok, wgt in zip(tokens, weights):
                dur = span * wgt / sum(weights)
                new_words.append(NarrationWord(start=round(t0, 3), end=round(t0 + dur * 0.92, 3), text=tok))
                t0 += dur
        new_phrases.append(p.model_copy(update={"text": " ".join(tokens)}))
    return narration.model_copy(update={"words": new_words, "phrases": new_phrases})


class _FixOut(BaseModel):
    phrases: list[str]


def proofread(narration: Narration, llm, model: str, *, brief: str = "", log=print) -> tuple[Narration, list[dict]]:
    """Koreksi salah dengar (nama tempat, istilah) dengan LLM + kosakata brand. Gagal/tidak cocok → transkrip asli.
    Kembalikan (narasi terkoreksi, daftar koreksi {index, before, after})."""
    import yaml

    from autoreels.analyze.transcribe import vocab_prompt
    from autoreels.config import load_prompt

    before = [p.text for p in narration.phrases]
    vocab = vocab_prompt(max_chars=2000).split("Kosakata:", 1)[-1].strip().rstrip(".")
    user = yaml.safe_dump({"kosakata_brand": vocab, "konteks_video": brief or "-",
                           "frasa": [f"P{i + 1}: {t}" for i, t in enumerate(before)]},
                          allow_unicode=True, sort_keys=False, width=200)
    messages = [{"role": "system", "content": load_prompt(TRANSCRIPT_FIX_PROMPT)}, {"role": "user", "content": user}]
    try:
        out = llm.complete_structured(messages, _FixOut, model=model, purpose="transcript_fix")
    except Exception as e:  # noqa: BLE001 — koreksi bersifat bantuan; transkrip asli tetap dipakai
        log(f"  [peringatan] koreksi transkrip gagal: {e}")
        return narration, []
    after = [re.sub(r"^P\d+\s*:\s*", "", t).strip() for t in out.phrases]
    if len(after) != len(before):
        log(f"  [peringatan] koreksi transkrip diabaikan: {len(after)} frasa ≠ {len(before)}")
        return narration, []
    # tulis ulang (tidak mirip) → tolak utuh; sisanya dijaga agar hanya membetulkan salah dengar
    after = [guard_spoken(a, b) if b and _similar_enough(a, b) else a for a, b in zip(before, after)]
    fixes = []
    for i, (a, b) in enumerate(zip(before, after)):
        if b and b != a:
            fixes.append({"index": i, "before": a, "after": b})
        else:
            after[i] = a
    if fixes:
        log(f"  koreksi transkrip: {len(fixes)} frasa diperbaiki")
        for f in fixes:
            log(f"    P{f['index'] + 1}: {f['before']}  →  {f['after']}")
    return apply_texts(narration, after), fixes


def _norm_token(t: str) -> str:
    return re.sub(r"[^\w]", "", t.lower())


def guard_spoken(before: str, after: str) -> str:
    """Pertahankan hanya koreksi salah dengar: kata yang DISISIPKAN LLM (tidak diucapkan) dibuang, kata yang
    dihapus dikembalikan, dan satu kata → beberapa kata hanya bila bunyinya mirip ("jasujan" → "jas hujan").
    Perbaikan huruf besar/tanda baca dipertahankan."""
    from difflib import SequenceMatcher

    a_tok, b_tok = before.split(), after.split()
    sm = SequenceMatcher(None, [_norm_token(t) for t in a_tok], [_norm_token(t) for t in b_tok], autojunk=False)
    out: list[str] = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            out += b_tok[j1:j2]
        elif op == "delete":
            out += a_tok[i1:i2]
        elif op == "replace":
            a_part, b_part = a_tok[i1:i2], b_tok[j1:j2]
            sound = SequenceMatcher(None, "".join(_norm_token(t) for t in a_part),
                                    "".join(_norm_token(t) for t in b_part)).ratio()
            if len(a_part) == len(b_part):
                # kata per kata; tolak yang memangkas kata benar ("persenyawaan" → "senyawa": imbuhan dibuang)
                out += [a if _trimmed_word(a, b) else b for a, b in zip(a_part, b_part)]
            elif (len(b_part) > len(a_part) and sound >= 0.6) or (len(b_part) < len(a_part) and sound >= 0.75):
                out += b_part  # pecah ("jasujan" → "jas hujan") atau gabung yang mirip bunyi
            else:
                out += _align_tokens(a_part, b_part)
        # "insert": kata tambahan yang tidak diucapkan → dibuang
    return " ".join(out)


def _trimmed_word(a: str, b: str) -> bool:
    """Koreksi yang hanya memotong kata asli (kata baru = bagian kata lama, ≥ 35% lebih pendek) bukan salah dengar,
    melainkan mengubah kata yang diucapkan — mis. "persenyawaan" → "senyawa"."""
    na, nb = _norm_token(a), _norm_token(b)
    return bool(nb) and nb != na and nb in na and len(nb) <= len(na) * 0.65


def _align_tokens(a_part: list[str], b_part: list[str]) -> list[str]:
    """Pasangkan kata asli dengan kata koreksi yang bunyinya mirip (urut); kata asli tanpa pasangan dipertahankan."""
    from difflib import SequenceMatcher

    out, k = [], 0
    for a in a_part:
        match = next((j for j in range(k, len(b_part))
                      if SequenceMatcher(None, _norm_token(a), _norm_token(b_part[j])).ratio() >= 0.5), None)
        if match is None:
            out.append(a)
        else:
            out.append(b_part[match])
            k = match + 1
    return out


def _similar_enough(a: str, b: str) -> bool:
    """Tolak 'koreksi' yang menulis ulang kalimat (bukan sekadar membetulkan salah dengar)."""
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.6


# ---- draf transkrip (web: transkrip → periksa/edit → buat video) ----
def _draft_dir(draft_id: str) -> Path:
    from autoreels.config import PATHS

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,80}", draft_id):
        raise ValueError("ID draf transkrip tidak valid")
    return PATHS["work"] / DRAFT_ROOT_NAME / draft_id


def create_draft(source: Path, *, llm=None, model: str | None = None, brief: str = "", log=print) -> dict:
    """Transkrip + bersihkan + koreksi AI → simpan draf (narasi.wav + draft.json). Kembalikan isi draf."""
    from datetime import datetime

    slug = re.sub(r"[^a-z0-9]+", "-", source.stem.lower()).strip("-")[:40] or "narasi"
    draft_id = f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    d = _draft_dir(draft_id)
    narration = prepare_narration(source, d, log=log)
    if narration.duration > 90:  # cek di awal, bukan di tengah job
        raise RuntimeError(f"Narasi {narration.duration:.0f} dtk setelah jeda dibuang, maksimal 90 dtk untuk Reels. "
                           "Persingkat rekamannya.")
    original = [p.text for p in narration.phrases]
    fixes: list[dict] = []
    if llm is not None and model:
        narration, fixes = proofread(narration, llm, model, brief=brief, log=log)
    draft = {"id": draft_id, "source": str(source), "original": original, "ai_fixes": fixes, "reviewed": False,
             "narration": narration.model_dump()}
    _save_draft(d, draft)
    return draft


def create_talk_draft(source: Path, *, speaker_clip: str, llm, model: str, brief: str = "", target: float = 40.0,
                      full: bool = False, log=print) -> dict:
    """Video bicara: transkrip → pilih kalimat (ringkas/utuh) → koreksi AI → draf untuk diperiksa manusia.
    Audio draf (narasi.wav) = ucapan terpilih, jadi tiap frasa bisa diputar saat memeriksa."""
    from datetime import datetime

    from autoreels.talk import prepare_talk

    slug = re.sub(r"[^a-z0-9]+", "-", source.stem.lower()).strip("-")[:40] or "bicara"
    draft_id = f"{datetime.now():%Y%m%d-%H%M%S}-{slug}"
    d = _draft_dir(draft_id)
    narration = prepare_talk(source, d, speaker_clip=speaker_clip, llm=llm, model=model, brief=brief, target=target,
                             full=full, log=log)
    original = [p.text for p in narration.phrases]
    narration, fixes = proofread(narration, llm, model, brief=brief, log=log)
    draft = {"id": draft_id, "kind": "bicara", "source": str(source), "speaker_clip": speaker_clip,
             "talk_full": full, "original": original, "ai_fixes": fixes, "reviewed": False,
             "narration": narration.model_dump()}
    _save_draft(d, draft)
    return draft


def _save_draft(d: Path, draft: dict) -> None:
    import json

    (d / "draft.json").write_text(json.dumps(draft, ensure_ascii=False, indent=1), encoding="utf-8")


def load_draft(draft_id: str) -> dict:
    import json

    f = _draft_dir(draft_id) / "draft.json"
    if not f.exists():
        raise FileNotFoundError(f"Draf transkrip {draft_id} tidak ditemukan (buat ulang transkripnya).")
    return json.loads(f.read_text(encoding="utf-8"))


def update_draft(draft_id: str, texts: list[str]) -> dict:
    """Simpan teks per frasa hasil periksa manusia (waktu audio tetap)."""
    draft = load_draft(draft_id)
    narration = apply_texts(Narration(**draft["narration"]), [str(t) for t in texts])
    draft.update(narration=narration.model_dump(), reviewed=True)
    _save_draft(_draft_dir(draft_id), draft)
    return draft


def use_draft(draft_id: str, out_dir: Path) -> tuple[Narration, str]:
    """Narasi dari draf yang sudah diperiksa: salin narasi.wav ke folder job. Kembalikan (narasi, file sumber)."""
    import shutil

    draft = load_draft(draft_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_draft_dir(draft_id) / "narasi.wav", out_dir / "narasi.wav")
    return Narration(**draft["narration"]), draft["source"]
