---
name: racik-animasi
description: Claude Code membuat video animasi 2D flat penuh (tanpa footage) untuk Reels Brand dengan Remotion — Claude menulis naskah, kode animasi per video, dan caption sendiri; render & checklist oleh kode, TANPA API LLM (Gemini/Groq). Pakai untuk /racik-animasi, "bikin video animasi", "video kartun/motion graphic", "animasi dari rekaman suara".
---

# Racik Animasi: Claude Code membuat video animasi

Kamu sutradara + animator. Rekaman suara pemilik → kamu menulis kode animasi Remotion (React) per video memakai
kit gaya khas **Racik Flat** (`animasi/src/kit/`) → kode merender & memeriksa. Rujukan alur:
`vendor/claude-animated-shorts/SKILL.md` (gaya 3D-nya tidak dipakai; alur naskah → suara → shot → cek still → render → QA dipakai).

**Aturan mutlak**
- **Tanpa API LLM.** Jangan memanggil Gemini/Groq/OpenAI (tidak lewat `autoreels run`, `import` tanpa caption, dsb.).
  Naskah, koreksi transkrip, deskripsi, dan caption kamu tulis sendiri. Transkripsi = faster-whisper lokal (CPU).
- Fakta bisnis hanya dari `config/brand.yaml` / ucapan narasi / pengguna. Harga tidak ada → jangan tampilkan angka.
- Nomor WhatsApp/IG di layar selalu dari `data.brand` (jangan diketik manual).
- Bahasa Indonesia ke pengguna. Perintah dijalankan dari root repo dengan `.venv/Scripts/autoreels`.
- Remotion: animasi hanya dari `useCurrentFrame()`/`useDetik()` — CSS transition/animation DILARANG (tidak ter-render).
  Rujukan teknis: skill `remotion-best-practices` (bila terpasang di `.claude/skills/`).

## 0. Tanyakan yang belum jelas (satu pesan)
Rekaman suara (mis. `footage/_uji/*.m4a`), pilar, tujuan video, nama video (kebab-case), mood musik.
Belum ada rekaman → tulis naskah dulu (langkah 1), pengguna merekam, baru lanjut.

## 1. Naskah (bila belum direkam)
±2,5–3 kata/dtk, 25–45 dtk. Rumus (diadaptasi dari STYLE_BIBLE claude-animated-shorts):
1. **Hook** kalimat pertama, tanpa basa-basi: pertanyaan/masalah penonton ("Liburan ke Garut, tapi pusing transportasi?").
2. **Solusi** 1 kalimat (nama layanan).
3. **Bukti/keunggulan** 3–5 ketukan pendek, tiap ketukan satu visual.
4. **Pembeda/bonus** (gratis, antar, dsb. — hanya yang ada di brand.yaml).
5. **CTA** WhatsApp + penutup pendek yang mengulang nama brand.
Tunjukkan naskah ke pengguna dan tunggu setuju.

## 2. Siapkan data
```
.venv/Scripts/autoreels animasi prepare -s <rekaman> -n <nama> -p <pilar> -b "<tujuan>" [--rentang "a-b,c-d"]
```
`--rentang`: potong & sambung bagian rekaman panjang (mis. podcast) sesuai urutan — boleh disusun ulang (cold open).
Podcast/konten orang lain: pilih sendiri bagian terbaik dari transkrip (baca, jangan pakai API); hanya untuk uji coba
kecuali ada izin pemiliknya; tokoh generik, bukan karikatur orang sungguhan.
Hasil: `animasi/public/<nama>/data.json` (kata per kata, frasa, brand, audio) + `work/_animasi/<nama>/naskah.txt`.
**Periksa transkrip**: betulkan salah dengar langsung di `data.json` → `kata[].text` (jangan ubah `start/end`,
jangan menambah kata yang tidak diucapkan) dan teks `frasa`. Tunjukkan daftar koreksi ke pengguna.

## 3. Rencana shot (tunjukkan ke pengguna sebelum menulis kode)
Satu adegan per ketukan naskah (±2–5 dtk): latar + elemen + kata pemicu. Prinsip:
- Tiap kalimat diilustrasikan harfiah; elemen muncul **0–3 frame sebelum** katanya diucapkan (`waktuKata`).
- Hook: teks hook terlihat sejak frame 0 (pakai waktu negatif, mis. `-0.3`), adegan hook ≤ 3 dtk, visual paling hidup.
- Tidak ada tahan diam: setiap adegan dibungkus `<Kamera>` (push-in pelan); hentakan (`hentak`) di kata penting.
- Pergantian adegan disembunyikan di `<Sapuan pada={…}>`; ganti warna latar tiap adegan (hijau/ungu/merah/kuning/krem).
- Zona aman: teks di y 300–1520, kanan atas kosong (logo ditempel importer).
- Maks ±2 elemen teks besar sekaligus; tulisan maks 2 baris per judul.

