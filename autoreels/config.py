"""Pemuatan konfigurasi: .env, path proyek, dan file YAML di config/."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

PATHS = {
    "config": ROOT / "config",
    "styles": ROOT / "config" / "styles",
    "prompts": ROOT / "prompts",
    "trends": ROOT / "trends",
    "assets": ROOT / "assets",
    "music": ROOT / "assets" / "music",
    "fonts": ROOT / "assets" / "fonts",
    "logo": ROOT / "assets" / "logo",
    "work": ROOT / "work",
    "output": ROOT / "output",
}


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    llm_model: str
    vision_model: str
    ffmpeg_bin: str
    llm_fallback: str = ""
    vision_fallback: str = ""
    tts_model: str = "gemini-3.8-flash-lite-tts"
    tts_fallback: str = "gemini-2.5-flash-preview-tts"
    # Model lokal via Ollama (opsional, untuk uji coba di laptop ber-GPU; API tetap default)
    local_llm_model: str = "ollama/qwen3:4b"
    local_vision_model: str = "ollama/qwen3-vl:4b-instruct"
    ollama_api_base: str = "http://127.0.0.1:11434"
    local_num_ctx: int = 8192
    transcribe_model: str = "small"  # faster-whisper (CPU, int8)

    def models_for(self, engine: str) -> tuple[str, str]:
        """(model teks Director/caption, model vision Describe) untuk mesin 'api' atau 'local'."""
        if engine == "local":
            return self.local_llm_model, self.local_vision_model
        return self.llm_model, self.vision_model


ENGINES = ("api", "local")


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "gemini"),
        llm_model=os.getenv("LLM_MODEL", "gemini/gemini-3.1-flash-lite"),
        vision_model=os.getenv("VISION_MODEL", "gemini/gemini-3.1-flash-lite"),
        ffmpeg_bin=os.getenv("FFMPEG_BIN", "ffmpeg"),
        llm_fallback=os.getenv("LLM_FALLBACK_MODEL", ""),
        vision_fallback=os.getenv("VISION_FALLBACK_MODEL", ""),
        tts_model=os.getenv("TTS_MODEL", "gemini-3.8-flash-lite-tts"),
        tts_fallback=os.getenv("TTS_FALLBACK_MODEL", "gemini-2.5-flash-preview-tts"),
        local_llm_model=os.getenv("LOCAL_LLM_MODEL", "ollama/qwen3:4b"),
        local_vision_model=os.getenv("LOCAL_VISION_MODEL", "ollama/qwen3-vl:4b-instruct"),
        ollama_api_base=os.getenv("OLLAMA_API_BASE", "http://127.0.0.1:11434").rstrip("/"),
        local_num_ctx=int(os.getenv("LOCAL_NUM_CTX", "8192")),
        transcribe_model=os.getenv("TRANSCRIBE_MODEL", "small"),
    )


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_brand() -> dict[str, Any]:
    return load_yaml(PATHS["config"] / "brand.yaml")


def load_pillars() -> dict[str, Any]:
    return load_yaml(PATHS["config"] / "pillars.yaml")


def load_hooks() -> dict[str, Any]:
    return load_yaml(PATHS["config"] / "hooks.yaml")


def load_style(name: str) -> dict[str, Any]:
    path = PATHS["styles"] / f"{name}.yaml"
    if not path.exists():
        available = ", ".join(list_styles())
        raise FileNotFoundError(f"Style preset '{name}' tidak ditemukan. Tersedia: {available}")
    return load_yaml(path)


def list_styles() -> list[str]:
    return sorted(p.stem for p in PATHS["styles"].glob("*.yaml"))


def load_prompt(name: str) -> str:
    """Baca prompt dari prompts/<name>.md (mis. 'director' atau 'pillars/rental')."""
    return (PATHS["prompts"] / f"{name}.md").read_text(encoding="utf-8")


def load_trend_brief() -> str:
    path = PATHS["trends"] / "brief.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""
