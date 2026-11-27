# ADR-009: Blur privasi dengan YuNet (OpenCV), bukan mediapipe

## Status
Diterima (2026-11-20, Tahap 2)

## Konteks
Prinsip 6 mewajibkan opsi blur wajah pelanggan dan pelat nomor. CLAUDE.md semula menyebut `mediapipe` untuk deteksi
wajah. `mediapipe` belum terpasang dan bergantung pada `opencv-contrib-python`, yang rawan bentrok dengan
`opencv-python-headless` yang sudah dipakai proyek (keduanya menyediakan modul `cv2`). Untuk pelat nomor tidak ada
detektor di `mediapipe`. Pemilik juga ingin sebagian video tetap menampilkan wajah (staf, testimoni berizin).

## Keputusan
- Deteksi wajah memakai **YuNet** lewat `cv2.FaceDetectorYN` (OpenCV 5.1 yang sudah terpasang); deteksi pelat
  memakai **LPD-YuNet** lewat `cv2.dnn`. Model ONNX (0,2 MB + 4 MB) disimpan di `assets/models/` (MIT / Apache 2.0).
- Blur dijalankan pada video gabungan 1080×1920 **sebelum** teks & logo ditempel (`render/privacy.py`).
- **Pilihan manusia, default mati**, terpisah untuk wajah dan pelat (web: langkah Atur; CLI: `--blur-wajah`,
  `--blur-pelat`). LLM tidak memutuskan privasi.
- Hasil dicatat di checklist sebagai butir tidak wajib ("periksa manual"), karena deteksi bisa terlewat.

## Konsekuensi
### Positif
- Tanpa paket Python baru dan tanpa GPU; satu versi OpenCV untuk semua.
- Wajah bisa tetap tampil bila memang diinginkan.
### Negatif
- Model pelat dilatih pada pelat Tiongkok: pelat Indonesia kecil/miring bisa terlewat (uji: pelat "AB …" terdeteksi).
- Menambah ±1,3× durasi video ke waktu render saat aktif (uji: 29 dtk untuk video 22 dtk).
- Saat transisi fade, bayangan gambar sebelumnya yang memudar bisa masih menampilkan pelat samar.

## Alternatif yang dipertimbangkan
- **mediapipe**: sesuai rencana awal, tetapi konflik paket `cv2` dan tidak punya detektor pelat.
- **Haar cascade bawaan OpenCV**: tanpa unduhan, tetapi lemah untuk wajah miring/kecil dan banyak salah deteksi.
- **Blur manual (pengguna menandai area)**: paling akurat, tetapi butuh UI penyuntingan per frame — di luar Tahap 2.
