"""Evaluasi (Tahap 4): rangkum job di output/ → eval/report.md + eval/results.csv.

Dua cara pakai (`autoreels eval` atau `python eval/run_eval.py`):
- rangkum job yang sudah ada (tanpa biaya AI), bisa disaring per tanggal;
- `--jalankan`: proses set uji di eval/testset/manifest.csv (per mesin, dengan/tanpa Critic), lalu rangkum.

Metrik otomatis sesuai CLAUDE.md bagian 9: waktu proses, biaya API, ketepatan durasi, hook ≤ 3 dtk, ketepatan beat,
skor rubrik Critic, jumlah revisi, error. Metrik manusia & lapangan diisi terpisah.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean

from autoreels.config import PATHS, ROOT
from autoreels.critic import LABELS

EVAL_DIR = ROOT / "eval"
MANIFEST = EVAL_DIR / "testset" / "manifest.csv"
MANIFEST_FIELDS = ["set_id", "pillar", "folder", "style", "durasi", "brief", "narasi", "bicara", "tujuan",
                   "jumlah_klip", "ada_ucapan",
                   "catatan"]


@dataclass
class JobMetrics:
    job_id: str
    created: str
    pillar: str
    style: str
    engine: str
    flow: str                 # video | narasi
    critic_mode: str          # revisi | nilai | mati
    status: str
    set_id: str = ""
    director_model: str = ""
    critic_model: str = ""
    target: float | None = None
    duration: float | None = None
    hook_duration: float | None = None
    beat_accuracy: float | None = None
    segments: int | None = None
    cost_usd: float | None = None
    process_sec: float | None = None
    revisions: int | None = None
    critic_revisions: int = 0
    critic_average: float | None = None
    critic_hook: int | None = None
    critic_scores: dict = field(default_factory=dict)
    failed_checks: list[str] = field(default_factory=list)

    @property
    def duration_ok(self) -> bool | None:
        if not self.target or self.duration is None:
            return None
        return abs(self.duration - self.target) <= self.target * 0.10

    @property
    def hook_ok(self) -> bool | None:
        return None if self.hook_duration is None else self.hook_duration <= 3.0 + 1e-3


@dataclass
class FailedJob:
    job_id: str
    reason: str


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


CRITIC_LABEL = {"revisi": "Critic + revisi", "nilai": "tanpa revisi (Critic menilai saja)", "mati": "tanpa Critic"}


def _critic_mode(v) -> str:
    """job.json lama menyimpan bool; baru: revisi | nilai | mati."""
    if v is True:
        return "revisi"
    if v in (False, None):
        return "mati"
    return str(v) if str(v) in CRITIC_LABEL else "mati"


def _date_of(job_id: str) -> str:
    return job_id[:8] if re.match(r"\d{8}-", job_id) else ""


def load_job(out_dir: Path) -> JobMetrics | None:
    """Metrik satu job (None bila bukan hasil pipeline AutoReels, mis. video impor)."""
    job = _read_json(out_dir / "job.json")
    if not job or job.get("source") == "import" or not (out_dir / "reel.mp4").exists():
        return None
    result = _read_json(out_dir / "result.json")
    stats = result.get("stats") or {}
    report = (out_dir / "report.md").read_text(encoding="utf-8") if (out_dir / "report.md").exists() else ""
    revisions = stats.get("revisions")
    if revisions is None:  # job lama: baca dari report.md
        m = re.search(r"Revisi Director: (\d+)", report)
        revisions = int(m.group(1)) if m else None
    critic = result.get("critic") or _read_json(out_dir / "critic.json") or {}
    final = critic.get("final") or {}
    status = result.get("status") or ((out_dir / "status.txt").read_text(encoding="utf-8").strip()
                                      if (out_dir / "status.txt").exists() else "perlu_tinjau")
    return JobMetrics(
        job_id=out_dir.name, created=str(job.get("created", "")).split(" (")[0], pillar=job.get("pillar", ""),
        style=job.get("style", ""), engine=job.get("engine", "api"), flow=job.get("flow", "video"),
        critic_mode=_critic_mode(job.get("critic")), status=status, set_id=job.get("eval_set", ""),
        director_model=(job.get("models") or {}).get("director", ""),
        critic_model=(job.get("models") or {}).get("critic", ""),
        target=stats.get("target_duration") or job.get("duration"),
        duration=stats.get("total_duration"), hook_duration=stats.get("hook_duration"),
        beat_accuracy=stats.get("beat_accuracy") if job.get("flow", "video") == "video" else None,
        segments=stats.get("segments"), cost_usd=stats.get("cost_usd"), process_sec=stats.get("process_sec"),
        revisions=revisions, critic_revisions=critic.get("critic_revisions", 0),
        critic_average=final.get("average"), critic_hook=final.get("hook"), critic_scores=final.get("scores") or {},
        failed_checks=[f"{i['group']} — {i['name']}" for i in result.get("checklist") or []
                       if i.get("required") and not i.get("passed")],
    )


def collect(since: str | None = None, job_ids: list[str] | None = None) -> tuple[list[JobMetrics], list[FailedJob]]:
    """since: 'YYYY-MM-DD' (job dibuat pada/sesudah tanggal itu). job_ids: hanya job ini."""
    floor = since.replace("-", "") if since else ""
    wanted = set(job_ids or [])
    jobs: list[JobMetrics] = []
    for out_dir in sorted(PATHS["output"].glob("*/")):
        if wanted and out_dir.name not in wanted or floor and _date_of(out_dir.name) < floor:
            continue
        m = load_job(out_dir)
        if m:
            jobs.append(m)
    failed: list[FailedJob] = []
    for work_dir in sorted(PATHS["work"].glob("*/")):
        if wanted and work_dir.name not in wanted or floor and _date_of(work_dir.name) < floor:
            continue
        prog = _read_json(work_dir / "progress.json")
        if prog.get("state") == "gagal" and not (PATHS["output"] / work_dir.name / "reel.mp4").exists():
            err = work_dir / "error.txt"
            reason = err.read_text(encoding="utf-8").strip().splitlines()[0] if err.exists() else "tidak tercatat"
            failed.append(FailedJob(work_dir.name, reason[:160]))
    return jobs, failed


# ---------------------------------------------------------------- laporan
def _avg(values) -> float | None:
    vals = [v for v in values if v is not None]
    return float(mean(vals)) if vals else None


def _pct(flags) -> str:
    vals = [f for f in flags if f is not None]
    return f"{sum(vals) / len(vals):.0%} ({sum(vals)}/{len(vals)})" if vals else "-"


def _fmt(v, suffix: str = "", digits: int = 2) -> str:
    if v is None:
        return "-"
    return f"{v:.{digits}f}{suffix}" if isinstance(v, float) else f"{v}{suffix}"


def _summary_row(label: str, jobs: list[JobMetrics]) -> str:
    return (f"| {label} | {len(jobs)} | {_pct([j.status == 'siap_unggah' for j in jobs])} | "
            f"{_fmt(_avg(j.process_sec for j in jobs), ' dtk', 0)} | {_fmt(_avg(j.cost_usd for j in jobs), '', 4)} | "
            f"{_pct([j.duration_ok for j in jobs])} | {_pct([j.hook_ok for j in jobs])} | "
            f"{_fmt(_avg(j.beat_accuracy for j in jobs))} | {_fmt(_avg(j.revisions for j in jobs))} | "
            f"{_fmt(_avg(j.critic_average for j in jobs))} | {_fmt(_avg(j.critic_hook for j in jobs))} |")


SUMMARY_HEAD = ("| Kelompok | Job | Siap unggah | Waktu proses | Biaya (USD) | Durasi ±10% | Hook ≤ 3 dtk | "
                "Ketepatan beat | Revisi validasi | Skor Critic | Skor hook |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|")


def build_report(jobs: list[JobMetrics], failed: list[FailedJob], title: str = "") -> str:
    now = f"{datetime.now():%Y-%m-%d %H:%M}"
    lines = [f"# Laporan Evaluasi AutoReels{(' — ' + title) if title else ''}", "",
             f"Dibuat {now}. {len(jobs)} job selesai, {len(failed)} job gagal. "
             "Metrik otomatis; rubrik manusia & metrik lapangan dicatat terpisah (lihat eval/rubric.md).", ""]
    if not jobs:
        return "\n".join(lines + ["Belum ada job untuk dirangkum."]) + "\n"

    lines += ["## Ringkasan", SUMMARY_HEAD, _summary_row("**Semua**", jobs), ""]
    groups: dict[str, list[JobMetrics]] = defaultdict(list)
    for j in jobs:
        groups[f"mesin {j.engine}, {CRITIC_LABEL[j.critic_mode]}"].append(j)
    if len(groups) > 1:
        lines += ["## Perbandingan mesin & Critic", SUMMARY_HEAD,
                  *[_summary_row(k, v) for k, v in sorted(groups.items())], ""]
    by_pillar: dict[str, list[JobMetrics]] = defaultdict(list)
    for j in jobs:
        by_pillar[f"{j.pillar} ({j.flow})"].append(j)
    lines += ["## Per pilar & alur", SUMMARY_HEAD, *[_summary_row(k, v) for k, v in sorted(by_pillar.items())], ""]

    by_model: dict[str, list[JobMetrics]] = defaultdict(list)
    for j in jobs:
        if j.director_model:
            by_model[j.director_model].append(j)
    if len(by_model) > 1:
        judges = sorted({j.critic_model for j in jobs if j.critic_model})
        lines += ["## Perbandingan model Director", "",
                  f"Penilai (Critic): {', '.join(judges) or '-'}"
                  + (" — sama untuk semua model, jadi skor bisa dibandingkan." if len(judges) == 1 else
                     " — BERBEDA antar job; bandingkan skor dengan hati-hati."), "",
                  SUMMARY_HEAD, *[_summary_row(k, v) for k, v in sorted(by_model.items())], ""]
    pairs = defaultdict(dict)
    for j in jobs:
        if j.set_id and j.critic_mode in ("revisi", "nilai"):
            pairs[j.set_id][j.critic_mode] = j  # job terbaru per set & mode
    paired = {k: v for k, v in pairs.items() if len(v) == 2}
    if paired:
        lines += ["## Efek revisi Critic per set uji (sama-sama dinilai Critic)",
                  "| Set | Status tanpa revisi | Status dengan revisi | Skor tanpa revisi | Skor dengan revisi | "
                  "Hook tanpa | Hook dengan | Revisi Critic | Biaya tambahan |",
                  "|---|---|---|---|---|---|---|---|---|"]
        gains = []
        for sid, v in sorted(paired.items()):
            a, b = v["nilai"], v["revisi"]
            if a.critic_average is not None and b.critic_average is not None:
                gains.append(b.critic_average - a.critic_average)
            extra = (b.cost_usd or 0) - (a.cost_usd or 0)
            lines.append(f"| {sid} | {a.status} | {b.status} | {_fmt(a.critic_average)} | {_fmt(b.critic_average)} | "
                         f"{_fmt(a.critic_hook)} | {_fmt(b.critic_hook)} | {b.critic_revisions} | {extra:+.4f} |")
        ready_a = sum(v["nilai"].status == "siap_unggah" for v in paired.values())
        ready_b = sum(v["revisi"].status == "siap_unggah" for v in paired.values())
        lines += ["", f"Siap unggah: {ready_a}/{len(paired)} tanpa revisi → {ready_b}/{len(paired)} dengan revisi Critic. "
                      + (f"Rata-rata perubahan skor Critic: {mean(gains):+.2f}." if gains else ""), ""]

    scored = [j for j in jobs if j.critic_scores]
    if scored:
        lines += ["## Skor rubrik Critic per aspek (rata-rata, 1–5)", "| Aspek | Rata-rata | Terendah | < 4 |",
                  "|---|---|---|---|"]
        for k, label in LABELS.items():
            vals = [j.critic_scores.get(k) for j in scored if j.critic_scores.get(k) is not None]
            if vals:
                lines.append(f"| {label} | {mean(vals):.2f} | {min(vals)} | {sum(v < 4 for v in vals)} |")
        revised = [j for j in scored if j.critic_revisions]
        lines += ["", f"Revisi atas catatan Critic: {len(revised)} dari {len(scored)} job "
                      f"(rata-rata {_fmt(_avg(j.critic_revisions for j in scored))} putaran).", ""]

    fails = Counter(f for j in jobs for f in j.failed_checks)
    if fails:
        lines += ["## Butir checklist wajib yang paling sering gagal", "| Butir | Jumlah job |", "|---|---|",
                  *[f"| {k} | {v} |" for k, v in fails.most_common(10)], ""]
    if failed:
        lines += ["## Job gagal (error)", "| Job | Alasan |", "|---|---|",
                  *[f"| {f.job_id} | {f.reason.replace('|', '/')} |" for f in failed], ""]

    lines += ["## Per job", "| Job | Set | Pilar | Mesin | Critic | Status | Durasi/target | Hook | Beat | Biaya | "
              "Waktu | Skor Critic |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for j in jobs:
        lines.append(
            f"| {j.job_id} | {j.set_id or '-'} | {j.pillar} | {j.engine} | {j.critic_mode} | "
            f"{'✅' if j.status == 'siap_unggah' else '⚠️'} {j.status} | {_fmt(j.duration, '', 1)}/{_fmt(j.target, '', 0)} | "
            f"{_fmt(j.hook_duration, '', 2)} | {_fmt(j.beat_accuracy)} | {_fmt(j.cost_usd, '', 4)} | "
            f"{_fmt(j.process_sec, '', 0)} | {_fmt(j.critic_average)} |")
    return "\n".join(lines) + "\n"


def write_outputs(jobs: list[JobMetrics], failed: list[FailedJob], title: str = "",
                  out_dir: Path = EVAL_DIR) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "report.md"
    report.write_text(build_report(jobs, failed, title), encoding="utf-8")
    csv_path = out_dir / "results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        cols = [k for k in asdict(jobs[0])] if jobs else list(JobMetrics.__dataclass_fields__)
        w = csv.DictWriter(f, fieldnames=[*cols, "duration_ok", "hook_ok"])
        w.writeheader()
        for j in jobs:
            row = asdict(j)
            row["critic_scores"] = json.dumps(row["critic_scores"])
            row["failed_checks"] = "; ".join(row["failed_checks"])
            w.writerow({**row, "duration_ok": j.duration_ok, "hook_ok": j.hook_ok})
    return report, csv_path


# ---------------------------------------------------------------- menjalankan set uji
def read_manifest(path: Path = MANIFEST) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)
                if (row.get("set_id") or "").strip() and not row["set_id"].startswith("#")]


def run_testset(*, engines: list[str], critic_modes: list, preview: bool, only: list[str] | None, log=print,
                on_progress=None, models: list[str] | None = None, judge: str | None = None) -> list[str]:
    """Proses tiap baris manifest untuk tiap kombinasi mesin × Critic. Kembalikan daftar job_id."""
    from autoreels.config import load_pillars
    from autoreels.ingest import make_job_id
    from autoreels.pipeline import run_pipeline

    rows = [r for r in read_manifest() if not only or r["set_id"] in only]
    if not rows:
        raise RuntimeError(f"Tidak ada set uji di {MANIFEST.relative_to(ROOT)} (isi kolom set_id, pillar, folder, …).")
    pillars = load_pillars()
    job_ids: list[str] = []
    for row in rows:
        folder = ROOT / row["folder"]
        if not folder.exists():
            log(f"[lewati] {row['set_id']}: folder {row['folder']} tidak ada")
            continue
        pillar = row["pillar"]
        style = row.get("style") or pillars.get(pillar, {}).get("default_style", "rental_energik")
        narration = ROOT / row["narasi"] if row.get("narasi") else None
        talk = ROOT / row["bicara"] if row.get("bicara") else None
        purpose = row.get("tujuan") or None
        for engine, model in [(e, m) for e in engines for m in (models or [None])]:
            for use_critic in critic_modes:
                job_id = make_job_id(pillar)
                mode = {True: 'revisi', 'nilai': 'nilai'}.get(use_critic, 'mati')
                log(f"=== {row['set_id']} · {model or 'mesin ' + engine} · Critic {mode} → {job_id}")
                try:
                    run_pipeline(input_path=folder, pillar=pillar, brief=row.get("brief") or f"Reel {pillar}",
                                 style_name=style, duration=float(row.get("durasi") or 20), preview=preview,
                                 engine=engine, critic=use_critic, narration=narration, talk=talk,
                                 purpose=purpose, job_id=job_id, log=log, llm_model=model, critic_model=judge,
                                 on_progress=on_progress)
                except Exception as e:  # noqa: BLE001 — satu set gagal tidak menghentikan evaluasi
                    log(f"[gagal] {row['set_id']}: {e}")
                    err = PATHS["work"] / job_id / "error.txt"
                    err.parent.mkdir(parents=True, exist_ok=True)
                    err.write_text(f"{type(e).__name__}: {e}\n", encoding="utf-8")
                _tag_job(job_id, row["set_id"])
                job_ids.append(job_id)
    return job_ids


def _tag_job(job_id: str, set_id: str) -> None:
    """Catat set uji di job.json agar laporan bisa mengelompokkan per set."""
    f = PATHS["output"] / job_id / "job.json"
    data = _read_json(f)
    if data:
        data["eval_set"] = set_id
        f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