## 3b. Gaya visual (bisa diganti tanpa menulis ulang kode)
Gaya ada di `animasi/src/kit/gaya.json`: `racik-flat` (stiker), `garis-tipis` (line-art), `kertas` (cut-out
stop-motion 12 fps), `neon-malam`, `tipografi-tebal`, `pastel-ceria`, `grainy-gradient` (dua terakhir dari arah gaya bang-motion). Pilih saat prepare (`--gaya`) atau
`autoreels animasi gaya -n <nama> --pakai <id>`; `--pratinjau` merender satu frame video di semua gaya
(`work/_animasi/<nama>/gaya/*.jpg`). Agar kode jalan di SEMUA gaya:
- Pakai token kit (`WARNA.*`, `TINTA`, `warna()`, `warnaObjek()`, `tepi()`, `bayang()`, `sudut()`, `garisSvg()`,
  `gayaHuruf()`), bukan hex/garis tinta mati. Gaya baru = tambah entri gaya.json (+ font di assets/fonts).
- Teks besar lewat `Judul` (gaya polos otomatis diberi pelat agar terbaca).

**Ciri khas per video (wajib):** jangan hanya menyusun komponen kit. Buat minimal satu elemen visual yang hanya ada
di cerita ini (komponen SVG baru di folder videonya, mis. peta jalur ke destinasi tertentu, alat proyek tertentu,
metafora dari naskah), dan variasikan komposisi/kamera antar video supaya tidak terasa template.

## 3c. Video 3D (`dimensi: 3d`, `prepare --dimensi 3d`)
Dunia toon three.js lewat `animasi/src/kit3d` (Remotion `@remotion/three` + React Three Fiber, render memakai GPU):
`Panggung3D` (kanvas + cahaya + kabut, `suasana` siang/senja/malam, transisi `menuju`+`p`), `Kamera3D` (kunci
kamera berinterpolasi halus + `hentak`; untuk kamera ikut objek beri satu kunci yang dihitung tiap frame),
`Bentuk` (mesh toon + garis tinta inverted hull), dunia (`Tanah`, `Jalan`/`JALUR`/`diJalur`/`sampingJalur`, `Hutan`
dengan zona `bersih`, `Pegunungan`, `Gunung kawah`, `Pantai`, `Diorama`), objek (`Motor3D`+pengendara, `Garasi`,
`Bangunan`, `Pin3D`, `Helm3D`, `JasHujan3D`, `PapanTeks`). Contoh lengkap: `animasi/src/videos/rental-garut-3d/`.
- Satu `Panggung3D` per `Adegan`; teks/kartu/CTA tetap komponen 2D di luar kanvas. `useFrame` DILARANG.
- Pelajaran pembingkaian 9:16 (sudut horizontal hanya ±23° pada fov 40): objek selebar 10 satuan perlu kamera
  ±25 satuan; bersihkan pohon di sekitar objek & di jalur pandang kamera (`Hutan bersih`); objek utama di separuh
  atas bila kartu 2D memakai separuh bawah; jangan ada papan/objek di antara kamera & subjek; jangan duplikasi teks
  2D dengan papan nama 3D. Selalu cek `stills` sebelum render (render 3D jauh lebih lama).

## 3d. Anti-PPT (wajib — diadaptasi dari `vendor/bang-motion`, baca `references/anti-ppt.md` di sana)
Video yang "benar secara teknis" tetap gagal bila terasa seperti slide. Periksa KODE sebelum render:
1. **Bukan potongan per kalimat.** Adegan berganti karena dunia/kamera bergerak (kamera meluncur, mendekat ke
   elemen yang bercerita lalu mundur, satu subjek yang terus beraksi), bukan karena `Adegan` baru tiap frasa.
   `Sapuan` maks 2 per video. 3D: satu `Panggung3D` + satu kamera yang dicampur antar momen (contoh
   `videos/rental-garut-3d`: luncuran melengkung mengitari subjek, terbang jauh = naik & menatap tujuan).
2. **Ada benang merah:** satu hero (motor, tukang, rumah) hadir > 60 % durasi, atau satu dunia yang disusuri kamera.
3. **Maks 2 tingkat teks per momen** (satu kalimat ≤ 5 kata + satu label dunia). Tidak ada tumpukan 3 kartu fitur:
   ganti dengan kata yang berganti di tempat yang sama, objek yang berubah, atau satu fitur yang didemokan.
4. **Tipografi hidup:** `Judul kapital={false}` (huruf kalimat) secara default, kapital tebal hanya untuk 1 momen
   penekanan; `rata`/`y`/arah masuk bergantian antar momen; tanpa titik otomatis.
5. **Transisi bervariasi**, light leak (`KilauCahaya` / `Sapuan kilau`) hanya untuk SATU momen istimewa.
6. **Kerangka bukan template:** hindari urutan hook → fitur → fitur → janji → logo → CTA bila tidak dituntut konsep.
Gagal satu poin → rombak sebelum render.

