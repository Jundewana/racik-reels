# ADR-007: Frontend React; hasil build di-commit dan disajikan FastAPI

## Status
Diterima (menggantikan rencana Gradio di Tahap 5)

## Konteks
Antarmuka butuh interaksi kaya: wizard 4 langkah, preview footage & video hasil, strip struktur video, perekam voice
over, pengaturan bahan AI, dan tampilan HP. Pengguna akhir tidak boleh harus memasang Node.js.

## Keputusan
Frontend ditulis dengan React + Vite + Tailwind di `frontend/` (dipecah per halaman, state di `state/studio.jsx`).
Hasil build `frontend/dist/` ikut di-commit dan disajikan `server.py` sebagai file statis. Bila `dist/` tidak ada,
server memakai versi cadangan tanpa build di `ui/` (Alpine.js). Mode `?mock=1` menjalankan UI dengan data simulasi.

## Konsekuensi
### Positif
- Tampilan bebas didesain; satu port untuk API & UI.
- Pengguna cukup Python; Node hanya untuk yang mengubah tampilan.
### Negatif
- `dist/` harus dibuild ulang & di-commit setiap perubahan UI (mudah lupa).
- Frontend baru bisa berjalan dengan backend lama bila server tidak di-restart (risiko R2).
- Dua UI (React & `ui/` cadangan) bisa tidak sinkron fitur.

## Alternatif yang dipertimbangkan
- **Gradio**: cepat dibuat, tetapi tata letak & interaksi terbatas.
- **Server-side templates (Jinja)**: tanpa build, tetapi interaksi (preview, perekam) jadi rumit.
