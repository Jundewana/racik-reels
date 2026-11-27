# Racik Animasi (Remotion)

Video animasi 2D flat penuh (tanpa footage) untuk Reels Brand. Claude Code menulis kode animasi per video
(skill `.claude/skills/racik-animasi/`), kode merender dan memeriksa. Tanpa API LLM.

```
footage/_uji/voice.m4a ──autoreels animasi prepare──► public/<nama>/data.json (+ narasi.wav, musik, _brand/)
Claude menulis src/videos/<nama>/Video.tsx ──autoreels animasi stills──► work/_animasi/<nama>/lembar_stills.jpg
caption.json (ditulis Claude) ──autoreels animasi render──► output/<job>/reel.mp4 + caption.txt + checklist
```

- `src/kit/` — gaya khas **Racik Flat**: garis tinta tebal, bayangan keras ala stiker, gerak memantul, sapuan pita
  miring, judul kinetik per kata. Komponen: panggung, teks, stiker, ikon, motor + pengendara, pemandangan, peta, CTA.
- `src/videos/` — satu folder per video, didaftarkan di `src/videos/index.ts`.
- `public/` — diisi otomatis oleh `prepare`, tidak di-commit.

Pratinjau interaktif: `npm run studio` (di folder ini). Cek tipe: `npm run typecheck`.
Pasang ulang dependensi: `npm install`.

## Lisensi Remotion
Remotion gratis untuk perorangan dan perusahaan dengan ≤ 3 karyawan. Pemakaian untuk perusahaan yang lebih besar
(Contoh Brand) butuh **Company License** (paket *Creators* ±$25/bulan per orang) — lihat
https://remotion.dev/docs/license. Untuk riset/uji coba pribadi pemilik proyek, versi gratis berlaku.
