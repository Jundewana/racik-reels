# Riset: mesin AI lokal (Ollama) vs API — 2026-11-20

Tujuan: menilai apakah model lokal di laptop (RTX 4050 Laptop 6 GB) bisa menggantikan API saat kuota habis.
Satu kali percobaan per konfigurasi (bukan statistik), footage & pengaturan sama.

## Pengaturan
- Footage: `footage/rental`, 6 klip, 23 adegan (22 layak pakai)
- Perintah: `autoreels run --pillar rental --style rental_energik --duration 20 --preview --engine <api|local>`
- Instruksi: "Promo sewa motor untuk wisatawan yang mau keliling Garut"
- Ollama 0.40.16, `LOCAL_NUM_CTX=8192`, model Q4_K_M

| Run | Director (teks) | Vision (Describe) |
|---|---|---|
| A | `qwen3:8b` (lokal) | `qwen3-vl:4b-instruct` (lokal) |
| B | `qwen3:4b` (lokal) | `qwen3-vl:4b-instruct` (lokal, **hasil cache dari A**) |
| C | `groq/openai/gpt-oss-120b` (API) | `gemini/gemini-3.1-flash-lite` (API) |

## Hasil

| | A — lokal 8B | B — lokal 4B | C — API |
|---|---|---|---|
| Selesai? | **Gagal**: panggilan Director > 15 mnt (timeout) | Ya | Ya |
| Describe (22 adegan) | ±205 dtk (6 batch × ±37 dtk) | (cache) | 62 dtk |
| Director + validasi | > 900 dtk | 120 dtk (2 panggilan × ±60 dtk) | 14 dtk |
| Revisi Director | — | 1 (hook 6 kata/34 huruf) | 0 |
| Perbaikan otomatis validator | — | 14 segmen dipangkas ke tempo gaya, 1 dibuang | 9 segmen diperpanjang, 6 ditambah, 1 dibuang |
| Total waktu | — | 150 dtk (+±205 dtk bila Describe tidak di-cache) | 110 dtk |
| Biaya | $0 | $0 | $0,0205 |
| Status checklist | — | **Siap unggah** | Perlu tinjau (audio *true peak* −0,6 dBTP; lihat catatan) |
| Hook | — | "Garut naik motor" — adegan hook 4/5 | "Keliling Garut pakai motor" — adegan hook 5/5 |

Hasil video: `output/20261120-103527-rental` (B) dan `output/20261120-103759-rental` (C).

## Temuan
1. **`qwen3:8b` tidak praktis di VRAM 6 GB.** Bobot 5,2 GB + konteks 8k = 6,6 GB; hanya ±4,2 GB masuk GPU, sisanya CPU
   (±9 token/dtk). EDL ±2.000 token → satu panggilan bisa > 15 mnt. *Catatan keadilan*: selama Run A laptop juga
   menjalankan server web dan browser headless untuk pengujian UI, jadi CPU ikut terbebani.
2. **`qwen3:4b` muat penuh di GPU** (±35 token/dtk) dan menghasilkan video yang lolos checklist.
3. **Vision lokal harus varian `-instruct`.** Tag polos `qwen3-vl:4b` adalah varian *thinking*: lambat (47 dtk/gambar)
   dan jawaban kosong bila mode berpikir dimatikan. `qwen3-vl:4b-instruct`: ±37 dtk per 4 adegan, deskripsi masuk akal.
4. **Model lokal mengabaikan tempo gaya** (segmen 4–5 dtk untuk gaya 0,6–1,2 dtk) — validator memperbaikinya.
   Model API justru membuat segmen terlalu pendek. Keduanya bergantung pada validator (ADR-003), jadi validator
   adalah komponen yang membuat mesin lokal layak dipakai.
5. **Pilihan hook API sedikit lebih baik** (adegan berpotensi hook tertinggi). Caption kedua mesin memakai layanan
   rental terkonfirmasi dari `brand.yaml`; caption lokal memulai kalimat dengan huruf kecil.
6. **Temuan di luar riset**: Run C gagal checklist karena *true peak* audio −0,6 dBTP (batas −1 dBTP) pada lagu
   `mixkit-gimme-that-groove-872.mp3`. Ini masalah tahap mix/loudnorm, bukan mesin AI.
   **Sudah diperbaiki (2026-11-20)**: true-peak limiter oversampling di PCM sebelum encoding AAC + pengaman
   akhir yang meng-encode ulang dari PCM. Render ulang Run C: −14,9 LUFS, −1,4 dBTP → siap unggah.
   (Catatan: meng-encode ulang AAC dari AAC justru menaikkan puncak lagi, −0,6 → +0,1 dBTP.)

## Kesimpulan & rekomendasi
- Untuk uji coba lokal di laptop ini (**sudah jadi default**): **`LOCAL_LLM_MODEL=ollama/qwen3:4b`** + **`LOCAL_VISION_MODEL=ollama/qwen3-vl:4b-instruct`**.
  Perkiraan ±6 mnt per video (vs ±2 mnt API), tanpa biaya, kualitas sedikit di bawah API.
- API tetap default untuk produksi; mesin lokal cocok sebagai cadangan saat kuota habis.
- Langkah riset berikutnya: ulangi beberapa kali per konfigurasi pada pilar lain (konstruksi, lowongan) dan nilai
  dengan rubrik `eval/rubric.md` agar tidak bergantung pada satu percobaan.
