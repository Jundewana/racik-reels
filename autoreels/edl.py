"""Skema Edit Decision List (EDL) — satu-satunya sumber kebenaran antara LLM dan renderer.

Lihat CLAUDE.md bagian 4.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Pillar(str, Enum):
    rental = "rental"
    konstruksi = "konstruksi"
    profil = "profil"
    lowongan = "lowongan"
    umum = "umum"            # konten di luar unit usaha (klip, podcast, edukasi) — default tanpa CTA


class Purpose(str, Enum):
    promosi = "promosi"      # mengajak booking/konsultasi/menghubungi → CTA + WhatsApp wajib
    informasi = "informasi"  # klip edukasi/kuliah/ucapan/berita → tanpa CTA jualan


class HookType(str, Enum):
    visual_wow = "visual_wow"
    pertanyaan = "pertanyaan"
    harga = "harga"
    before_after = "before_after"
    angka = "angka"
    kontras = "kontras"


class SegmentRole(str, Enum):
    hook = "hook"
    isi = "isi"
    bukti = "bukti"
    suasana = "suasana"
    cta = "cta"


class Reframe(str, Enum):
    subject_track = "subject_track"
    center = "center"
    blur_pad = "blur_pad"


class Transition(str, Enum):
    cut = "cut"
    fade = "fade"
    slide_left = "slide_left"
    zoom_punch = "zoom_punch"
    whip = "whip"


class MusicMood(str, Enum):
    upbeat = "upbeat"
    santai = "santai"
    inspiratif = "inspiratif"
    dramatis = "dramatis"
    none = "none"


class LogoPosition(str, Enum):
    top_left = "top_left"
    top_right = "top_right"
    bottom_left = "bottom_left"
    bottom_right = "bottom_right"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class Hook(_Strict):
    type: HookType
    overlay_text: str | None = None
    source_segment_index: int = Field(0, ge=0)


class Compare(_Strict):
    """Mode before–after: segmen dibuka dengan adegan "sebelum" ini, lalu wipe ke adegan segmen ("sesudah")."""
    source_file: str
    scene_id: str | None = None
    start: float = Field(..., ge=0)
    end: float = Field(..., gt=0)


class Segment(_Strict):
    index: int = Field(..., ge=0)
    source_file: str
    scene_id: str | None = None  # ID adegan dari analysis.json (untuk validasi & jejak)
    start: float = Field(..., ge=0)
    end: float = Field(..., gt=0)
    role: SegmentRole
    reason: str = ""
    reframe: Reframe = Reframe.subject_track
    speed: float = Field(1.0, gt=0, le=16)
    transition_in: Transition = Transition.cut
    overlay_text: str | None = None
    keep_original_audio: bool = False
    compare: Compare | None = None  # before–after (biasanya di segmen hook pilar konstruksi)

    @model_validator(mode="after")
    def _end_after_start(self) -> "Segment":
        if self.end <= self.start:
            raise ValueError(f"segmen {self.index}: end ({self.end}) harus > start ({self.start})")
        return self

    @property
    def output_duration(self) -> float:
        """Durasi segmen di video akhir (setelah speed)."""
        return (self.end - self.start) / self.speed


class Subtitles(_Strict):
    enabled: bool = False
    style: str = "bold_putih_outline"
    language: str = "id"


class Music(_Strict):
    mood: MusicMood = MusicMood.upbeat
    volume_db: float = -14
    duck_under_speech: bool = True
    cut_on_beat: bool = True


class Branding(_Strict):
    logo: bool = True
    position: LogoPosition = LogoPosition.top_right


class Privacy(_Strict):
    blur_faces: bool = False
    blur_plates: bool = False


class CTA(_Strict):
    text: str
    at_sec: float = Field(..., ge=0)


class VoiceOverMode(str, Enum):
    none = "none"        # tanpa voice over
    rekam = "rekam"      # suara manusia (direkam/diunggah pengguna) — pilihan utama
    gemini = "gemini"    # suara AI (Gemini TTS)


class VoiceLine(_Strict):
    at_sec: float = Field(..., ge=0)   # kapan baris mulai diucapkan (detik di video akhir)
    text: str


class VoiceOver(_Strict):
    mode: VoiceOverMode = VoiceOverMode.none
    voice: str = "Puck"                # nama suara Gemini TTS (mode gemini)
    lines: list[VoiceLine] = Field(default_factory=list)
    recording: str | None = None       # file rekaman di output/<job_id>/ (mode rekam)
    offset_sec: float = 0.0            # geser rekaman (+ = mundur) untuk menyamakan dengan video


class NarrationWord(_Strict):
    start: float = Field(..., ge=0)   # detik di narasi bersih (= detik di video akhir)
    end: float = Field(..., ge=0)
    text: str


class Phrase(_Strict):
    start: float = Field(..., ge=0)
    end: float = Field(..., gt=0)
    text: str
    src_start: float | None = None  # video bicara: detik awal frasa di video pembicara asli (sinkron bibir)

    @property
    def duration(self) -> float:
        return self.end - self.start


class Narration(_Strict):
    """Alur "narasi dulu": suara menentukan tempo; segmen i menampilkan b-roll untuk frasa i.
    Diisi kode (bukan LLM) dari transkrip; disimpan di EDL agar render ulang tidak butuh transkripsi lagi."""
    file: str = "narasi.wav"           # narasi bersih (tanpa jeda & kata pengisi) di output/<job_id>/
    source: str = ""                   # file narasi asli
    duration: float = Field(..., gt=0)
    words: list[NarrationWord] = Field(default_factory=list)
    phrases: list[Phrase] = Field(default_factory=list)
    speaker_clip: str | None = None    # video bicara: nama file klip pembicara (segmen dari klip ini dikunci ke src_start)
    cold_open_sec: float = 0.0         # video bicara: detik awal berisi cold open (teaser yang terdengar lagi nanti)


class EDL(_Strict):
    version: str = "1.0"
    pillar: Pillar
    target_duration_sec: float = Field(..., gt=0, le=180)  # Reels IG maks 3 menit
    aspect: str = Field("9:16", pattern=r"^9:16$")
    style_preset: str
    hook: Hook
    segments: list[Segment] = Field(..., min_length=1)
    subtitles: Subtitles = Subtitles()
    music: Music = Music()
    branding: Branding = Branding()
    privacy: Privacy = Privacy()
    purpose: Purpose = Purpose.promosi
    cta: CTA | None = None
    voiceover: VoiceOver = VoiceOver()
    narration: Narration | None = None  # alur "narasi dulu" (None = alur "video dulu" ikut musik)
    caption_suggestion: str = ""
    hashtags: list[str] = Field(default_factory=list)
    notes_for_human: str = ""

    @model_validator(mode="after")
    def _check_consistency(self) -> "EDL":
        indices = [s.index for s in self.segments]
        if indices != list(range(len(self.segments))):
            raise ValueError(f"index segmen harus berurutan 0..n-1, didapat {indices}")
        if self.hook.source_segment_index >= len(self.segments):
            raise ValueError("hook.source_segment_index menunjuk segmen yang tidak ada")
        for tag in self.hashtags:
            if not tag.startswith("#") or " " in tag:
                raise ValueError(f"hashtag tidak valid: {tag!r}")
        return self

    @property
    def total_duration(self) -> float:
        return sum(s.output_duration for s in self.segments)

    # --- I/O -----------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "EDL":
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return p

    @classmethod
    def json_schema_str(cls) -> str:
        """Skema JSON untuk disisipkan ke prompt Director / structured output."""
        return json.dumps(cls.model_json_schema(), ensure_ascii=False, indent=2)
