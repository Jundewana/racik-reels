"""Pelacak progress pipeline: persen keseluruhan + langkah aktif.

Ditulis juga ke work/<job_id>/progress.json agar `autoreels status` bisa memantau dari terminal lain.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# bobot tiap langkah terhadap total 100%
STEPS: dict[str, tuple[str, float]] = {
    "ingest": ("Ingest & proxy", 5),
    "analyze": ("Analisis adegan & musik", 20),
    "describe": ("Deskripsi visual (AI)", 30),
    "direct": ("Director menyusun edit (AI)", 15),
    "render": ("Render video", 25),
    "checklist": ("Checklist Siap Unggah", 5),
}


NOTE_MAX = 40     # catatan keputusan AI terakhir yang disimpan
NOTE_LINES = 24   # baris per catatan


class Progress:
    def __init__(self, job_id: str, file: Path | None = None, on_update=None,
                 labels: dict[str, str] | None = None) -> None:
        self.labels = labels or {}  # ganti label langkah (mis. untuk alur impor)
        self.job_id = job_id
        self.file = file
        self.on_update = on_update
        self.step = "ingest"
        self.step_frac = 0.0
        self.detail = ""
        self.started = time.time()
        self.done_steps: set[str] = set()
        self.state = "berjalan"
        self.notes: list[dict] = []  # keputusan AI yang ditampilkan di layar proses web

    @property
    def percent(self) -> float:
        total = sum(w for _, w in STEPS.values())
        done = sum(STEPS[s][1] for s in self.done_steps)
        if self.step not in self.done_steps and self.step in STEPS:
            done += STEPS[self.step][1] * min(1.0, self.step_frac)
        return round(100 * done / total, 1)

    def start(self, step: str, detail: str = "") -> None:
        self.step, self.step_frac, self.detail = step, 0.0, detail
        self._emit()

    def update(self, done: float, total: float, detail: str = "") -> None:
        self.step_frac = done / total if total else 1.0
        if detail:
            self.detail = detail
        self._emit()

    def finish(self, step: str) -> None:
        self.done_steps.add(step)
        if self.step == step:
            self.step_frac = 1.0
        self._emit()

    def note(self, title: str, lines: list[str] | None = None) -> None:
        """Catat keputusan AI (mis. hook terpilih, alasan tiap potongan) untuk ditampilkan langsung di web."""
        self.notes.append({"at": round(time.time() - self.started, 1), "step": self.step, "title": title,
                           "lines": [str(x)[:220] for x in (lines or []) if str(x).strip()][:NOTE_LINES]})
        self.notes = self.notes[-NOTE_MAX:]
        self._emit()

    def end(self, state: str) -> None:
        self.state = state
        if state == "selesai":
            self.done_steps = set(STEPS)
        self._emit()

    def snapshot(self) -> dict:
        return {
            "job_id": self.job_id,
            "percent": self.percent,
            "step": self.step,
            "step_label": self.labels.get(self.step) or STEPS.get(self.step, (self.step, 0))[0],
            "step_index": list(STEPS).index(self.step) + 1 if self.step in STEPS else 0,
            "steps_total": len(STEPS),
            "detail": self.detail,
            "elapsed_sec": round(time.time() - self.started, 1),
            "state": self.state,
            "notes": self.notes,
        }

    def _emit(self) -> None:
        snap = self.snapshot()
        if self.file:
            try:
                self.file.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass
        if self.on_update:
            self.on_update(snap)


class NullProgress(Progress):
    def __init__(self) -> None:
        super().__init__("-")

    def _emit(self) -> None:
        pass
