"""Musik orisinal untuk Racik Animasi: Claude Code menulis PARTITUR (musik.json), modul ini menyintesisnya (numpy).

Tanpa sampel & tanpa model: semua bunyi dibangkitkan matematis (osilator, derau, amplop), jadi bebas hak cipta.
Gaya: jingle/kartun ceria — pad akor, bass, drum, arpeggio, melodi marimba — dengan energi per bagian.

Partitur (work/_animasi/<nama>/musik.json), contoh:
{
  "bpm": 112, "kunci": "D", "skala": "mayor",          # skala: mayor | minor
  "progresi": ["I", "V", "vi", "IV"],                  # satu akor per birama, diulang
  "bagian": [                                          # energi 1 (tenang) – 3 (penuh), berlaku sampai bagian berikut
    {"mulai": 0.0, "energi": 2},
    {"mulai": 9.5, "energi": 1, "tanpa": ["drum"]},
    {"mulai": 33.0, "energi": 3}
  ],
  "aksen": [4.0, 22.8],                                # hentakan (crash + kick) di detik ini
  "sfx": [{"t": 2.1, "jenis": "whoosh"}, {"t": 29.7, "jenis": "ding"}],   # whoosh|thump|pop|ding|klik|naik
  "seed": 3
}
Instrumen yang bisa dimatikan per bagian lewat "tanpa": pad, bass, drum, arp, melodi.
Keluaran: musik.wav (tanpa sfx) & sfx.wav terpisah — musik diturunkan (ducking) di bawah narasi, sfx tidak.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from autoreels.render.sfx import SR, _pop, _thump, _whoosh, _write

NOTE = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8,
        "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}
SCALE = {"mayor": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}
ROMAN = {"i": 0, "ii": 1, "iii": 2, "iv": 3, "v": 4, "vi": 5, "vii": 6}
INSTRUMENTS = ("pad", "bass", "drum", "arp", "melodi")
SFX_KINDS = ("whoosh", "thump", "pop", "ding", "klik", "naik")


def _hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def chord_notes(symbol: str, key: str, scale: str) -> list[int]:
    """'vi' → nada MIDI triad (oktaf 4) di kunci & skala. Huruf besar/kecil tidak mengubah kualitas (ikut skala)."""
    root_pc = NOTE[key.upper()]
    steps = SCALE[scale]
    deg = ROMAN[symbol.strip().lower().rstrip("7")]
    notes = []
    for k in (0, 2, 4):
        d = deg + k
        notes.append(60 + root_pc + steps[d % 7] + 12 * (d // 7))
    return notes


# ------------------------------------------------------------------ instrumen (mono, panjang n sampel)
def _env(n: int, a: float, d: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.clip(t / max(a, 1e-4), 0, 1) * np.exp(-t / max(d, 1e-4))


def _pad(freqs: list[float], dur: float) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.12):  # dua osilator sedikit sumbang → lebar
            ph = 2 * np.pi * f * (1 + det / 100) * t
            out += (2 / np.pi) * np.arcsin(np.sin(ph))  # segitiga: lembut
    env = np.clip(t / 0.25, 0, 1) * np.clip((dur - t) / 0.3, 0, 1)
    return out * env / (len(freqs) * 2)


def _bass(f: float, dur: float) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sign(np.sin(2 * np.pi * f * t)) * 0.5
    return tone * np.clip(t / 0.005, 0, 1) * np.exp(-t / 0.35) * np.clip((dur - t) / 0.02, 0, 1)


def _marimba(f: float, dur: float = 0.6) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.04)
    return tone * _env(n, 0.002, 0.22)


def _pluck(f: float, dur: float = 0.25) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(2 * np.pi * f * 2 * t) * 0.3
    return sq * _env(n, 0.002, 0.07)


def _kick() -> np.ndarray:
    return _thump(0.3)[:, 0]


def _snare(rng: np.random.Generator) -> np.ndarray:
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.concatenate([[0], noise[:-1]]) * 0.6  # sedikit lolos-tinggi
    return (noise * 0.55 * np.exp(-t / 0.06) + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)) * 0.7


def _hat(rng: np.random.Generator, open_: bool = False) -> np.ndarray:
    n = int(SR * (0.18 if open_ else 0.05))
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.concatenate([[0], noise[:-1]])  # lolos-tinggi
    return noise * np.exp(-t / (0.06 if open_ else 0.012)) * 0.25


def _crash(rng: np.random.Generator) -> np.ndarray:
    n = int(SR * 1.4)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.concatenate([[0], noise[:-1]]) * 0.8
    return noise * np.exp(-t / 0.45) * 0.35


def _ding() -> np.ndarray:
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    f = 1568.0
    tone = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.01 * t) + 0.2 * np.sin(2 * np.pi * f * 3.5 * t)
    return tone * _env(n, 0.002, 0.3)


def _klik() -> np.ndarray:
    n = int(SR * 0.04)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2200 * t) * np.exp(-t / 0.006)


def _naik(dur: float = 0.5) -> np.ndarray:
    """Nada meluncur naik (riser pendek) — untuk kemunculan judul/CTA."""
    t = np.arange(int(SR * dur)) / SR
    freq = 300 * (2 ** (t / dur * 2))
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.sin(np.pi * t / dur) * 0.6


def _add(buf: np.ndarray, sig: np.ndarray, at: float, gain: float = 1.0) -> None:
    i = int(at * SR)
    if i >= len(buf) or i + len(sig) <= 0:
        return
    j = max(0, -i)
    i = max(0, i)
    k = min(len(buf) - i, len(sig) - j)
    buf[i:i + k] += sig[j:j + k] * gain


# ------------------------------------------------------------------ komposisi
def _energy_at(sections: list[dict], t: float) -> dict:
    cur = {"energi": 2, "tanpa": []}
    for s in sorted(sections, key=lambda s: s.get("mulai", 0)):
        if t >= s.get("mulai", 0) - 1e-6:
            cur = s
    return cur


def validate_score(score: dict) -> list[str]:
    errs = []
    if not 60 <= float(score.get("bpm", 0)) <= 180:
        errs.append("bpm harus 60–180")
    if str(score.get("kunci", "C")).upper() not in NOTE:
        errs.append(f"kunci tidak dikenal: {score.get('kunci')}")
    if score.get("skala", "mayor") not in SCALE:
        errs.append("skala harus mayor|minor")
    for c in score.get("progresi", []):
        if c.strip().lower().rstrip("7") not in ROMAN:
            errs.append(f"akor tidak dikenal: {c} (pakai angka romawi I–VII)")
    for s in score.get("bagian", []):
        if s.get("energi", 2) not in (1, 2, 3):
            errs.append("energi bagian harus 1, 2, atau 3")
        bad = set(s.get("tanpa", [])) - set(INSTRUMENTS)
        if bad:
            errs.append(f"instrumen tidak dikenal di 'tanpa': {sorted(bad)}")
    for e in score.get("sfx", []):
        if e.get("jenis") not in SFX_KINDS:
            errs.append(f"sfx tidak dikenal: {e.get('jenis')} (pilihan: {', '.join(SFX_KINDS)})")
    return errs


def compose(score: dict, duration: float) -> np.ndarray:
    """Partitur → musik stereo float (puncak dinormalisasi −1 dBFS, fade out 1,5 dtk)."""
    errs = validate_score(score)
    if errs:
        raise ValueError("Partitur musik tidak valid: " + "; ".join(errs))
    rng = np.random.default_rng(int(score.get("seed", 1)))
    bpm = float(score.get("bpm", 110))
    key, scale = str(score.get("kunci", "C")), score.get("skala", "mayor")
    prog = score.get("progresi") or ["I", "V", "vi", "IV"]
    sections = score.get("bagian") or [{"mulai": 0, "energi": 2}]
    beat = 60.0 / bpm
    bar = beat * 4
    n = int(SR * (duration + 2))
    L = np.zeros(n)
    R = np.zeros(n)
    scale_pcs = [(NOTE[key.upper()] + s) % 12 for s in SCALE[scale]]
    melody_prev = 72 + NOTE[key.upper()] % 12

    n_bars = int(np.ceil(duration / bar)) + 1
    for b in range(n_bars):
        t0 = b * bar
        sec = _energy_at(sections, t0)
        e, off = int(sec.get("energi", 2)), set(sec.get("tanpa", []))
        chord = chord_notes(prog[b % len(prog)], key, scale)
        # pad
        if "pad" not in off:
            p = _pad([_hz(m) for m in chord], bar)
            _add(L, p, t0, 0.22 if e > 1 else 0.28)
            _add(R, p, t0, 0.22 if e > 1 else 0.28)
        # bass: akar oktaf 2, ketukan 1 & 3 (energi 3: tiap ketukan + sinkop)
        if "bass" not in off:
            root = chord[0] - 24
            hits = [0, 2] if e == 1 else ([0, 1.5, 2, 3.5] if e == 2 else [0, 0.5, 1.5, 2, 2.5, 3.5])
            for h in hits:
                sig = _bass(_hz(root + (12 if h in (1.5, 3.5) and e == 3 else 0)), beat * 0.9)
                _add(L, sig, t0 + h * beat, 0.45)
                _add(R, sig, t0 + h * beat, 0.45)
        # drum
        if "drum" not in off:
            kicks = [0, 2] if e == 1 else ([0, 1.5, 2] if e == 2 else [0, 1, 2, 2.75, 3])
            for h in kicks:
                k = _kick()
                _add(L, k, t0 + h * beat, 0.7)
                _add(R, k, t0 + h * beat, 0.7)
            if e >= 2:
                for h in (1, 3):
                    s = _snare(rng)
                    _add(L, s, t0 + h * beat, 0.5)
                    _add(R, s, t0 + h * beat, 0.5)
            step = 0.5 if e < 3 else 0.25
            for i in range(int(4 / step)):
                hh = _hat(rng, open_=(e == 3 and i % 8 == 6))
                g = 0.18 if e == 1 else (0.28 if i % 2 == 0 else 0.18)
                _add(L, hh, t0 + i * step * beat, g * 0.8)
                _add(R, hh, t0 + i * step * beat, g)
        # arpeggio 1/8 (energi ≥ 2)
        if "arp" not in off and e >= 2:
            pattern = [0, 1, 2, 1, 0, 2, 1, 2]
            for i, pi in enumerate(pattern):
                sig = _pluck(_hz(chord[pi] + 12), beat * 0.45)
                _add(L, sig, t0 + i * beat / 2, 0.10)
                _add(R, sig, t0 + i * beat / 2, 0.07)
        # melodi marimba: nada akor / skala berjalan, ritme dari seed, frasa 2 birama (tanya–jawab)
        if "melodi" not in off and e >= 2:
            rhythm = [[0, 1, 1.5, 2.5, 3], [0, 0.5, 1, 2, 3.5], [0, 1.5, 2, 3]][(b + int(score.get("seed", 1))) % 3]
            for h in rhythm:
                chord_pcs = [m % 12 for m in chord]
                cands = [m for m in range(melody_prev - 5, melody_prev + 6) if m % 12 in scale_pcs and 67 <= m <= 86]
                strong = h in (0, 2)
                pool = [m for m in cands if m % 12 in chord_pcs] if strong else cands
                pool = pool or cands or [melody_prev]
                melody_prev = int(rng.choice(pool))
                sig = _marimba(_hz(melody_prev), 0.5)
                _add(L, sig, t0 + h * beat, 0.16)
                _add(R, sig, t0 + h * beat, 0.20)
    for a in score.get("aksen", []):
        c = _crash(rng)
        k = _kick()
        _add(L, c, a, 0.8)
        _add(R, c, a, 0.8)
        _add(L, k, a, 0.9)
        _add(R, k, a, 0.9)

    out = np.stack([L, R], axis=1)[: int(SR * duration)]
    out = np.tanh(out * 1.2)  # saturasi lembut: menyatukan & menahan puncak
    fade = int(SR * 1.5)
    if len(out) > fade:
        out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    fin = int(SR * 0.05)
    out[:fin] *= np.linspace(0, 1, fin)[:, None]
    return out


def sfx_track(events: list[dict], duration: float) -> np.ndarray:
    n = int(SR * duration)
    buf = np.zeros((n, 2))
    gen = {"whoosh": lambda: _whoosh(0.5), "thump": lambda: _thump(0.35), "pop": lambda: _pop(0.12)}
    lead = {"whoosh": 0.22, "naik": 0.4}  # bunyi dimulai sebelum titiknya (puncak tepat di t)
    for e in events:
        kind = e["jenis"]
        sig = gen[kind]() if kind in gen else {"ding": _ding, "klik": _klik, "naik": _naik}[kind]()
        if sig.ndim == 1:
            sig = np.stack([sig, sig], axis=1)
        sig = sig / max(1e-9, float(np.abs(sig).max())) * float(10 ** (e.get("db", 0) / 20))
        i = int((float(e["t"]) - lead.get(kind, 0.0)) * SR)
        if i < 0:
            sig, i = sig[-i:], 0
        k = min(n - i, len(sig))
        if k > 0:
            buf[i:i + k] += sig[:k]
    return buf


def render_score(score: dict, duration: float, music_out: Path, sfx_out: Path | None = None) -> tuple[Path, Path | None]:
    music = compose(score, duration)
    _write(music_out, music)  # dinormalisasi ke −3 dBFS; volume akhir diatur di animasi (musik_db) + loudnorm importer
    sfx_path = None
    if sfx_out is not None and score.get("sfx"):
        _write(sfx_out, sfx_track(score["sfx"], duration))
        sfx_path = sfx_out
    return music_out, sfx_path
