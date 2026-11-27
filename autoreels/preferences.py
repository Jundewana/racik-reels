"""Belajar dari editan manusia (tambahan tahap 4).

1. Setelah AI membuat Reel, EDL versi AI disimpan sebagai output/<job>/edl_ai.json (tidak pernah ditimpa).
2. Setiap render ulang dari EDL (edit di web, voice over, `autoreels render`), perbedaan EDL manusia vs AI
   dicatat ke output/<job>/edits.json (selalu dibandingkan dengan versi AI, jadi file ini menimpa diri sendiri).
3. `summarize()` merangkum edits.json semua job (LLM, prompts/preferences.md) → config/preferensi.md
   bagian "Ringkasan otomatis". Bagian "Catatan manual" ditulis pemilik dan tidak pernah diubah AI.
4. Director membaca config/preferensi.md sebagai `preferensi_pemilik`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from autoreels.config import PATHS, load_prompt
from autoreels.edl import EDL

AI_FILE = "edl_ai.json"
EDITS_FILE = "edits.json"
PREF_FILE = "preferensi.md"
AUTO_HEAD = "## Ringkasan otomatis"
MANUAL_HEAD = "## Catatan manual"
MAX_JOBS = 30          # job terbaru yang dirangkum (hemat token)
MAX_PREF_CHARS = 2500  # batas teks preferensi yang dikirim ke Director


def pref_path() -> Path:
    return PATHS["config"] / PREF_FILE


# --- 1. simpan versi AI -----------------------------------------------------------------
def snapshot_ai(out_dir: Path, edl: EDL) -> None:
    """Simpan EDL versi AI sekali saja (job baru); render ulang tidak menimpanya."""
    path = out_dir / AI_FILE
    if not path.exists():
        edl.save(path)


# --- 2. beda EDL manusia vs AI ---------------------------------------------------------
def _txt(v) -> str:
    return f"“{v}”" if v else "(kosong)"


def _val(v):
    return getattr(v, "value", v)


def diff_edl(ai: EDL, human: EDL) -> list[str]:
    """Daftar perubahan yang dibuat manusia, dalam bahasa Indonesia singkat (satu baris per perubahan)."""
    out: list[str] = []
    if (ai.hook.overlay_text or "") != (human.hook.overlay_text or ""):
        out.append(f"teks hook diubah: {_txt(ai.hook.overlay_text)} → {_txt(human.hook.overlay_text)}")
    if ai.hook.type != human.hook.type:
        out.append(f"tipe hook diubah: {_val(ai.hook.type)} → {_val(human.hook.type)}")
    a_cta, h_cta = (ai.cta.text if ai.cta else ""), (human.cta.text if human.cta else "")
    if a_cta != h_cta:
        out.append(f"teks CTA diubah: {_txt(a_cta)} → {_txt(h_cta)}")

    a_segs = {s.index: s for s in ai.segments}
    h_segs = {s.index: s for s in human.segments}
    for i in sorted(a_segs.keys() & h_segs.keys()):
        a, h = a_segs[i], h_segs[i]
        if (a.overlay_text or "") != (h.overlay_text or ""):
            out.append(f"teks overlay segmen {i} ({_val(a.role)}): {_txt(a.overlay_text)} → {_txt(h.overlay_text)}")
        if (a.source_file, a.scene_id) != (h.source_file, h.scene_id):
            out.append(f"adegan segmen {i} ({_val(a.role)}) diganti: {a.reason or a.scene_id} → "
                       f"{h.reason or h.scene_id}")
        elif abs((a.end - a.start) - (h.end - h.start)) > 0.25:
            out.append(f"durasi segmen {i} ({_val(a.role)}): {a.end - a.start:.1f} → {h.end - h.start:.1f} dtk")
        if abs(a.speed - h.speed) > 0.01:
            out.append(f"kecepatan segmen {i}: {a.speed:g}× → {h.speed:g}×")
        if a.transition_in != h.transition_in:
            out.append(f"transisi segmen {i}: {_val(a.transition_in)} → {_val(h.transition_in)}")
    for i in sorted(a_segs.keys() - h_segs.keys()):
        s = a_segs[i]
        out.append(f"segmen {i} ({_val(s.role)}) dibuang: {s.reason or s.scene_id}")
    for i in sorted(h_segs.keys() - a_segs.keys()):
        s = h_segs[i]
        out.append(f"segmen {i} ({_val(s.role)}) ditambah: {s.reason or s.scene_id}")

    if ai.style_preset != human.style_preset:
        out.append(f"style diganti: {ai.style_preset} → {human.style_preset}")
    if ai.music.mood != human.music.mood:
        out.append(f"mood musik: {_val(ai.music.mood)} → {_val(human.music.mood)}")
    if abs(ai.music.volume_db - human.music.volume_db) > 0.5:
        out.append(f"volume musik: {ai.music.volume_db:g} → {human.music.volume_db:g} dB")
    if ai.branding.logo != human.branding.logo:
        out.append(f"logo {'dinyalakan' if human.branding.logo else 'dimatikan'}")
    for f in ("blur_faces", "blur_plates"):
        if getattr(ai.privacy, f) != getattr(human.privacy, f):
            out.append(f"privasi {f}: {getattr(ai.privacy, f)} → {getattr(human.privacy, f)}")

    if ai.narration and human.narration:
        a_ph, h_ph = ai.narration.phrases, human.narration.phrases
        changed = [(a.text, h.text) for a, h in zip(a_ph, h_ph) if a.text.strip() != h.text.strip()]
        for a, h in changed[:8]:
            out.append(f"subtitle dikoreksi: {_txt(a)} → {_txt(h)}")
        if len(changed) > 8:
            out.append(f"(+{len(changed) - 8} baris subtitle lain dikoreksi)")

    a_vo = [(round(x.at_sec, 1), x.text) for x in ai.voiceover.lines]
    h_vo = [(round(x.at_sec, 1), x.text) for x in human.voiceover.lines]
    if ai.voiceover.mode != human.voiceover.mode:
        out.append(f"voice over: {_val(ai.voiceover.mode)} → {_val(human.voiceover.mode)}")
    if a_vo != h_vo and h_vo:
        a_t, h_t = " / ".join(t for _, t in a_vo), " / ".join(t for _, t in h_vo)
        out.append(f"naskah voice over diubah: {_txt(a_t[:200])} → {_txt(h_t[:200])}")

    if ai.caption_suggestion.strip() != human.caption_suggestion.strip():
        out.append(f"caption diubah: {_txt(ai.caption_suggestion[:200])} → {_txt(human.caption_suggestion[:200])}")
    if set(ai.hashtags) != set(human.hashtags):
        added, removed = set(human.hashtags) - set(ai.hashtags), set(ai.hashtags) - set(human.hashtags)
        out.append(f"hashtag: +{sorted(added)} −{sorted(removed)}")
    return out


def record_edits(out_dir: Path, human: EDL) -> list[str]:
    """Catat perbedaan EDL manusia vs versi AI ke edits.json. Job lama tanpa edl_ai.json dilewati."""
    ai_file = out_dir / AI_FILE
    if not ai_file.exists():
        return []
    try:
        changes = diff_edl(EDL.load(ai_file), human)
    except Exception:  # noqa: BLE001 — pencatatan preferensi tidak boleh menggagalkan render
        return []
    path = out_dir / EDITS_FILE
    if changes:
        path.write_text(json.dumps({
            "job_id": out_dir.name, "pillar": _val(human.pillar), "style": human.style_preset,
            "updated": f"{datetime.now():%Y-%m-%d %H:%M:%S}", "changes": changes,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    elif path.exists():
        path.unlink()  # editan dikembalikan persis ke versi AI
    return changes


# --- 3. rangkum jadi preferensi --------------------------------------------------------
def collect_edits(output_dir: Path | None = None, since: str | None = None) -> list[dict]:
    """edits.json semua job (terbaru dulu, maks MAX_JOBS); `since` = hanya yang diperbarui setelah waktu ini."""
    root = output_dir or PATHS["output"]
    items = []
    for f in root.glob(f"*/{EDITS_FILE}"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if d.get("changes") and (since is None or d.get("updated", "") > since):
            items.append(d)
    items.sort(key=lambda d: d.get("updated", ""), reverse=True)
    return items[:MAX_JOBS]


def _split(text: str) -> tuple[str, str]:
    """(ringkasan otomatis, catatan manual) dari isi preferensi.md."""
    auto, manual, cur = [], [], None
    for line in text.splitlines():
        if line.strip().startswith(AUTO_HEAD):
            cur = auto
            continue
        if line.strip().startswith(MANUAL_HEAD):
            cur = manual
            continue
        if cur is not None:
            cur.append(line)
    return "\n".join(auto).strip(), "\n".join(manual).strip()


def last_summarized() -> str | None:
    """Waktu rangkuman terakhir (dari baris `<!-- dirangkum: ... -->`)."""
    p = pref_path()
    if not p.exists():
        return None
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("<!-- dirangkum:"):
            return line.removeprefix("<!-- dirangkum:").removesuffix("-->").strip()
    return None


def status() -> dict:
    """Untuk web/CLI: jumlah job yang diedit, berapa yang belum dirangkum, isi file."""
    p = pref_path()
    return {
        "edited_jobs": len(collect_edits()),
        "new_since_summary": len(collect_edits(since=last_summarized())) if last_summarized() else len(collect_edits()),
        "last_summarized": last_summarized(),
        "text": p.read_text(encoding="utf-8") if p.exists() else "",
    }


def write_text(text: str) -> None:
    """Simpan isi preferensi.md yang diedit pemilik (penanda waktu rangkuman dipertahankan)."""
    stamp = last_summarized()
    body = "\n".join(line for line in text.strip().splitlines() if not line.startswith("<!-- dirangkum:"))
    pref_path().write_text((f"<!-- dirangkum: {stamp} -->\n" if stamp else "") + body + "\n", encoding="utf-8")


def compose(auto: str, manual: str, stamp: str) -> str:
    return (f"<!-- dirangkum: {stamp} -->\n# Preferensi pemilik (dibaca Director)\n\n"
            f"{AUTO_HEAD}\n_Dibuat AI dari editan Anda; boleh diedit/dihapus. Dirangkum ulang menimpa bagian ini._\n\n"
            f"{auto.strip()}\n\n{MANUAL_HEAD}\n_Tulis aturan Anda sendiri di sini; tidak pernah diubah AI._\n\n"
            f"{manual.strip()}\n")


def summarize(llm=None, model: str | None = None, log=print) -> str:
    """Rangkum editan semua job → config/preferensi.md (bagian otomatis). Kembalikan isi file."""
    edits = collect_edits()
    if not edits:
        raise ValueError("Belum ada editan yang tercatat. Edit hasil Reel (hook, CTA, subtitle, dll.) lalu "
                         "render ulang; editan dari job sebelum fitur ini tidak tercatat.")
    if llm is None:
        from autoreels.llm import LLMClient

        llm = LLMClient(log=log)
    p = pref_path()
    old_auto, manual = _split(p.read_text(encoding="utf-8")) if p.exists() else ("", "")
    lines = []
    for d in edits:
        lines.append(f"### job {d['job_id']} (pilar {d.get('pillar')}, style {d.get('style')})")
        lines += [f"- {c}" for c in d["changes"]]
    user = (f"Ringkasan preferensi sebelumnya (perbarui, jangan dibuang tanpa alasan):\n{old_auto or '(belum ada)'}\n\n"
            f"Catatan manual pemilik (jangan diulang, jangan dibantah):\n{manual or '(kosong)'}\n\n"
            f"Editan manusia terhadap hasil AI ({len(edits)} job, terbaru dulu):\n" + "\n".join(lines))
    messages = [{"role": "system", "content": load_prompt("preferences")}, {"role": "user", "content": user}]
    auto = llm.complete(messages, model=model, purpose="rangkum preferensi", temperature=0.2).strip()
    from autoreels.llm import strip_code_fence

    auto = strip_code_fence(auto).strip()
    text = compose(auto, manual, f"{datetime.now():%Y-%m-%d %H:%M:%S}")
    p.write_text(text, encoding="utf-8")
    log(f"Preferensi dirangkum dari {len(edits)} job → {p}")
    return text


# --- 4. untuk Director -----------------------------------------------------------------
def for_director() -> str | None:
    """Isi preferensi (tanpa komentar & petunjuk) untuk konteks Director; None bila kosong."""
    p = pref_path()
    if not p.exists():
        return None
    auto, manual = _split(p.read_text(encoding="utf-8"))
    clean = lambda t: "\n".join(x for x in t.splitlines() if x.strip() and not x.strip().startswith("_"))  # noqa: E731
    parts = [x for x in (clean(auto), clean(manual)) if x]
    text = "\n".join(parts).strip()
    return text[:MAX_PREF_CHARS] if text else None
