# ADR-005: Antrean job dalam proses dengan 1 worker

## Status
Diterima — risiko R1 & R3 ditangani 2026-11-20 (penanda job tertinggal, kunci `work/.job.lock`)

## Konteks
Render FFmpeg dan model lokal memakai CPU/GPU penuh; dua job bersamaan di satu laptop justru lebih lambat dan
berisiko kehabisan VRAM/RAM. Web harus tetap responsif dan menampilkan progres selama job berjalan.

## Keputusan
`server.py` memakai `JobRunner` dengan `ThreadPoolExecutor(max_workers=1)`. Job baru masuk antrean; progres ditulis
ke `work/<job>/progress.json` dan dibaca UI tiap detik (polling). Log job juga ditulis ke `work/<job>/log.txt`.

## Konsekuensi
### Positif
- Sederhana, tanpa broker (Redis/Celery); progres tahan terhadap refresh browser.
- Sumber daya laptop tidak diperebutkan oleh job web.
### Negatif
- **Antrean hanya di memori**: bila server dimatikan, job yang antri hilang dan job berjalan meninggalkan
  `progress.json` berstatus "berjalan" (R1).
- **CLI tidak lewat antrean**: `autoreels run` dari terminal bisa berjalan bersamaan dengan job web (R3).
### Netral
- Polling 1 dtk cukup untuk satu pengguna; WebSocket tidak diperlukan.

## Alternatif yang dipertimbangkan
- **Celery/RQ + Redis**: antrean tahan restart, tetapi menambah layanan yang harus dipasang & dijalankan di Windows.
- **Proses terpisah per job**: isolasi lebih baik, tetapi koordinasi sumber daya tetap perlu kunci.

## Usulan lanjutan
Kunci file bersama (`work/.job.lock`) untuk CLI & server, dan penandaan job "terhenti" saat server mulai.
