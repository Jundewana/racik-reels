"""Transkripsi per kata dengan faster-whisper (CPU, int8, bahasa id); tandai kata pengisi & jeda (Tahap 3).

Alur: transcribe() → Transcript (kata + waktu, di-cache per hash file & model) → keep_ranges() (rentang yang
dipertahankan: tanpa kata pengisi & jeda panjang, potongan di batas kata) → remap_words() (waktu kata di
timeline hasil potong, untuk subtitle karaoke).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from autoreels.config import PATHS, get_settings
from autoreels.media import file_hash

CACHE_DIR = PATHS["work"] / "_cache" / "transcripts"
TRANSCRIPT_VERSION = 2  # v2: prompt kosakata brand ikut menentukan cache

MAX_PAUSE = 0.6     # jeda lebih lama dari ini dipotong (CLAUDE.md: jeda > 0,6 dtk)
EDGE_PAD = 0.08     # sisakan sedikit napas di tepi tiap potongan agar suara tidak terpotong
FILLER_WORDS = {"anu", "eh", "ehm", "em", "emm", "hm", "hmm", "uh", "um", "umm", "eee", "ee", "ah"}
FILLER_RE = re.compile(r"^(e+|e+h+|e+m+|m+|h+m+|u+m+|u+h+|a+h+)$")
# Prompt awal: mendorong Whisper menulis kata pengisi apa adanya (default-nya sering dibuang)
VERBATIM_PROMPT = "Eee, jadi gini, emm, kita tuh, anu, ya. Hmm, oke."


def _norm(word: str) -> str:
    return re.sub(r"[^\w]", "", word.lower())


def vocab_prompt(max_chars: int = 600) -> str:
    """Prompt awal Whisper: gaya verbatim + kosakata brand (brand.yaml: transcribe_vocab, layanan rental,
    nama usaha; pillars.yaml: keyword). Membantu nama tempat/istilah yang sering salah dengar."""
    from autoreels.config import load_brand, load_pillars

    brand, terms = load_brand(), []
    terms += brand.get("transcribe_vocab") or []
    terms += [brand.get("short_name", ""), brand.get("company_name", "")]
    terms += brand.get("rental_services") or []
    for p in load_pillars().values():
        if isinstance(p, dict):
            terms += p.get("keywords") or []
    seen, uniq = set(), []
    for t in (str(x).strip() for x in terms):
        if t and t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    prompt = f"{VERBATIM_PROMPT} Kosakata: " + ", ".join(uniq)
    return prompt[:max_chars].rsplit(",", 1)[0] + "." if len(prompt) > max_chars else prompt + "."


def is_filler(word: str) -> bool:
    w = _norm(word)
    return bool(w) and (w in FILLER_WORDS or bool(FILLER_RE.match(w)))


@dataclass
class Word:
    start: float
    end: float
    text: str
    prob: float = 1.0
    filler: bool = False


@dataclass
class Transcript:
    path: str
    model: str
    language: str
    duration: float
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words).strip()

    def pauses(self, min_gap: float = MAX_PAUSE) -> list[tuple[float, float]]:
        """Jeda di antara kata (yang bukan pengisi) yang lebih panjang dari min_gap."""
        spoken = [w for w in self.words if not w.filler]
        return [(a.end, b.start) for a, b in zip(spoken, spoken[1:]) if b.start - a.end > min_gap]

    @property
    def fillers(self) -> list[Word]:
        return [w for w in self.words if w.filler]


def join_hyphen_tokens(words: list) -> list:
    """Whisper memecah kata ulang jadi dua token ("anak" + "-anak") → subtitle "anak -anak". Gabungkan token yang
    diawali "-" ke kata sebelumnya ("anak-anak"), waktu akhirnya diperpanjang."""
    out: list = []
    for w in words:
        t = w.text.strip()
        prev_t = out[-1].text.strip() if out else ""
        hyphen = len(t) > 1 and t.startswith("-") and (t[1].isalpha() or (t[1].isdigit() and prev_t[-1:].isdigit()))
        number = len(t) > 1 and t[0] in ".," and t[1].isdigit() and prev_t[-1:].isdigit()  # "545" + ".000," → "545.000,"
        if out and (hyphen or number) and not out[-1].filler:
            prev = out[-1]
            out[-1] = Word(prev.start, max(prev.end, w.end), prev.text.rstrip() + t, min(prev.prob, w.prob), False)
        else:
            out.append(w)
    return out


def _cache_file(path: Path, model_name: str | None = None) -> Path:
    import hashlib

    model_name = model_name or get_settings().transcribe_model
    phash = hashlib.sha1(vocab_prompt().encode("utf-8")).hexdigest()[:8]
    return CACHE_DIR / f"{file_hash(Path(path))}_{model_name}_{phash}_v{TRANSCRIPT_VERSION}.json"


def is_transcribed(path: str | Path, model_name: str | None = None) -> bool:
    """Transkrip video ini sudah ada di cache (tidak perlu CPU berat lagi)."""
    return _cache_file(Path(path), model_name).exists()


def transcribe(path: str | Path, model_name: str | None = None, language: str = "id", log=print,
               on_progress=None) -> Transcript:
    """Transkrip per kata (cache per hash file + model). Model diunduh sekali saat pertama dipakai.
    on_progress(frac 0–1): dipanggil tiap segmen selesai (video panjang butuh belasan menit di CPU)."""
    path = Path(path)
    model_name = model_name or get_settings().transcribe_model
    prompt = vocab_prompt()
    cache = _cache_file(path, model_name)
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        return Transcript(**{**data, "words": join_hyphen_tokens([Word(**w) for w in data["words"]])})

    from faster_whisper import WhisperModel  # impor lambat: berat

    from autoreels.analyze.audio import _decode

    log(f"  transkripsi {path.name} (faster-whisper '{model_name}', CPU) …")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    # dekode sendiri lewat ffmpeg (16 kHz mono): pembaca bawaan faster-whisper (PyAV) bentrok versi & tidak
    # menangani semua format; ffmpeg juga membaca audio dari file video
    audio = _decode(path, 16000)
    segments, info = model.transcribe(
        audio, language=language, word_timestamps=True, beam_size=5,
        initial_prompt=prompt, condition_on_previous_text=False, vad_filter=False,
    )
    words: list[Word] = []
    total = max(float(info.duration), 1.0)
    for seg in segments:
        if on_progress:
            on_progress(min(1.0, float(seg.end) / total))
        for w in seg.words or []:
            text = w.word.strip()
            if not text:
                continue
            words.append(Word(round(float(w.start), 3), round(float(w.end), 3), text,
                              round(float(w.probability), 3), is_filler(text)))
    tr = Transcript(str(path), model_name, info.language, round(float(info.duration), 3), join_hyphen_tokens(words))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({**asdict(tr)}, ensure_ascii=False, indent=1), encoding="utf-8")
    return tr


ENV_HOP = 0.02          # envelope audio: satu nilai RMS per 20 ms
VOICED_FRAC = 0.3       # jeda dianggap "ada suara" bila ≥ 30% framenya cukup keras
VOICED_REL = 0.25       # "cukup keras" = ≥ 25% level ucapan (median RMS saat kata diucapkan)


class AudioEnvelope:
    """RMS audio per 20 ms (dibaca bertahap lewat ffmpeg, hemat memori untuk video panjang). Dipakai agar jeda
    yang sebenarnya berisi suara tak tertranskrip ("yee", tawa, "hah?") tidak dibuang sebagai hening."""

    def __init__(self, rms: np.ndarray, hop: float = ENV_HOP) -> None:
        self.rms, self.hop = rms, hop

    @classmethod
    def from_file(cls, path: Path | str, sr: int = 8000) -> "AudioEnvelope":
        import subprocess

        from autoreels.media import ffmpeg_bin

        frame = int(sr * ENV_HOP)
        proc = subprocess.Popen([ffmpeg_bin(), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                                 "-f", "s16le", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        out, rest = [], b""
        while True:
            chunk = proc.stdout.read(frame * 2 * 500)
            if not chunk:
                break
            buf = rest + chunk
            n = len(buf) // (frame * 2) * frame * 2
            if n:
                x = np.frombuffer(buf[:n], dtype=np.int16).astype(np.float32).reshape(-1, frame) / 32768.0
                out.append(np.sqrt((x ** 2).mean(axis=1)))
            rest = buf[n:]
        proc.wait()
        return cls(np.concatenate(out) if out else np.zeros(0, dtype=np.float32))

    def _slice(self, a: float, b: float) -> np.ndarray:
        return self.rms[max(0, int(a / self.hop)):max(0, int(b / self.hop))]

    def speech_level(self, words: list[Word]) -> float:
        vals = [self._slice(w.start, w.end) for w in words if w.end > w.start]
        vals = [v for v in vals if v.size]
        return float(np.median(np.concatenate(vals))) if vals else 0.0

    def _floor(self, level: float) -> float:
        return max(VOICED_REL * level, 3 * float(np.percentile(self.rms, 10)) if self.rms.size else 0.0)

    def voiced_times(self, a: float, b: float, level: float) -> np.ndarray:
        """Waktu (dtk) frame bersuara di rentang a..b."""
        i0 = max(0, int(a / self.hop))
        seg = self.rms[i0:max(i0, int(b / self.hop))]
        return (np.nonzero(seg >= self._floor(level))[0] + i0) * self.hop

    def voiced(self, a: float, b: float, level: float) -> bool:
        """Ada suara berarti di rentang a..b (di luar 60 ms tepi, agar ekor kata tidak terhitung)?"""
        seg = self._slice(a + 0.06, b - 0.06)
        if seg.size == 0 or level <= 0:
            return False
        floor = max(VOICED_REL * level, 3 * float(np.percentile(self.rms, 10)) if self.rms.size else 0.0)
        return float((seg >= floor).mean()) >= VOICED_FRAC


SQUEEZE_GAP = 3.0        # jeda sebelum deretan kata yang dicurigai (dtk)
SQUEEZE_WORD_SEC = 0.2   # rata-rata < 0,2 dtk per kata = terlalu cepat untuk ucapan manusia
SQUEEZE_MIN_WORDS = 8


def repair_squeezed(words: list[Word], env: AudioEnvelope | None) -> tuple[list[Word], int]:
    """Whisper kadang salah menaruh waktu kata di bagian bermusik: ucapan ±20 dtk dimampatkan ke beberapa detik
    setelah "jeda" panjang yang sebenarnya berisi suara. Deretan seperti itu disebar ulang di sepanjang jeda +
    deretannya, mengikuti frame yang benar-benar bersuara (bobot = panjang kata). Kembalikan (kata, jumlah diperbaiki)."""
    if env is None or len(words) < SQUEEZE_MIN_WORDS:
        return words, 0
    words = sorted(words, key=lambda w: (w.start, w.end))
    level = env.speech_level(words)
    out, fixed, i = list(words), 0, 1
    while i < len(out):
        gap_start = out[i - 1].end
        if out[i].start - gap_start <= SQUEEZE_GAP:
            i += 1
            continue
        k = i
        while k + 1 < len(out) and (out[k + 1].end - out[i].start) / (k + 2 - i) < SQUEEZE_WORD_SEC:
            k += 1
        n = k + 1 - i
        if n < SQUEEZE_MIN_WORDS or not env.voiced(gap_start, out[i].start, level):
            i += 1
            continue
        a, b = gap_start + 0.05, out[k].end
        times = env.voiced_times(a, b, level)
        if times.size < n * 3:  # terlalu sedikit frame bersuara → sebar rata
            times = np.linspace(a, b, max(n * 5, 2))
        weights = np.array([len(w.text.strip()) + 1 for w in out[i:k + 1]], dtype=float)
        edges = np.concatenate([[0.0], np.cumsum(weights) / weights.sum()])
        pos = (edges * (times.size - 1)).round().astype(int)
        for j, w in enumerate(out[i:k + 1]):
            s = float(times[pos[j]])
            e = max(s + 0.08, float(times[pos[j + 1]]) - 0.02)
            out[i + j] = Word(round(s, 3), round(e, 3), w.text, w.prob, w.filler)
        fixed += n
        i = k + 1
    return out, fixed


def keep_ranges(tr: Transcript, max_pause: float = MAX_PAUSE, pad: float = EDGE_PAD,
                envelope: AudioEnvelope | None = None) -> list[tuple[float, float]]:
    """Rentang audio yang dipertahankan: kata pengisi dibuang, jeda > max_pause dipotong.
    Batas potongan selalu di batas kata (± pad), tidak pernah di tengah kata.
    envelope: bila ada, jeda yang ternyata berisi suara (seruan/tawa yang tidak ditulis Whisper) TIDAK dipotong."""
    spoken = [w for w in tr.words if not w.filler]
    if not spoken:
        return []
    level = envelope.speech_level(spoken) if envelope is not None else 0.0
    groups: list[list[Word]] = [[spoken[0]]]
    for prev, w in zip(spoken, spoken[1:]):
        filler_between = any(f.start >= prev.end - 0.01 and f.end <= w.start + 0.01 for f in tr.fillers)
        long_gap = w.start - prev.end > max_pause
        if long_gap and not filler_between and envelope is not None and envelope.voiced(prev.end, w.start, level):
            long_gap = False  # bukan hening: ada suara yang tak tertranskrip
        if long_gap or filler_between:
            groups.append([w])
        else:
            groups[-1].append(w)
    ranges = []
    for i, g in enumerate(groups):
        lo = g[0].start - pad
        hi = g[-1].end + pad
        if i > 0:  # jangan menabrak kata sebelumnya
            lo = max(lo, (groups[i - 1][-1].end + g[0].start) / 2)
        if i + 1 < len(groups):
            hi = min(hi, (g[-1].end + groups[i + 1][0].start) / 2)
        ranges.append((round(float(max(0.0, lo)), 3), round(float(min(tr.duration, hi)), 3)))
    return ranges


def remap_words(tr: Transcript, ranges: list[tuple[float, float]]) -> list[Word]:
    """Waktu kata (bukan pengisi) di timeline setelah rentang `ranges` disambung berurutan."""
    out, offset = [], 0.0
    # urut waktu: daftar kata bisa berisi kalimat cold open di depan (dipakai dua kali) — tanpa diurutkan, langkah
    # berikutnya yang mengira kata selalu urut memampatkan semua kata sesudahnya (subtitle kebut-kebutan)
    ordered = sorted(tr.words, key=lambda w: (w.start, w.end))
    for a, b in ranges:
        for w in ordered:
            if w.filler or w.start < a - 0.01 or w.end > b + 0.01:
                continue
            out.append(Word(round(w.start - a + offset, 3), round(w.end - a + offset, 3), w.text, w.prob))
        offset += b - a
    return out


def cleanup_stats(tr: Transcript, ranges: list[tuple[float, float]]) -> dict:
    kept = sum(b - a for a, b in ranges)
    return {
        "duration": tr.duration,
        "kept": round(kept, 2),
        "removed": round(tr.duration - kept, 2),
        "fillers": len(tr.fillers),
        "long_pauses": len(tr.pauses()),
        "words": len([w for w in tr.words if not w.filler]),
    }
