"""[3] Describe — vision LLM mendeskripsikan adegan layak pakai (batch agar hemat request)."""

from __future__ import annotations

from pathlib import Path

import re

from pydantic import BaseModel, Field, field_validator

from autoreels.analyze.models import Analysis, Scene
from autoreels.config import load_prompt
from autoreels.ingest import CACHE_ROOT
from autoreels.llm import LLMClient, image_to_content, max_images_per_request
from autoreels.media import run_ffmpeg

BATCH_SIZE = 8
FRAME_WIDTH = 640  # ≤ 768 px sesuai aturan hemat biaya


SCENE_ID_RE = re.compile(r"K\d+-\d+")


def normalize_scene_id(value: str) -> str:
    """'ADEGAN K7-4', 'k7-4', 'Adegan: K7-4' → 'K7-4'."""
    m = SCENE_ID_RE.search(str(value).upper())
    return m.group(0) if m else str(value).strip()


class SceneDescription(BaseModel):
    scene_id: str

    @field_validator("scene_id", mode="before")
    @classmethod
    def _norm_id(cls, v: str) -> str:
        return normalize_scene_id(v)

    subject: str = "tidak diketahui"
    action: str = ""
    setting: str = "lainnya"
    mood: str = ""
    hook_potential: int = Field(0, ge=0, le=5)
    relevance_rental: int = Field(0, ge=0, le=5)
    suggested_text: str | None = None
    stage: str | None = None  # konstruksi: awal | proses | hasil (lainnya → None)

    @field_validator("stage", mode="before")
    @classmethod
    def _norm_stage(cls, v):
        s = str(v or "").strip().lower()
        for key, words in {"awal": ("awal", "sebelum", "before", "kosong"),
                           "proses": ("proses", "pengerjaan", "progress", "konstruksi"),
                           "hasil": ("hasil", "selesai", "jadi", "after", "akhir")}.items():
            if any(w in s for w in words):
                return key
        return None


class DescriptionBatch(BaseModel):
    scenes: list[SceneDescription]


def _frame_times(scene: Scene) -> list[float]:
    d = scene.duration
    if d < 2.0:
        return [scene.start + d / 2]
    if d < 5.0:
        return [scene.start + d * 0.3, scene.start + d * 0.7]
    return [scene.start + d * 0.15, scene.start + d * 0.5, scene.start + d * 0.85]


def extract_frames(scene: Scene, clip_hash: str, proxy: Path) -> list[Path]:
    out_dir = CACHE_ROOT / clip_hash / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for t in _frame_times(scene):
        f = out_dir / f"{t:08.2f}.jpg"
        if not f.exists():
            run_ffmpeg(["-ss", f"{t:.3f}", "-i", str(proxy), "-frames:v", "1",
                        "-vf", f"scale={FRAME_WIDTH}:-2", "-q:v", "5", str(f)])
        frames.append(f)
    return frames


def describe_scenes(analysis: Analysis, llm: LLMClient, model: str, log=print,
                    progress=None, skip_clips: set[str] | None = None) -> dict[str, SceneDescription]:
    """skip_clips: klip yang tidak perlu dideskripsikan (mis. video pembicara: gambarnya terkunci ke ucapan)."""
    system = load_prompt("describe")
    usable = [s for s in analysis.usable_scenes() if s.source_file not in (skip_clips or set())]
    if not usable:
        return {}
    all_frames = {}
    for scene in usable:
        clip = analysis.clip(scene.source_file)
        all_frames[scene.scene_id] = extract_frames(scene, clip.hash, CACHE_ROOT / clip.hash / "proxy.mp4")

    def make_batches(scenes: list[Scene], for_model: str) -> list[list[tuple[Scene, list[Path]]]]:
        """Bagi adegan ke batch sesuai batas gambar per request model tersebut."""
        max_imgs = max_images_per_request(for_model)
        batches: list[list[tuple[Scene, list[Path]]]] = [[]]
        img_count = 0
        for scene in scenes:
            frames = all_frames[scene.scene_id]
            if max_imgs < 8:  # provider ketat → 1 frame tengah per adegan
                frames = [frames[len(frames) // 2]]
            if batches[-1] and (len(batches[-1]) >= BATCH_SIZE or img_count + len(frames) > max_imgs):
                batches.append([])
                img_count = 0
            batches[-1].append((scene, frames))
            img_count += len(frames)
        return [b for b in batches if b]

    def ask(batch: list[tuple[Scene, list[Path]]], for_model: str) -> DescriptionBatch:
        content: list[dict] = [{"type": "text", "text": f"Ada {len(batch)} adegan. Deskripsikan semuanya."}]
        for scene, frames in batch:
            content.append({"type": "text", "text": f"ADEGAN {scene.scene_id} (durasi {scene.duration:.1f} dtk):"})
            content.extend(image_to_content(f) for f in frames)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]
        return llm.complete_structured(messages, DescriptionBatch, model=for_model, purpose="describe",
                                       allow_fallback=False)

    chain = [model, *llm.fallback_chain(model)]
    current = 0  # model yang sedang dipakai; setelah gagal, batch berikutnya langsung memakai cadangan yang jalan
    results: dict[str, SceneDescription] = {}
    done = 0
    for batch in make_batches(usable, model):
        log(f"  deskripsi adegan {done + 1}–{done + len(batch)} dari {len(usable)} …")
        if progress:
            progress.update(done, len(usable), f"adegan {done + 1}–{done + len(batch)} dari {len(usable)}")
        done += len(batch)
        while True:
            m = chain[current]
            try:
                parsed_list = [ask(sub, m) for sub in make_batches([s for s, _ in batch], m)]
                break
            except (RuntimeError, ValueError) as e:
                if current + 1 >= len(chain):
                    raise
                current += 1
                log(f"  [cadangan] {m} gagal ({str(e)[:80]}…) → {chain[current]}")
        for parsed in parsed_list:
            for d in parsed.scenes:
                results[d.scene_id] = d
    missing = [s.scene_id for s in usable if s.scene_id not in results]
    for sid in missing:
        results[sid] = SceneDescription(scene_id=sid)
    if missing:
        log(f"  [peringatan] {len(missing)} adegan tidak dideskripsikan: {', '.join(missing)}")
    return results
