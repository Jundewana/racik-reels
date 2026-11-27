# ADR-002: LLM hanya menulis EDL JSON; FFmpeg yang mengeksekusi

## Status
Diterima

## Konteks
LLM pandai memilih adegan, menyusun alur, dan menulis teks, tetapi tidak bisa diandalkan untuk menghasilkan
perintah render yang tepat (timestamp, filter, ukuran). Hasil wajib benar-benar siap unggah dan harus bisa diulang
tanpa biaya AI ketika manusia hanya mengubah teks.

## Keputusan
Director (LLM) menghasilkan **Edit Decision List** berformat JSON yang skemanya didefinisikan sekali sebagai model
pydantic di `autoreels/edl.py` (satu-satunya sumber kebenaran). Renderer deterministik (`render/*`, FFmpeg) hanya
membaca EDL. `edl.json` disimpan bersama hasil sehingga `autoreels render --edl …` dan tombol "Render ulang" di web
tidak memanggil LLM.

## Konsekuensi
### Positif
- Hasil bisa diulang & diaudit; manusia bisa mengedit EDL.
- Ganti model/provider LLM tidak menyentuh renderer.
- Biaya AI hanya sekali per video; edit teks gratis.
### Negatif
- Setiap fitur render baru butuh perubahan skema EDL + renderer + prompt Director.
- LLM bisa menghasilkan EDL yang valid secara skema tetapi buruk secara isi (ditangani ADR-003 & Critic).
### Netral
- Skema EDL menjadi dokumen kontrak yang harus dijaga kompatibilitasnya (`version`).

## Alternatif yang dipertimbangkan
- **LLM menulis perintah FFmpeg langsung**: fleksibel tetapi rapuh, sulit divalidasi, berbahaya (eksekusi perintah).
- **Model video end-to-end (generatif)**: butuh GPU besar, hasil sulit dikendalikan, melanggar prinsip biaya.