## 3e. Efek Remotion (skill `remotion-best-practices` → `remotion-markup`)
`@remotion/effects` lewat `HtmlInCanvas`/`Solid` (WebGL, `Config.setChromiumOpenGlRenderer('angle')` sudah diset):
`Panggung3D` sudah memakai colorCorrection + vignette + tilt-shift (`fokus`, `bokeh`). `@react-three/postprocessing`
(EffectComposer) TIDAK jalan di ThreeCanvas Remotion (frame kosong) — jangan dipakai. Lainnya tersedia:
`glow`, `zoomBlur`, `halftone`, `paper`, `noise`, `chromaticAberration`, transisi `@remotion/transitions`.

## 4. Tulis kode
- Folder `animasi/src/videos/<nama>/Video.tsx`, daftarkan di `animasi/src/videos/index.ts` (`'<nama>': Komponen`).
- Contoh lengkap: `animasi/src/videos/rental-garut/Video.tsx`.
- **Penanda adegan (wajib):** tepat sebelum kode tiap adegan tulis satu baris `// === ADEGAN 3: judul singkat ===` (nomor urut dari 1, judul ≤ 4 kata). Web Ruang Kerja memakainya untuk lini masa adegan. Sebelum menulis kode buat juga daftar langkah dengan TodoWrite (satu butir per adegan + musik, caption, cek frame, render) dan perbarui statusnya.
- Kit (`import … from '../../kit'`):
  - waktu: `useData`, `useDetik`, `waktuKata(data, 'kata', setelah?)`, `waktuTiapKata(data, 'kalimat')`
  - panggung: `Adegan`, `Kamera`, `Latar` (pola titik/garis/sinar/kotak), `Sapuan`, `GarisLaju`
  - teks: `Judul` (kinetik per kata), `Label`, `Subtitle` (karaoke, opsional), `Cap` (stempel)
  - objek: `Stiker`, `KartuFitur`, `Ikon`/`IkonBebas` (helm, jasHujan, jam, tagHarga, kilat, kalender, kereta, rumah,
    chat, cek, kunci, kilau, pusing, pin, tanya, tangan), `Motor` (+ pengendara), `Pemandangan` (parallax), `PetaRute`
    (skematis), `CtaWA`
  - tema: `WARNA`, `GARIS`, `BAYANGAN`, `AMAN`, `FONT_JUDUL`, `FONT_ISI`
- Butuh elemen baru yang dipakai ulang → tambahkan ke kit (gaya sama: garis tinta `TINTA` ±7 px, bayangan keras,
  gerak `pop`), bukan di file video.
- Cek tipe: `.venv/Scripts/autoreels animasi cek`.

## 5. Cek still (wajib sebelum render penuh)
```
.venv/Scripts/autoreels animasi stills -n <nama>                 # tengah tiap frasa
.venv/Scripts/autoreels animasi stills -n <nama> --detik 0,0.5,4.1
```
Lihat `work/_animasi/<nama>/lembar_stills.jpg` (dan file di `stills/`). Periksa: hook terbaca di 0 dtk, teks tidak
terpotong/bertumpuk, tidak ada garis sambungan, elemen sesuai kata yang diucapkan, zona aman, kontras teks.
Perbaiki → ulangi sampai bersih.

## 5b. Musik orisinal (kamu yang menggubah)
Tulis partitur `work/_animasi/<nama>/musik.json` (format & contoh di docstring `autoreels/musik_sintesis.py`):
tempo/kunci sesuai suasana, `bagian` mengikuti adegan (energi 1 di bagian masalah, 3 di solusi/CTA; `tanpa: ["melodi"]`
saat ucapan padat), `aksen` di hentakan, `sfx` (whoosh di tiap Sapuan, pop saat kartu muncul, ding di "gratis").
`.venv/Scripts/autoreels animasi musik -n <nama>` (render juga menggubah otomatis). Konten bicara: `"musik_db": -24`.

## 6. Caption (kamu yang menulis, tanpa API)
`work/_animasi/<nama>/caption.json`: `{"caption": "…", "hashtags": ["#…"]}` mengikuti `config/caption_guide.md`
(sapaan, emoji, Sunda ringan bila pilar rental) + hashtag dasar pilar di `config/pillars.yaml`. Tanpa harga karangan.

## 7. Render + checklist
```
.venv/Scripts/autoreels animasi render -n <nama> [--cta "Booking sekarang!"]
```
Remotion → `work/_animasi/<nama>/anim.mp4` → importer: 1080×1920 30 fps, −14 LUFS, TANPA watermark (default;
`--logo` untuk menempel), caption dari file, pilar `umum` = video informasi tanpa CTA,
Checklist Siap Unggah → `output/<job>/` (reel.mp4, caption.txt, report.md). Render CPU ±3–6 menit per 45 dtk.
Laporkan status checklist apa adanya; butir gagal → perbaiki & render ulang.

## 8. Serahkan
Path `reel.mp4`, `caption.txt`, ringkasan checklist, dan catatan yang perlu dicek manusia (mis. pelafalan, peta skematis).
