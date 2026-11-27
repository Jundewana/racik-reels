# ADR-003: Validator aturan keras + loop revisi, bukan percaya LLM

## Status
Diterima

## Konteks
Aturan "siap unggah" bersifat pasti: hook ≤ 3 dtk, durasi ±10%, adegan `unusable` dilarang, potongan di ketukan,
teks maksimal 5 kata/28 huruf, tanpa placeholder `[HARGA]`. LLM (terutama model kecil/lokal) sering melanggar
sebagian aturan ini.

## Keputusan
`validate.py` memeriksa EDL dengan kode biasa. Pelanggaran yang aman diperbaiki otomatis (mis. snap ke beat,
pangkas hook, isi CTA default) dan dicatat sebagai `fixes`; pelanggaran yang butuh penilaian dikembalikan ke Director
sebagai pesan error untuk direvisi, maksimal 2 putaran. Setelah render, `checklist.py` memeriksa hasil video nyata
(resolusi, durasi, loudness, teks). Gagal → status `perlu_tinjau` dengan alasan, tidak pernah diam-diam lolos.

## Konsekuensi
### Positif
- Kualitas minimum terjamin terlepas dari model LLM yang dipakai (penting untuk mesin lokal).
- Alasan kegagalan jelas untuk manusia.
### Negatif
- Aturan harus dirawat di dua tempat (prompt & validator) agar LLM tahu batasnya.
- Revisi menambah waktu & biaya (dibatasi 2 putaran).

## Alternatif yang dipertimbangkan
- **Percaya keluaran LLM**: cepat tetapi melanggar prinsip "hasil wajib benar-benar jadi".
- **LLM kedua sebagai satu-satunya penjaga**: penilaian subjektif tetap berguna (Critic, Tahap 4), tetapi aturan pasti
  lebih murah & andal bila ditulis sebagai kode.
