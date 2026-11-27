"""Ubah file config (hook, hashtag/keyword, brand, brief tren, panduan caption) secara aman.

Dipakai oleh main.py. Penulisan dilakukan baris-per-baris agar komentar di YAML tidak hilang.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import yaml

from autoreels.config import PATHS

HOOKS_FILE = PATHS["config"] / "hooks.yaml"
PILLARS_FILE = PATHS["config"] / "pillars.yaml"
BRAND_FILE = PATHS["config"] / "brand.yaml"
TREND_FILE = PATHS["trends"] / "brief.md"
CAPTION_GUIDE_FILE = PATHS["config"] / "caption_guide.md"

PILLARS = ["rental", "konstruksi", "profil", "lowongan", "umum"]
PILLAR_LABELS = {"rental": "Rental Motor", "konstruksi": "Konstruksi", "profil": "Profil & Jasa",
                 "lowongan": "Lowongan", "umum": "Konten Umum"}
DEFAULT_BRIEF = {
    "rental": "Promo sewa motor untuk wisatawan yang mau keliling Garut",
    "konstruksi": "Tampilkan progres proyek dari awal sampai selesai",
    "profil": "Perkenalkan layanan Contoh Brand",
    "lowongan": "Info lowongan kerja di Contoh Brand",
    "umum": "Potong bagian paling menarik jadi klip singkat yang informatif",
}
DEFAULT_STYLE = {"rental": "rental_energik", "konstruksi": "proyek_profesional",
                 "profil": "info_lowongan", "lowongan": "info_lowongan",
                 "umum": "klip_informatif"}
HOOK_TYPES = ["visual_wow", "pertanyaan", "harga", "before_after", "angka", "kontras"]
HOOK_MAX_WORDS = 5
HOOK_MAX_CHARS = 28

HOOKS_HEADER = """\
# Pustaka pola hook (bahasa Indonesia) per pilar. Director memilih/menyesuaikan dari sini.
# Aturan: MAKS 5 kata & 28 huruf agar teks hook tampil besar di layar.
# [HARGA]/[N] diisi dari brand.yaml/instruksi — jangan dikarang; bila tidak ada, jangan pakai pola itu.
# File ini bisa diubah lewat `python main.py` → menu Hook.
"""


def _q(value: str) -> str:
    """String YAML ber-kutip ganda yang aman."""
    return json.dumps(value, ensure_ascii=False)


# --- hook -------------------------------------------------------------------------------
def load_hooks() -> dict[str, list[dict]]:
    data = yaml.safe_load(HOOKS_FILE.read_text(encoding="utf-8")) if HOOKS_FILE.exists() else {}
    return {p: list((data or {}).get(p) or []) for p in PILLARS}


def save_hooks(hooks: dict[str, list[dict]]) -> None:
    lines = [HOOKS_HEADER]
    for pillar in PILLARS:
        lines.append(f"{pillar}:")
        items = hooks.get(pillar) or []
        if not items:
            lines.append("  []")
        for h in items:
            lines.append(f"  - {{ type: {h['type']}, text: {_q(h['text'])} }}")
        lines.append("")
    HOOKS_FILE.write_text("\n".join(lines), encoding="utf-8")


def hook_problems(text: str) -> list[str]:
    problems = []
    words = len(text.split())
    if words > HOOK_MAX_WORDS:
        problems.append(f"{words} kata (maks {HOOK_MAX_WORDS})")
    if len(text) > HOOK_MAX_CHARS:
        problems.append(f"{len(text)} huruf (maks {HOOK_MAX_CHARS})")
    return problems


def add_hook(pillar: str, hook_type: str, text: str) -> None:
    hooks = load_hooks()
    hooks[pillar].append({"type": hook_type, "text": text.strip()})
    save_hooks(hooks)


def remove_hook(pillar: str, index: int) -> dict:
    hooks = load_hooks()
    removed = hooks[pillar].pop(index)
    save_hooks(hooks)
    return removed


# --- pilar: hashtag & keyword --------------------------------------------------------------
def normalize_hashtags(raw: str) -> list[str]:
    tags = []
    for part in re.split(r"[\s,;]+", raw):
        tag = re.sub(r"[^0-9a-z_]", "", part.lower().lstrip("#"))
        if tag and f"#{tag}" not in tags:
            tags.append(f"#{tag}")
    return tags


def normalize_keywords(raw: str) -> list[str]:
    out = []
    for part in re.split(r"[,;\n]+", raw):
        kw = " ".join(part.lower().split())
        if kw and kw not in out:
            out.append(kw)
    return out


def get_pillar(pillar: str) -> dict:
    data = yaml.safe_load(PILLARS_FILE.read_text(encoding="utf-8")) or {}
    return data.get(pillar) or {}


def set_pillar_list(pillar: str, key: str, values: list[str]) -> None:
    """Ganti/tambah baris `  key: [...]` di blok pilar tanpa menyentuh baris lain."""
    lines = PILLARS_FILE.read_text(encoding="utf-8").splitlines()
    new_line = f"  {key}: {json.dumps(values, ensure_ascii=False)}"
    start = next((i for i, ln in enumerate(lines) if ln.rstrip() == f"{pillar}:"), None)
    if start is None:
        lines += ["", f"{pillar}:", new_line]
    else:
        end = next((i for i in range(start + 1, len(lines))
                    if lines[i] and not lines[i].startswith((" ", "#"))), len(lines))
        idx = next((i for i in range(start + 1, end) if lines[i].lstrip().startswith(f"{key}:")), None)
        if idx is not None:
            lines[idx] = new_line
        else:
            insert_at = end
            while insert_at > start + 1 and not lines[insert_at - 1].strip():
                insert_at -= 1
            lines.insert(insert_at, new_line)
    PILLARS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- brand -----------------------------------------------------------------------------------
def load_brand_raw() -> dict:
    return yaml.safe_load(BRAND_FILE.read_text(encoding="utf-8")) or {}


def set_brand_value(parent: str, key: str, value: str) -> None:
    """Ganti nilai `key` di dalam blok `parent:` (mis. pricing.rental_per_day), komentar baris dipertahankan."""
    lines = BRAND_FILE.read_text(encoding="utf-8").splitlines()
    p = next((i for i, ln in enumerate(lines) if ln.rstrip().startswith(f"{parent}:")), None)
    if p is None:
        raise KeyError(f"Blok '{parent}' tidak ada di brand.yaml")
    for i in range(p + 1, len(lines)):
        ln = lines[i]
        if ln and not ln.startswith((" ", "#")):
            break
        m = re.match(rf"^(\s+){re.escape(key)}:\s*(\"[^\"]*\"|[^#]*?)(\s*#.*)?$", ln)
        if m:
            lines[i] = f"{m.group(1)}{key}: {_q(value)}{m.group(3) or ''}"
            BRAND_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    raise KeyError(f"'{parent}.{key}' tidak ada di brand.yaml")


# --- brief tren --------------------------------------------------------------------------------
def write_trend_brief(*, formats: list[str], hooks: list[str], audio: list[str],
                      moments: list[str], notes: list[str]) -> Path:
    def section(title: str, items: list[str]) -> str:
        body = "\n".join(f"- {x}" for x in items) if items else "- [ISI]"
        return f"## {title}\n{body}\n"

    text = (
        "# Brief Tren Mingguan\n\n"
        "> Diisi MANUAL (lewat `python main.py` atau edit langsung). "
        "Director hanya boleh memakai tren yang tertulis di sini.\n\n"
        f"**Diperbarui:** {date.today():%Y-%m-%d}\n\n"
        + section("Format yang sedang ramai", formats) + "\n"
        + section("Gaya hook yang naik", hooks) + "\n"
        + section("Audio trending (judul saja)", audio) + "\n"
        + section("Momen musiman / event Garut", moments) + "\n"
        + section("Catatan lain", notes)
    )
    TREND_FILE.write_text(text, encoding="utf-8")
    return TREND_FILE


def trend_updated() -> str:
    """Tanggal '**Diperbarui:** YYYY-MM-DD' di brief tren (kosong bila tidak ada)."""
    if not TREND_FILE.exists():
        return ""
    m = re.search(r"\*\*Diperbarui:\*\*\s*([0-9-]+)", TREND_FILE.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def read_trend_items() -> dict[str, list[str]]:
    """Baca isi brief tren per bagian (mengabaikan placeholder [ISI])."""
    out: dict[str, list[str]] = {}
    current = None
    if not TREND_FILE.exists():
        return out
    for ln in TREND_FILE.read_text(encoding="utf-8").splitlines():
        if ln.startswith("## "):
            current = ln[3:].strip()
            out[current] = []
        elif current and ln.startswith("- ") and "[ISI" not in ln:
            out[current].append(ln[2:].strip())
    return out


# --- panduan caption ---------------------------------------------------------------------------
def load_caption_guide() -> dict[str, str]:
    if not CAPTION_GUIDE_FILE.exists():
        return {}
    out = {}
    for ln in CAPTION_GUIDE_FILE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^- \*\*(.+?):\*\* (.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def load_caption_examples() -> list[str]:
    """Contoh caption di bawah heading '### Contoh N'."""
    if not CAPTION_GUIDE_FILE.exists():
        return []
    examples, current = [], None
    for ln in CAPTION_GUIDE_FILE.read_text(encoding="utf-8").splitlines():
        if ln.startswith("### Contoh"):
            if current is not None:
                examples.append("\n".join(current).strip())
            current = []
        elif ln.startswith("#") and current is not None:
            examples.append("\n".join(current).strip())
            current = None
        elif current is not None:
            current.append(ln)
    if current is not None:
        examples.append("\n".join(current).strip())
    return [e for e in examples if e]


def write_caption_guide(fields: dict[str, str], examples: list[str]) -> Path:
    lines = ["# Panduan Caption Instagram Brand", "",
             "> Dibaca Director saat menulis caption. Ubah lewat `python main.py`.", ""]
    lines += [f"- **{k}:** {v}" for k, v in fields.items() if v]
    if examples:
        lines += ["", "## Contoh caption yang bagus", ""]
        for i, ex in enumerate(examples, 1):
            lines += [f"### Contoh {i}", ex.strip(), ""]
    CAPTION_GUIDE_FILE.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return CAPTION_GUIDE_FILE
