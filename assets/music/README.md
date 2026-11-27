# Cara menaruh musik

Taruh file musik **bebas royalti** ke folder sesuai **suasananya (mood)**:

```
assets/music/
├── upbeat/       ← semangat, cepat, ceria      → promo rental motor, lowongan
├── santai/       ← tenang, chill, akustik      → perjalanan wisata, pemandangan
├── inspiratif/   ← membangun, sinematik, haru  → progres proyek konstruksi, profil
└── dramatis/     ← tegang, epik, bass berat    → before–after, reveal hasil
```

## Aturan singkat

1. **Format:** `.mp3`, `.wav`, atau `.m4a`. Durasi minimal ±30 detik.
2. **Nama file:** huruf kecil, tanpa spasi, beri tahu tempo bila tahu.
   Contoh: `upbeat/energi-pagi_120bpm.mp3`, `santai/angin-gunung.mp3`.
3. **Satu lagu, satu folder.** Kalau lagu cocok untuk dua mood, pilih yang paling dominan.
4. **Jangan** pakai lagu berhak cipta (lagu artis, rekaman dari YouTube/TikTok). Sumber aman:
   YouTube Audio Library, Pixabay Music, Uppbeat, Mixkit, Free Music Archive (cek lisensi tiap lagu).
5. Catat sumber & lisensi di `assets/music/LISENSI.md` (judul — sumber — jenis lisensi), untuk jaga-jaga bila ada klaim hak cipta.

## Bagaimana sistem memakainya

- Director memilih `music.mood` di EDL (default dari style preset, mis. `rental_energik` → `upbeat`).
- Sistem mengambil lagu dari folder mood itu, mendeteksi beat-nya otomatis, lalu memotong video **mengikuti beat**.
- Tidak perlu memotong atau mengedit lagunya sendiri.
- Musik trending Instagram tidak bisa dimasukkan dari sini. Kalau ingin memakainya, tambahkan manual di aplikasi Instagram saat unggah.
