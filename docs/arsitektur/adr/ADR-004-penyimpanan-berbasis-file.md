# ADR-004: Penyimpanan berbasis file, tanpa database

## Status
Diterima

## Konteks
Data sistem: footage mentah (besar), cache analisis & LLM, hasil per job (video, EDL, caption, laporan), dan
konfigurasi yang diedit pengguna (brand, hook, tren). Satu pengguna, satu proses, tanpa query kompleks.

## Keputusan
Semua disimpan sebagai file: `footage/` (input), `work/` (cache per hash file & per job, `progress.json`),
`output/<job_id>/` (hasil), `config/*.yaml`, `prompts/*.md`, `trends/brief.md`, `assets/`. Cache LLM berkunci hash
prompt + gambar. Penyunting konfigurasi menjaga komentar YAML (`config_editor.py`).

## Konsekuensi
### Positif
- Mudah dibaca, dicadangkan, dipindah ke laptop lain, dan diedit manual.
- Render ulang hanya butuh `output/<job>/` (EDL + job.json).
### Negatif
- Tidak ada transaksi/locking; aman hanya karena satu worker (ADR-005).
- Riwayat dibaca dengan memindai folder (`/api/jobs` membatasi 100 terbaru).
- `work/` bisa membesar tanpa batas (risiko R9 di README).

## Alternatif yang dipertimbangkan
- **SQLite**: transaksi & query, tetapi belum ada kebutuhan relasi; menambah migrasi skema.
- **Penyimpanan cloud**: biaya & unggah footage besar; bertentangan dengan ADR-001.
