"""Evaluasi set uji -> eval/report.md (Tahap 4). Sama dengan `autoreels eval`; argumen diteruskan.

Contoh:
  python eval/run_eval.py                       # rangkum semua job di output/ (tanpa biaya AI)
  python eval/run_eval.py --sejak 2026-11-20
  python eval/run_eval.py --jalankan --engine api --engine local --bandingkan-critic
"""

import sys

from autoreels.cli import app

if __name__ == "__main__":
    sys.argv = ["autoreels", "eval", *sys.argv[1:]]
    app()
