"""Model data hasil analisis (disimpan ke work/<job_id>/analysis.json)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scene(BaseModel):
    scene_id: str
    source_file: str
    start: float
    end: float
    sharpness: float = 0.0       # variance of Laplacian (proxy 480p)
    brightness: float = 0.0      # rata-rata luminance 0–255
    shake: float = 0.0           # jitter gerak kamera (px, makin besar makin goyang)
    motion: float = 0.0          # rata-rata gerak global (px per sampel)
    usable: bool = True
    reasons: list[str] = Field(default_factory=list)
    crop_cx_start: float = 0.5   # pusat crop 9:16 (0–1 relatif lebar) di awal adegan
    crop_cx_end: float = 0.5     # ... di akhir adegan
    crop_path: list[list[float]] = Field(default_factory=list)  # [[detik, cx], …] 5/dtk, dihaluskan (pengikut subjek)
    moment_curve: list[list[float]] = Field(default_factory=list)  # [[detik, skor 0–1], …] (analyze/moments.py)

    @property
    def duration(self) -> float:
        return self.end - self.start


class ClipInfo(BaseModel):
    name: str
    path: str
    hash: str
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool


class MusicInfo(BaseModel):
    path: str
    mood: str
    tempo: float
    duration: float
    start_offset: float                     # detik di lagu tempat Reel dimulai
    beats: list[float] = Field(default_factory=list)  # waktu beat relatif terhadap start_offset

    @property
    def beat_interval(self) -> float:
        return 60.0 / self.tempo if self.tempo else 0.5


class Analysis(BaseModel):
    clips: list[ClipInfo]
    scenes: list[Scene]
    music: MusicInfo | None = None

    def clip(self, name: str) -> ClipInfo | None:
        return next((c for c in self.clips if c.name == name), None)

    def usable_scenes(self) -> list[Scene]:
        return [s for s in self.scenes if s.usable]
