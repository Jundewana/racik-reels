"""Agen Antigravity + Remotion: cadangan untuk Claude Code (`claude -p`) saat langganan Claude mencapai batas.

Menjalankan loop agentic tool-calling lewat `litellm` (Gemini / model multimodal yang dikonfigurasi di `.env`),
menggunakan tool yang sama amannya dengan daftar `allowedTools` Claude Code, serta memancarkan event Ruang Kerja
(`start`, `text`, `read`, `write`, `edit`, `bash`, `plan`, `frame`, `end`) agar UI live tetap bekerja identik.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

import litellm

from autoreels.config import ROOT, get_settings
from autoreels.llm import image_to_content

MAX_TURNS = 40
MAX_READ_CHARS = 32000
MAX_CMD_CHARS = 8000
ALLOWED_ANIMASI_SUBCMDS = {"cek", "stills", "render", "gaya", "musik"}

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Baca file teks di dalam repository (kode, skill, config, data.json, adegan.txt).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relatif terhadap root repo."},
                    "start_line": {"type": "integer", "description": "Baris awal (1-indexed, opsional)."},
                    "end_line": {"type": "integer", "description": "Baris akhir (inklusif, opsional)."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_image",
            "description": "Lihat file gambar (mis. work/_animasi/<nama>/lembar_kontak_1.jpg atau lembar_stills.jpg).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path gambar relatif terhadap root repo."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Tulis atau timpa file milik video ini (Video.tsx, index.ts, musik.json, caption.json, atau komponen di kit/).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relatif terhadap root repo."},
                    "content": {"type": "string", "description": "Isi file lengkap."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Ubah sebagian teks dalam file yang sudah ada (penggantian persis).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relatif terhadap root repo."},
                    "old_string": {"type": "string", "description": "Teks lama persis yang akan diganti."},
                    "new_string": {"type": "string", "description": "Teks pengganti."},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Daftar file/folder di dalam direktori repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Direktori relatif terhadap root repo (default '.')."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_animasi_cmd",
            "description": "Jalankan subperintah `autoreels animasi` (hanya: cek, stills, render, gaya, musik).",
            "parameters": {
                "type": "object",
                "properties": {
                    "args": {
                        "type": "string",
                        "description": "Argumen setelah `autoreels animasi`, mis. `cek`, `stills -n nama`, atau `render -n nama`.",
                    },
                },
                "required": ["args"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_write",
            "description": "Perbarui daftar rencana langkah kerja yang tampil di Ruang Kerja.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                            },
                            "required": ["content", "status"],
                        },
                    },
                },
                "required": ["todos"],
            },
        },
    },
]


def _resolve_repo_path(rel_path: str) -> Path:
    p = (ROOT / rel_path.lstrip("/\\")).resolve()
    root_res = ROOT.resolve()
    if p != root_res and root_res not in p.parents:
        raise ValueError(f"Path di luar repository tidak diizinkan: {rel_path}")
    return p


def is_writable_path(nama: str, rel_path: str) -> bool:
    """Batasi penulisan hanya ke folder video ini, index.ts, kit/, dan work/_animasi/<nama>/."""
    p = _resolve_repo_path(rel_path)
    allowed_dirs = [
        (ROOT / "animasi" / "src" / "videos" / nama).resolve(),
        (ROOT / "animasi" / "src" / "kit").resolve(),
        (ROOT / "animasi" / "src" / "kit3d").resolve(),
        (ROOT / "work" / "_animasi" / nama).resolve(),
    ]
    allowed_files = {
        (ROOT / "animasi" / "src" / "videos" / "index.ts").resolve(),
        (ROOT / "animasi" / "public" / nama / "data.json").resolve(),
    }
    if p in allowed_files:
        return True
    return any(d == p or d in p.parents for d in allowed_dirs)


def _autoreels_exe() -> str:
    win = ROOT / ".venv" / "Scripts" / "autoreels.exe"
    if win.exists():
        return str(win)
    nix = ROOT / ".venv" / "bin" / "autoreels"
    if nix.exists():
        return str(nix)
    return "autoreels"


def _pick_models() -> list[str]:
    settings = get_settings()
    primary = (
        os.getenv("ANTIGRAVITY_MODEL", "").strip()
        or settings.vision_model
        or settings.llm_model
    )
    candidates = [primary]
    for raw in (settings.vision_fallback, settings.llm_fallback, "gemini/gemini-2.5-flash"):
        for fb in (raw or "").split(","):
            fb = fb.strip()
            if fb and fb not in candidates:
                candidates.append(fb)
    return candidates


def _is_transient_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        k in msg
        for k in ("503", "429", "unavailable", "high demand", "rate limit", "overloaded", "timeout", "temporarily")
    )


def _sleep_cancelable(seconds: float, cancel_event: threading.Event | None) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if cancel_event and cancel_event.is_set():
            return False
        time.sleep(min(0.5, max(0.05, deadline - time.time())))
    return True


def _completion_with_retry(
    models: list[str],
    messages: list[dict[str, Any]],
    *,
    on_text: Callable[[str], None],
    cancel_event: threading.Event | None = None,
) -> Any:
    delays = (3, 6, 12, 20)
    last_exc: Exception | None = None
    for idx, model in enumerate(models):
        for attempt in range(len(delays) + 1):
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Dihentikan pengguna.")
            try:
                return litellm.completion(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.3,
                )
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if not _is_transient_error(exc):
                    if idx + 1 < len(models):
                        on_text(f"[cadangan] {model} gagal ({type(exc).__name__}), beralih ke {models[idx + 1]}…")
                        break
                    raise
                if attempt < len(delays):
                    wait_s = delays[attempt]
                    on_text(f"[menunggu] {model} sedang sibuk, mencoba lagi dalam {wait_s} dtk…")
                    if not _sleep_cancelable(wait_s, cancel_event):
                        raise RuntimeError("Dihentikan pengguna.") from exc
                elif idx + 1 < len(models):
                    on_text(f"[cadangan] Beralih dari {model} ke {models[idx + 1]}…")
    assert last_exc is not None
    raise last_exc


def _exec_tool(
    nama: str,
    name: str,
    args: dict[str, Any],
    *,
    cancel_event: threading.Event | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Jalankan satu tool; kembalikan (teks_hasil, lampiran_gambar_opsional)."""
    if name == "read_file":
        p = _resolve_repo_path(str(args.get("path", "")))
        if not p.is_file():
            return f"Error: file tidak ditemukan: {args.get('path')}", []
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(1, int(args.get("start_line") or 1))
        end = min(len(lines), int(args.get("end_line") or len(lines)))
        numbered = [f"{i}: {lines[i - 1]}" for i in range(start, end + 1)]
        text = "\n".join(numbered)
        if len(text) > MAX_READ_CHARS:
            text = text[:MAX_READ_CHARS] + "\n... [terpotong]"
        return text, []

    if name == "read_image":
        p = _resolve_repo_path(str(args.get("path", "")))
        if not p.is_file():
            return f"Error: gambar tidak ditemukan: {args.get('path')}", []
        return f"Gambar {args.get('path')} dilampirkan untuk diperiksa.", [image_to_content(p)]

    if name == "write_file":
        rel = str(args.get("path", ""))
        if not is_writable_path(nama, rel):
            return f"Error: path tidak diizinkan untuk ditulis: {rel}", []
        p = _resolve_repo_path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(str(args.get("content", "")), encoding="utf-8")
        return f"OK: {rel} ditulis.", []

    if name == "edit_file":
        rel = str(args.get("path", ""))
        if not is_writable_path(nama, rel):
            return f"Error: path tidak diizinkan untuk diubah: {rel}", []
        p = _resolve_repo_path(rel)
        if not p.is_file():
            return f"Error: file tidak ditemukan: {rel}", []
        src = p.read_text(encoding="utf-8")
        old = str(args.get("old_string", ""))
        new = str(args.get("new_string", ""))
        if not old or old not in src:
            return f"Error: old_string tidak ditemukan di {rel}.", []
        p.write_text(src.replace(old, new, 1), encoding="utf-8")
        return f"OK: {rel} diubah.", []

    if name == "list_files":
        d = _resolve_repo_path(str(args.get("directory") or "."))
        if not d.is_dir():
            return f"Error: direktori tidak ditemukan: {args.get('directory')}", []
        entries = []
        for item in sorted(d.iterdir()):
            if item.name in (".git", ".venv", "node_modules", "__pycache__"):
                continue
            entries.append(item.name + ("/" if item.is_dir() else ""))
        return "\n".join(entries[:200]) or "(kosong)", []

    if name == "run_animasi_cmd":
        raw_args = str(args.get("args", "")).strip().split()
        if not raw_args or raw_args[0] not in ALLOWED_ANIMASI_SUBCMDS:
            return (
                f"Error: hanya subperintah {sorted(ALLOWED_ANIMASI_SUBCMDS)} yang diizinkan.",
                [],
            )
        cmd = [_autoreels_exe(), "animasi", *raw_args]
        proc = subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        out_chunks: list[str] = []
        while True:
            if cancel_event and cancel_event.is_set():
                proc.kill()
                return "Error: dibatalkan pengguna.", []
            line = proc.stdout.readline() if proc.stdout else ""
            if not line and proc.poll() is not None:
                break
            if line:
                out_chunks.append(line)
        rc = proc.wait()
        out = "".join(out_chunks)[-MAX_CMD_CHARS:]
        return f"Exit code: {rc}\n{out}", []

    if name == "todo_write":
        return "OK: daftar rencana diperbarui.", []

    return f"Error: tool tidak dikenal: {name}", []


