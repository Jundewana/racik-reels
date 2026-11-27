"""Kunci job bersama (CLI & server web) — mencegah dua job berat berjalan bersamaan di satu laptop.

File `work/.job.lock` berisi PID, label, dan waktu mulai. Kunci milik proses yang sudah mati dianggap basi dan
diambil alih. Satu proses (server) boleh memegang kunci untuk satu job sekaligus (JobRunner 1 worker).
"""

from __future__ import annotations

import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from autoreels.config import PATHS

LOCK_FILE = PATHS["work"] / ".job.lock"


class JobBusyError(RuntimeError):
    """Job lain sedang berjalan (dari proses lain)."""

    def __init__(self, holder: dict):
        self.holder = holder
        super().__init__(describe(holder))


def describe(holder: dict) -> str:
    started = holder.get("started")
    since = f", sejak {time.strftime('%H:%M', time.localtime(started))}" if started else ""
    return f"Job lain sedang berjalan: {holder.get('label', '?')} (PID {holder.get('pid')}{since})."


def pid_alive(pid: int) -> bool:
    """Apakah proses dengan PID ini masih hidup (tanpa mengirim sinyal apa pun)."""
    if not pid or pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return bool(ok) and code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # POSIX: sinyal 0 hanya memeriksa keberadaan
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_holder(lock_file: Path = LOCK_FILE) -> dict | None:
    """Pemegang kunci yang masih hidup, atau None (kunci basi dihapus)."""
    try:
        holder = json.loads(lock_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        holder = {}
    if pid_alive(int(holder.get("pid", 0) or 0)):
        return holder
    try:
        lock_file.unlink()
    except FileNotFoundError:
        pass
    return None


def try_acquire(label: str, job_id: str | None = None, lock_file: Path = LOCK_FILE) -> bool:
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if read_holder(lock_file) is not None:
                return False
            continue  # kunci basi sudah dihapus → coba lagi
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "label": label, "job_id": job_id, "started": time.time()}, f)
        return True
    return False


def release(lock_file: Path = LOCK_FILE) -> None:
    holder = None
    try:
        holder = json.loads(lock_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    if holder and holder.get("pid") == os.getpid():
        try:
            lock_file.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def job_lock(label: str, job_id: str | None = None, *, wait: bool = False, on_wait=None,
             poll_sec: float = 3.0, lock_file: Path = LOCK_FILE):
    """Pegang kunci selama blok berjalan. wait=False → JobBusyError bila terkunci;
    wait=True → tunggu (memanggil on_wait(holder) tiap poll) sampai kunci lepas."""
    while not try_acquire(label, job_id, lock_file):
        holder = read_holder(lock_file) or {}
        if not wait:
            raise JobBusyError(holder)
        if on_wait:
            on_wait(holder)
        time.sleep(poll_sec)
    try:
        yield
    finally:
        release(lock_file)
