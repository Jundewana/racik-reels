"""[2] Analyze — adegan, kualitas, subjek (crop), dan musik."""

from __future__ import annotations

import json

from autoreels.analyze.models import Analysis, ClipInfo, Scene
from autoreels.ingest import SourceClip

ANALYSIS_VERSION = "4"  # 2: jalur crop (Scene.crop_path); 3: batas geser crop; 4: skor momen (moment_curve)


def analyze_clip(clip: SourceClip) -> list[Scene]:
    """Analisis satu klip (di-cache per hash file)."""
    from autoreels.analyze.quality import sample_clip, score_scene
    from autoreels.analyze.scenes import detect_scenes

    cache = clip.cache_dir / f"scenes_v{ANALYSIS_VERSION}.json"
    if cache.exists():
        scenes = [Scene(**s) for s in json.loads(cache.read_text(encoding="utf-8"))]
        return [s.model_copy(update={"source_file": clip.name}) for s in scenes]

    ranges = detect_scenes(clip.proxy, clip.info.duration)
    samples, _ = sample_clip(clip.proxy)
    scenes = []
    for i, (start, end) in enumerate(ranges):
        base = Scene(scene_id=f"{clip.hash[:6]}_{i:02d}", source_file=clip.name, start=start, end=end)
        scenes.append(score_scene(base, samples))
    cache.write_text(json.dumps([s.model_dump() for s in scenes], indent=1), encoding="utf-8")
    return scenes


def analyze_clips(clips: list[SourceClip], log=print, progress=None) -> Analysis:
    infos, scenes = [], []
    for idx, clip in enumerate(clips):
        if progress:
            progress.update(idx, len(clips) + 1, f"klip {idx + 1}/{len(clips)}: {clip.name}")
        clip_scenes = analyze_clip(clip)
        # ID adegan pendek & mudah dibaca LLM: K<klip>-<n>
        for n, s in enumerate(clip_scenes):
            s.scene_id = f"K{idx + 1}-{n + 1}"
        bad = sum(not s.usable for s in clip_scenes)
        log(f"  {clip.name}: {len(clip_scenes)} adegan, {bad} tidak layak")
        scenes.extend(clip_scenes)
        infos.append(ClipInfo(
            name=clip.name, path=str(clip.path), hash=clip.hash, duration=clip.info.duration,
            width=clip.info.display_width, height=clip.info.display_height,
            fps=clip.info.fps, has_audio=clip.info.has_audio,
        ))
    return Analysis(clips=infos, scenes=scenes)