def _to_block_event_payload(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Petakan pemanggilan tool Antigravity ke format blok tool_use Claude agar Ruang Kerja tetap kompatibel."""
    if name == "read_file":
        return {"name": "Read", "input": {"file_path": args.get("path", "")}}
    if name == "read_image":
        return {"name": "Read", "input": {"file_path": args.get("path", "")}}
    if name == "write_file":
        return {"name": "Write", "input": {"file_path": args.get("path", ""), "content": args.get("content", "")}}
    if name == "edit_file":
        return {
            "name": "Edit",
            "input": {
                "file_path": args.get("path", ""),
                "old_string": args.get("old_string", ""),
                "new_string": args.get("new_string", ""),
            },
        }
    if name == "todo_write":
        return {"name": "TodoWrite", "input": {"todos": args.get("todos", [])}}
    if name == "run_animasi_cmd":
        return {"name": "Bash", "input": {"command": f"autoreels animasi {args.get('args', '')}"}}
    return {"name": name, "input": args}


def run_remotion_agent(
    nama: str,
    prompt: str,
    *,
    on_text: Callable[[str], None],
    on_tool: Callable[[dict[str, Any]], None],
    on_frame: Callable[[], None],
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Jalankan loop Antigravity Remotion hingga selesai atau dibatalkan."""
    models = _pick_models()
    system_msg = (
        "Kamu adalah agen Antigravity Remotion di dalam AutoReels. "
        "Tugasmu membaca skill yang diminta, memeriksa data & lembar kontak/stills dengan tool `read_file` dan `read_image`, "
        "menulis kode Remotion TypeScript yang rapi dan lolos `autoreels animasi cek`, `stills`, dan `render`. "
        "Selalu panggil tool secara bertahap dan jangan berhenti sebelum `autoreels animasi render -n " + nama + "` berhasil."
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]

    total_cost = 0.0
    final_text = ""

    for _turn in range(MAX_TURNS):
        if cancel_event and cancel_event.is_set():
            return {"ok": False, "cancelled": True, "result": "Dihentikan pengguna.", "cost": total_cost}

        resp = _completion_with_retry(
            models,
            messages,
            on_text=on_text,
            cancel_event=cancel_event,
        )
        try:
            total_cost += float(litellm.completion_cost(completion_response=resp) or 0.0)
        except Exception:  # noqa: BLE001
            pass

        msg = resp.choices[0].message
        content = (getattr(msg, "content", None) or "").strip()
        if content:
            final_text = content
            on_text(content)

        tool_calls = getattr(msg, "tool_calls", None) or []
        assistant_entry: dict[str, Any] = {"role": "assistant", "content": content or ""}
        if tool_calls:
            assistant_entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ]
        messages.append(assistant_entry)

        if not tool_calls:
            return {"ok": True, "cancelled": False, "result": final_text, "cost": total_cost}

        pending_images: list[dict[str, Any]] = []
        for tc in tool_calls:
            if cancel_event and cancel_event.is_set():
                return {"ok": False, "cancelled": True, "result": "Dihentikan pengguna.", "cost": total_cost}
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                fn_args = {}

            on_tool(_to_block_event_payload(fn_name, fn_args))
            result_text, imgs = _exec_tool(nama, fn_name, fn_args, cancel_event=cancel_event)
            if fn_name == "run_animasi_cmd" and "stills" in str(fn_args.get("args", "")):
                on_frame()
            if imgs:
                pending_images.extend(imgs)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_text})

        if pending_images:
            messages.append(
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "Berikut gambar yang kamu minta:"}, *pending_images],
                }
            )
        time.sleep(0.05)

    return {
        "ok": False,
        "cancelled": False,
        "result": f"Batas langkah ({MAX_TURNS}) tercapai sebelum selesai.",
        "cost": total_cost,
    }
