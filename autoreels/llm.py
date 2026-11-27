"""Wrapper LLM via litellm: retry, cache berbasis hash, dan pencatat biaya per job.

Semua panggilan LLM di proyek ini WAJIB lewat modul ini.
Model `ollama/<nama>` (opsional, uji coba lokal di GPU) dipanggil langsung ke API Ollama — bukan lewat
litellm — agar mode berpikir Qwen3 bisa dimatikan, skema JSON dikirim, dan `num_ctx` diatur.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from autoreels.config import PATHS, get_settings

T = TypeVar("T", bound=BaseModel)

CACHE_DIR = PATHS["work"] / "_llm_cache"
PATIENCE_SEC = 900  # total waktu menunggu saat rate limit / server sibuk sebelum menyerah
FALLBACK_PATIENCE_SEC = 60  # bila masih ada model cadangan: tunggu sebentar saja, lalu pindah
DAILY_LIMIT_HINTS = ("per day", "perday", "daily", "requestsperday", "tokens per day", "tpd", "rpd")


@dataclass
class UsageRecord:
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    cached: bool
    purpose: str


@dataclass
class CostTracker:
    """Mengumpulkan token & estimasi biaya untuk ditulis ke report.md."""

    records: list[UsageRecord] = field(default_factory=list)

    def add(self, rec: UsageRecord) -> None:
        self.records.append(rec)

    @property
    def total_cost(self) -> float:
        return sum(r.cost_usd for r in self.records)

    def summary_markdown(self) -> str:
        lines = [
            "| Tujuan | Model | Token in | Token out | Cache | Biaya (USD) |",
            "|---|---|---|---|---|---|",
        ]
        for r in self.records:
            lines.append(
                f"| {r.purpose} | {r.model} | {r.prompt_tokens} | {r.completion_tokens} "
                f"| {'ya' if r.cached else 'tidak'} | {r.cost_usd:.5f} |"
            )
        lines.append(f"\n**Total estimasi biaya:** ${self.total_cost:.4f}")
        return "\n".join(lines)


def _hash_request(model: str, messages: list[dict[str, Any]], extra: dict[str, Any]) -> str:
    payload = json.dumps({"model": model, "messages": messages, "extra": extra}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def image_to_content(path: str | Path) -> dict[str, Any]:
    """Ubah file gambar (sudah diperkecil <=768 px) menjadi blok konten vision."""
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    suffix = Path(path).suffix.lower().lstrip(".") or "jpeg"
    mime = "jpeg" if suffix == "jpg" else suffix
    return {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{data}"}}


class LLMClient:
    def __init__(self, tracker: CostTracker | None = None, use_cache: bool = True, log=print) -> None:
        self.log = log  # pesan [menunggu]/[cadangan] ikut ke log job (terminal maupun web)
        self.settings = get_settings()
        self.fallback_enabled = True  # False: uji model tertentu tanpa cadangan (evaluasi antar-model)
        self.tracker = tracker or CostTracker()
        self.use_cache = use_cache
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        purpose: str = "llm",
        json_mode: bool = False,
        temperature: float = 0.4,
        max_retries: int = 3,
        allow_fallback: bool = True,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        """Panggil LLM (cache + retry); bila model utama gagal/overload, coba model cadangan dari .env.
        json_schema hanya dipakai model lokal (Ollama structured outputs)."""
        model = model or self.settings.llm_model
        chain = [model, *(self.fallback_chain(model) if allow_fallback and self.fallback_enabled else [])]
        for i, m in enumerate(chain):
            last = i == len(chain) - 1
            try:
                return self._complete_one(messages, model=m, purpose=purpose if i == 0 else f"{purpose} (cadangan)",
                                          json_mode=json_mode, temperature=temperature, max_retries=max_retries,
                                          json_schema=json_schema,
                                          patience=PATIENCE_SEC if last else FALLBACK_PATIENCE_SEC)
            except RuntimeError as e:
                if last:
                    raise
                self.log(f"  [cadangan] {m} gagal ({str(e)[:90]}…) → mencoba {chain[i + 1]}")
        raise RuntimeError("rantai model kosong")  # tidak terjangkau

    def synthesize_speech(self, text: str, *, voice: str = "Puck", style: str = "",
                          purpose: str = "tts") -> Path:
        """Teks → file WAV (Gemini TTS). Di-cache per (model, suara, gaya, teks); model cadangan bila gagal.

        PENTING: jangan beri instruksi gaya dalam teks (mis. "Ucapkan dengan ramah: …") — terbukti ikut
        DIBACAKAN oleh TTS (diuji 2026-11-19 dengan transkripsi). Karakter suara diatur lewat `voice`."""
        import httpx

        models = [m for m in (self.settings.tts_model, self.settings.tts_fallback) if m]
        tts_dir = CACHE_DIR / "tts"
        tts_dir.mkdir(parents=True, exist_ok=True)
        last_err = ""
        for model in models:
            key = hashlib.sha256(json.dumps([model, voice, style, text]).encode("utf-8")).hexdigest()[:32]
            out = tts_dir / f"{key}.wav"
            if self.use_cache and out.exists():
                self.tracker.add(UsageRecord(model, 0, 0, 0.0, True, purpose))
                return out
            body = {"contents": [{"parts": [{"text": f"{style}: {text}" if style else text}]}],
                    "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {
                        "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            waited, attempt = 0.0, 0
            r = None
            while True:
                try:
                    r = httpx.post(url, headers={"x-goog-api-key": _api_key_for("gemini/x") or ""},
                                   json=body, timeout=120)
                except httpx.HTTPError as e:
                    last_err = f"{type(e).__name__}: {e}"
                    break
                if r.status_code == 200:
                    break
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                # Kuota HARIAN habis (mis. free tier 10 permintaan/hari) → percuma menunggu, langsung ke cadangan.
                delay = re.search(r'"retryDelay":\s*"(\d+)', r.text)
                if r.status_code == 429 and ("PerDay" in r.text or "per day" in r.text
                                             or (delay and int(delay.group(1)) > 120)):
                    self.log(f"  [kuota] TTS {model}: kuota harian habis → pakai model cadangan")
                    break
                if r.status_code in (429, 500, 503) and waited < PATIENCE_SEC:
                    wait = min(60, 10 * 2 ** min(attempt, 3))
                    self.log(f"  [menunggu] TTS {model} sibuk/limit — coba lagi dalam {wait} dtk")
                    time.sleep(wait)
                    waited += wait
                    attempt += 1
                    continue
                break
            if r is None or r.status_code != 200:
                self.log(f"  [cadangan] TTS {model} gagal ({last_err[:80]})")
                continue
            data = r.json()
            try:
                inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
            except (KeyError, IndexError):
                last_err = f"respons TTS tanpa audio: {str(data)[:200]}"
                continue
            raw = base64.b64decode(inline["data"])
            mime = inline.get("mimeType", "")
            if raw[:4] == b"RIFF":  # sudah WAV utuh (model 3.x)
                out.write_bytes(raw)
            else:  # PCM mentah, mis. audio/L16;codec=pcm;rate=24000 (model 2.5)
                import wave

                m = re.search(r"rate=(\d+)", mime)
                with wave.open(str(out), "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(int(m.group(1)) if m else 24000)
                    w.writeframes(raw)
            usage = data.get("usageMetadata", {})
            self.tracker.add(UsageRecord(model, usage.get("promptTokenCount", 0) or 0,
                                         usage.get("candidatesTokenCount", 0) or 0, 0.0, False, purpose))
            return out
        raise RuntimeError(f"Suara AI (Gemini TTS) gagal dibuat: {last_err}")

    def fallback_for(self, model: str) -> str:
        """Cadangan pertama (kompatibel lama)."""
        chain = self.fallback_chain(model)
        return chain[0] if chain else ""

    def fallback_chain(self, model: str) -> list[str]:
        """Model cadangan berurutan dari .env (LLM_FALLBACK_MODEL / VISION_FALLBACK_MODEL, dipisah koma).
        Hanya untuk model API utama: mesin lokal tidak pernah diam-diam pindah ke API."""
        for primary, raw in ((self.settings.llm_model, self.settings.llm_fallback),
                             (self.settings.vision_model, self.settings.vision_fallback)):
            chain = [primary, *(x.strip() for x in raw.split(",") if x.strip())]
            if model in chain:  # model utama, atau salah satu cadangan → sisa rantai sesudahnya
                rest = chain[chain.index(model) + 1:] if model != primary else chain[1:]
                out = []
                for m in rest:
                    if m != model and m not in out:
                        out.append(m)
                return out
        return []

    def _complete_one(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        purpose: str,
        json_mode: bool,
        temperature: float,
        max_retries: int,
        json_schema: dict[str, Any] | None = None,
        patience: float = 0.0,
    ) -> str:
        local = is_local_model(model)
        extra: dict[str, Any] = {"json_mode": json_mode, "temperature": temperature}
        if local:  # hanya untuk model lokal, agar cache model API lama tetap berlaku
            extra.update(json_schema=json_schema, num_ctx=self.settings.local_num_ctx)
        key = _hash_request(model, messages, extra)
        cache_file = CACHE_DIR / f"{key}.json"

        if self.use_cache and cache_file.exists():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            self.tracker.add(UsageRecord(model, 0, 0, 0.0, True, purpose))
            return cached["content"]

        if local:
            content, p_tok, c_tok = self._ollama_chat(messages, model=model, json_mode=json_mode,
                                                      json_schema=json_schema, temperature=temperature)
            self.tracker.add(UsageRecord(model, p_tok, c_tok, 0.0, False, purpose))
            if self.use_cache:
                cache_file.write_text(json.dumps({"content": content}, ensure_ascii=False), encoding="utf-8")
            return content

        import litellm  # impor lambat agar CLI tetap cepat

        kwargs: dict[str, Any] = {"model": model, "messages": messages, "timeout": 120}
        gateway = model.split("/", 1)[0]
        if gateway in OPENAI_COMPAT_BASES:  # litellm memanggilnya lewat provider "openai" + api_base gerbang
            kwargs.update(model="openai/" + model.split("/", 1)[1], api_base=OPENAI_COMPAT_BASES[gateway])
        if not _is_gemini3(model):  # Gemini 3+: temperature akan dihapus, pakai default model
            kwargs["temperature"] = temperature
        api_key = _api_key_for(model)
        if api_key:
            # Kirim eksplisit: mencegah variabel sistem lain (mis. GOOGLE_API_KEY lama) dipakai litellm.
            kwargs["api_key"] = api_key
        if json_mode and not model.startswith(("cohere/", "cohere_chat/")):
            kwargs["response_format"] = {"type": "json_object"}

        litellm.suppress_debug_info = True
        last_err: Exception | None = None
        resp = None
        attempt = 0
        waited = 0.0
        while True:
            try:
                resp = litellm.completion(**kwargs)
                break
            except Exception as e:  # noqa: BLE001 — error jaringan/rate limit dari provider
                last_err = e
                msg = str(e).lower()
                if any(k in msg for k in ("api key", "api_key", "permission", "not found", "invalid_argument",
                                          "timeout", "timed out", "too many images", "request too large",
                                          "insufficient balance", "unsupportedparams", "credit",
                                          "payment card")):
                    break  # error konfigurasi / request terlalu besar: percuma diulang
                transient = any(k in msg for k in ("rate", "429", "quota", "exhausted", "503",
                                                   "high demand", "overloaded", "unavailable"))
                if transient and any(h in msg.replace(" ", "") or h in msg for h in DAILY_LIMIT_HINTS) \
                        and patience < PATIENCE_SEC:
                    break  # jatah HARIAN habis: menunggu percuma, langsung ke model cadangan
                if transient and waited < (patience or PATIENCE_SEC):
                    # rate limit / server sibuk: tunggu dengan sabar lalu coba lagi
                    wait = min(60, 10 * 2 ** min(attempt, 3))
                    self.log(f"  [menunggu] {model} sedang sibuk/terkena limit — coba lagi dalam {wait} dtk "
                          f"(sudah menunggu {waited:.0f}/{patience or PATIENCE_SEC:.0f} dtk)")
                    time.sleep(wait)
                    waited += wait
                    attempt += 1
                    continue
                if not transient and attempt < max_retries - 1:
                    time.sleep(3 * (attempt + 1))
                    attempt += 1
                    continue
                break
        if resp is None:
            raise RuntimeError(f"Panggilan LLM ke '{model}' gagal: {last_err}")

        content = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        try:
            cost = float(litellm.completion_cost(completion_response=resp))
        except Exception:  # noqa: BLE001 — model tanpa tabel harga
            cost = 0.0
        if not cost and model in PRICE_PER_M and usage is not None:
            pin, pout = PRICE_PER_M[model]
            cost = ((getattr(usage, 'prompt_tokens', 0) or 0) * pin
                    + (getattr(usage, 'completion_tokens', 0) or 0) * pout) / 1e6
        self.tracker.add(
            UsageRecord(
                model=model,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                cost_usd=cost,
                cached=False,
                purpose=purpose,
            )
        )
        if self.use_cache:
            cache_file.write_text(json.dumps({"content": content}, ensure_ascii=False), encoding="utf-8")
        return content

    def _ollama_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        json_mode: bool,
        json_schema: dict[str, Any] | None,
        temperature: float,
    ) -> tuple[str, int, int]:
        """Satu panggilan ke Ollama (/api/chat). Kembalikan (konten, token prompt, token keluaran)."""
        import httpx

        name = model.split("/", 1)[1]
        body: dict[str, Any] = {
            "model": name,
            "messages": ollama_messages(messages),
            "stream": False,
            "think": False,  # Qwen3: matikan mode berpikir agar JSON langsung keluar & cepat
            "keep_alive": "10m",
            "options": {"temperature": temperature, "num_ctx": self.settings.local_num_ctx},
        }
        if json_mode:
            body["format"] = json_schema or "json"
        url = f"{self.settings.ollama_api_base}/api/chat"
        t0 = time.perf_counter()
        retried = False
        for _ in range(4):  # penyesuaian otomatis bila versi Ollama/model menolak opsi tertentu
            try:
                r = httpx.post(url, json=body, timeout=900)
            except httpx.ConnectError as e:
                raise RuntimeError(
                    f"Ollama tidak berjalan di {self.settings.ollama_api_base}. Buka aplikasi Ollama dulu."
                ) from e
            except httpx.HTTPError as e:
                raise RuntimeError(f"Panggilan ke Ollama ({name}) gagal: {type(e).__name__}: {e}") from e
            if r.status_code == 200:
                break
            err = r.text[:300]
            low = err.lower()
            if r.status_code == 404 or "not found" in low:
                raise RuntimeError(f"Model lokal '{name}' belum diunduh. Jalankan: ollama pull {name}")
            if "think" in low and "think" in body:  # model tanpa mode berpikir
                body.pop("think")
                continue
            if isinstance(body.get("format"), dict) and any(k in low for k in ("format", "schema", "grammar")):
                self.log(f"  [lokal] skema JSON ditolak Ollama ({err[:80]}); pakai mode JSON biasa")
                body["format"] = "json"
                continue
            if r.status_code >= 500 and not retried:  # mis. model sedang dimuat/ditukar: coba sekali lagi
                retried = True
                self.log(f"  [lokal] Ollama sibuk (HTTP {r.status_code}: {err[:80]}); coba lagi dalam 5 dtk")
                time.sleep(5)
                continue
            raise RuntimeError(f"Ollama ({name}) menolak permintaan: HTTP {r.status_code} {err}")
        else:
            raise RuntimeError(f"Ollama ({name}) menolak permintaan: HTTP {r.status_code} {r.text[:300]}")
        data = r.json()
        msg = data.get("message") or {}
        content = msg.get("content") or ""
        if not content.strip() and msg.get("thinking") and "think" in body:
            # Varian "thinking" (mis. qwen3-vl:4b) mengabaikan think:false: semua token habis untuk berpikir
            # dan jawabannya kosong. Ulangi tanpa opsi itu; model berpikir dulu lalu menjawab.
            self.log(f"  [lokal] {name} adalah varian 'thinking' (jawaban kosong); ulangi dengan mode berpikir. "
                     f"Lebih cepat: pakai tag '-instruct' (mis. {name.split(':')[0]}:{name.split(':')[-1]}-instruct)")
            body.pop("think")
            r = httpx.post(url, json=body, timeout=900)
            if r.status_code != 200:
                raise RuntimeError(f"Ollama ({name}) menolak permintaan: HTTP {r.status_code} {r.text[:300]}")
            data = r.json()
            content = (data.get("message") or {}).get("content") or ""
        p_tok = int(data.get("prompt_eval_count") or 0)
        c_tok = int(data.get("eval_count") or 0)
        if not content.strip():
            raise RuntimeError(f"Model lokal {name} tidak mengembalikan jawaban ({c_tok} token keluar, "
                               f"done_reason={data.get('done_reason')}). Coba LOCAL_NUM_CTX lebih besar.")
        self.log(f"  [lokal] {name}: {time.perf_counter() - t0:.1f} dtk, {p_tok} token masuk, {c_tok} token keluar")
        if p_tok >= self.settings.local_num_ctx - 64:
            self.log(f"  [lokal] peringatan: prompt ({p_tok} token) menyentuh batas konteks "
                     f"LOCAL_NUM_CTX={self.settings.local_num_ctx}; sebagian prompt bisa terpotong.")
        return content, p_tok, c_tok

    def complete_structured(
        self,
        messages: list[dict[str, Any]],
        schema: type[T],
        *,
        model: str | None = None,
        purpose: str = "llm",
        max_attempts: int = 3,
        allow_fallback: bool = True,
    ) -> T:
        """Minta JSON, validasi dengan pydantic, retry dengan pesan error dimasukkan ke prompt."""
        msgs = list(messages)
        last_err = ""
        model = model or self.settings.llm_model
        json_schema = schema.model_json_schema() if is_local_model(model) else None
        for _ in range(max_attempts):
            raw = self.complete(msgs, model=model, purpose=purpose, json_mode=True, allow_fallback=allow_fallback,
                                json_schema=json_schema)
            try:
                return schema.model_validate_json(strip_code_fence(raw))
            except ValidationError as e:
                last_err = str(e)
                msgs = msgs + [
                    {"role": "assistant", "content": raw},
                    {
                        "role": "user",
                        "content": "JSON tidak valid terhadap skema. Perbaiki error berikut dan "
                        f"kirim ulang JSON lengkap saja:\n{last_err}",
                    },
                ]
        raise ValueError(f"Output LLM tetap tidak valid setelah {max_attempts} percobaan:\n{last_err}")


def strip_code_fence(text: str) -> str:
    """Ambil JSON dari respons: buang blok <think>, pembungkus ```json, dan teks di luar objek."""
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    t = t.strip()
    if "{" in t:  # ambil objek JSON pertama yang utuh; teks/penjelasan sesudahnya dibuang (mis. Cohere)
        start = t.index("{")
        try:
            _, end = json.JSONDecoder().raw_decode(t[start:])
            return t[start:start + end]
        except ValueError:
            if not t.startswith("{") and "}" in t:
                t = t[start: t.rindex("}") + 1]
    return t


_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "cohere": "COHERE_API_KEY",
    "cohere_chat": "COHERE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "runcrate": "RUN_CRATE_API_KEY",
    "aionlabs": "AIONLABS_API_KEY",
}

# Gerbang OpenAI-compatible: model ditulis "<gerbang>/<id katalog>", mis. "runcrate/openai/gpt-oss-120b"
OPENAI_COMPAT_BASES = {"runcrate": "https://api.runcrate.ai/v1", "aionlabs": "https://api.aionlabs.ai/v1"}
# Harga per 1 juta token (input, output) untuk model yang tidak dikenal tabel harga litellm
PRICE_PER_M = {
    "aionlabs/aion-labs/aion-2.0": (0.80, 1.60), "aionlabs/aion-labs/aion-3.0": (3.00, 6.00),
    "aionlabs/aion-labs/aion-3.0-mini": (0.70, 1.40), "aionlabs/aion-labs/aion-3.5": (3.00, 6.00),
    "aionlabs/aion-labs/aion-3.5-mini": (0.70, 1.40), "aionlabs/aion-labs/aion-rp-llama-3.1-8b": (0.80, 1.60),
}


def _api_key_for(model: str) -> str | None:
    import os

    get_settings()  # memastikan .env sudah dimuat
    env = _KEY_ENV.get(model.split("/", 1)[0])
    return (os.environ.get(env) or None) if env else None


def _is_gemini3(model: str) -> bool:
    name = model.split("/", 1)[-1]
    return name.startswith("gemini-") and (name.split("-")[1][:1].isdigit() and int(name.split("-")[1][0]) >= 3
                                           or "latest" in name)


def max_images_per_request(model: str) -> int:
    """Batas gambar per request per provider (Groq qwen: maks 3; lokal: VRAM & konteks terbatas)."""
    if model.startswith("groq/"):
        return 3
    if is_local_model(model):
        return 4
    return 24


# ---------------------------------------------------------------------------
# Model lokal (Ollama)
# ---------------------------------------------------------------------------
def is_local_model(model: str | None) -> bool:
    return bool(model) and model.startswith(("ollama/", "ollama_chat/"))


def ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format pesan OpenAI/litellm → format Ollama.

    Ollama menaruh gambar di field `images` per pesan (urutannya hilang dari teks), jadi tiap gambar diganti
    penanda "[gambar #n]" di teks agar model tahu gambar mana milik adegan mana."""
    out = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            out.append({"role": m["role"], "content": content})
            continue
        texts, images = [], []
        for part in content or []:
            if part.get("type") == "text":
                texts.append(part.get("text", ""))
            elif part.get("type") == "image_url":
                url = (part.get("image_url") or {}).get("url", "")
                images.append(_shrink_b64(url.split(",", 1)[1] if url.startswith("data:") else url))
                texts.append(f"[gambar #{len(images)}]")
        msg: dict[str, Any] = {"role": m["role"], "content": "\n".join(texts)}
        if images:
            msg["images"] = images
        out.append(msg)
    return out


# Perkecil frame sebelum dikirim ke Ollama (hemat transfer & memori). Catatan (diuji 2026-11-20): qwen3-vl di
# Ollama tetap memakai ±1000 token per gambar berapa pun ukurannya, jadi batas gambar per request tetap kecil.
LOCAL_IMAGE_MAX_SIDE = 512


def _shrink_b64(b64: str, max_side: int = LOCAL_IMAGE_MAX_SIDE) -> str:
    """Perkecil gambar base64 untuk model lokal; kembalikan apa adanya bila gagal/sudah kecil."""
    try:
        import cv2
        import numpy as np

        img = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_COLOR)
        if img is None or max(img.shape[:2]) <= max_side:
            return b64
        scale = max_side / max(img.shape[:2])
        small = cv2.resize(img, (round(img.shape[1] * scale), round(img.shape[0] * scale)), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buf.tobytes()).decode("ascii") if ok else b64
    except Exception:  # noqa: BLE001 — perkecil hanya penghematan; jangan gagalkan permintaan
        return b64


def ollama_status(timeout: float = 1.5) -> dict[str, Any]:
    """Apakah Ollama berjalan & model lokal di .env sudah diunduh (untuk pilihan mesin di web)."""
    import httpx

    s = get_settings()
    wanted = {"llm": s.local_llm_model, "vision": s.local_vision_model}
    try:
        r = httpx.get(f"{s.ollama_api_base}/api/tags", timeout=timeout)
        r.raise_for_status()
        installed = {m.get("name", "") for m in r.json().get("models", [])}
    except Exception:  # noqa: BLE001 — Ollama mati/tidak terpasang
        return {"running": False, "installed": [], "models": wanted, "missing": [],
                "reason": f"Ollama tidak berjalan di {s.ollama_api_base}. Buka aplikasi Ollama."}

    def have(model: str) -> bool:
        name = model.split("/", 1)[1]
        return name in installed or (":" not in name and f"{name}:latest" in installed)

    missing = [m.split("/", 1)[1] for m in wanted.values() if not have(m)]
    return {"running": True, "installed": sorted(installed), "models": wanted, "missing": missing,
            "reason": f"Belum diunduh: {', '.join(missing)}. Jalankan: ollama pull <nama>" if missing else ""}
