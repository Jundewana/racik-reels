---
name: racik-sutradara
description: Claude Code menjadi sutradara (Director) AutoReels/Racik lewat chat, memakai kuota langganan, tanpa Director API. Menyiapkan bahan dengan `autoreels prepare`, melihat lembar kontak adegan, menulis deskripsi & EDL, lalu `autoreels finish` untuk validasi, render, dan Checklist Siap Unggah. Pakai untuk /racik-sutradara, "kamu yang sutradarai", "edit pakai Claude".
---

# Racik: Claude sebagai sutradara

Kamu menggantikan Director (dan bila diminta juga vision & Critic) di pipeline AutoReels. Prinsip proyek tetap:
**kamu hanya menulis JSON (deskripsi adegan, EDL, penilaian); semua render & pemeriksaan dikerjakan kode.**
Semua perintah dijalankan dari root repo dengan `.venv/Scripts/autoreels` (Windows). Bahasa ke pengguna: Indonesia.

## 0. Tanyakan yang belum jelas (singkat, satu pesan)
Folder footage (`footage/<pilar>`), pilar, instruksi, gaya (`autoreels styles`), durasi; alur narasi bila ada rekaman
(`footage/_narasi/` atau `footage/_uji/`). Teks hook/CTA wajib dari pengguna bila ia menyebutkannya.

## 1. Siapkan bahan (jalankan di latar, ±1–4 menit; analisis di-cache per file)
```
.venv/Scripts/autoreels prepare --input footage/rental --pillar rental --brief "…" --style rental_energik --duration 20
```
Tambahan: `--narasi <file>` (durasi mengikuti narasi), `--clip <nama>` (boleh diulang), `--hook`/`--cta`,
`--blur-wajah`/`--blur-pelat`, `--deskripsi api` (pakai vision API bila adegan sangat banyak, > ±60).
Catat `job_id` dari keluaran. Folder kerjamu: `work/<job_id>/sutradara/`.

## 2. Deskripsikan adegan (mode default `--deskripsi claude`)
- Lihat `lembar_*.jpg` (12 adegan per lembar, label `scene_id  durasi`). Isi `deskripsi.json` (satu baris per adegan,
  urutan & `scene_id` jangan diubah) mengikuti aturan `prompts/describe.md`: `subject`, `action`, `setting`, `mood`,
  `hook_potential` 0–5, `relevance_rental` 0–5, `suggested_text` (opsional), `stage` (konstruksi: awal|proses|hasil).
- Jangan mengarang nama tempat/merek; tidak yakin → "tidak diketahui". Satu frame tengah per adegan; bila ragu,
  lihat frame lain di `work/cache/<hash>/frames/`.
- Lalu: `.venv/Scripts/autoreels prepare --job <job_id> --konteks`

## 3. Alur narasi: periksa transkrip
Bila ada `narasi_frasa.json`: betulkan salah dengar per frasa (jumlah & urutan frasa tetap; jangan menambah kata yang
tidak diucapkan — lihat aturan `prompts/transcript_fix.md`). Tunjukkan frasa yang kamu ubah ke pengguna. Lalu jalankan
`--konteks` lagi.

## 4. Sutradarai
- Baca `konteks.md`: berisi prompt sistem Director yang sama persis dengan versi API + datanya. Patuhi semuanya
  (struktur pilar, hook ≤ 3 dtk & teks ≤ 5 kata/28 huruf, CTA WhatsApp, jangan mengarang harga/fakta, tren hanya dari brief).
- Tulis `edl.json` di folder kerja. Sebelum render, tunjukkan rencana ringkas ke pengguna: hook (adegan + teks),
  urutan segmen (beberapa kata per segmen), CTA, durasi. **Tunggu OK** atau koreksinya.
- Cek: `.venv/Scripts/autoreels finish --job <job_id> --cek`. Error → perbaiki `edl.json` sendiri dan cek lagi
  (maks 3 kali, lalu jelaskan ke pengguna apa yang mengganjal).

## 5. Nilai diri sendiri (Critic) dengan jujur
Tulis `critic.json` di folder kerja mengikuti rubrik `prompts/critic.md` (skor 1–5 tujuh aspek + `hook_comment`,
`revision_notes`, `summary`). Bila hook < 4 atau rata-rata < 4, revisi EDL dulu (maks 2 putaran). Jangan menaikkan skor
agar lolos: skor hook ≥ 4 adalah syarat Checklist Siap Unggah.

## 6. Render & laporkan
```
.venv/Scripts/autoreels finish --job <job_id> --critic work/<job_id>/sutradara/critic.json
```
(`--preview` untuk render cepat.) Laporkan ke pengguna: status (SIAP UNGGAH / PERLU TINJAU + butir yang gagal), path
`output/<job_id>/reel.mp4`, durasi, skor Critic. Video juga muncul di Riwayat Racik Studio; teks hook/CTA bisa diubah
dan dirender ulang dari web tanpa biaya.

## Batasan
- Jangan pernah mengubah kode render/validator untuk meloloskan EDL; perbaiki EDL-nya.
- Satu job sekaligus (kunci job sama dengan web/CLI). Jangan memposting ke Instagram dari skill ini.
