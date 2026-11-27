# ADR-001: Monolit modular yang berjalan lokal di laptop

## Status
Diterima (2026-11-19, dicatat 2026-11-20)

## Konteks
Pengguna adalah 1–2 admin media sosial Brand di Garut dengan satu laptop. Prinsip proyek: modal minim, tanpa
server cloud, data footage pelanggan tidak perlu keluar dari laptop kecuali frame kecil untuk LLM. Beban kerja:
beberapa video per hari, satu job berjalan sekaligus, tiap job butuh menit (render FFmpeg + LLM).

## Keputusan
Satu paket Python (`autoreels/`) dengan modul terpisah per tanggung jawab (ingest, analyze, describe, director,
validate, render, checklist, importer, server). Semua berjalan dalam satu proses di laptop; antarmuka web disajikan
oleh proses yang sama di `127.0.0.1`.

## Konsekuensi
### Positif
- Tanpa biaya hosting; mudah dipasang (`pip install`, `python main.py --web`).
- Modul bisa dites dan dijalankan terpisah lewat CLI (`autoreels analyze`, `render --edl`).
- Footage mentah tetap di laptop.
### Negatif
- Hanya tersedia selama laptop menyala; tidak bisa diakses dari luar jaringan rumah/kantor.
- Skala terbatas pada satu mesin (memang cukup untuk kebutuhan ini).
### Netral
- Bila kelak perlu dipakai banyak orang, batas modul yang jelas memudahkan pemisahan (mis. render jadi worker).

## Alternatif yang dipertimbangkan
- **Layanan cloud (VPS + antrean + worker)**: bisa diakses di mana saja, tapi biaya bulanan, unggah footage besar,
  dan operasional server tidak sebanding untuk 1–2 pengguna.
- **Microservices**: kompleksitas jaringan & deployment tanpa manfaat pada skala satu laptop.
