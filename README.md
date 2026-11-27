# Racik (AutoReels)

Ubah **video mentah** menjadi **video siap unggah** (saat ini format Instagram Reels 9:16) untuk Contoh Brand (`@contohbrand`), cukup dengan instruksi bahasa Indonesia. Berjalan di laptop biasa (CPU) + API LLM;
GPU hanya opsional untuk uji coba model lokal.

- **Racik** = nama aplikasi di tampilan web (konstanta `APP_NAME` di `frontend/src/lib/constants.js`).
- **AutoReels** = nama kode/paket Python (`autoreels/`, perintah `autoreels`).

> Spesifikasi lengkap: [CLAUDE.md](CLAUDE.md) · Arsitektur & keputusan desain: [docs/arsitektur/](docs/arsitektur/README.md)

## Status

| Tahap | Isi | Status |
|---|---|---|
| 0 | Fondasi: struktur repo, skema EDL, wrapper LLM, CLI | ✅ selesai |
| 1 | MVP montase b-roll (Rental Motor) | ✅ selesai |
| 2 | Gaya, brand & pilar Konstruksi | ✅ transisi xfade (fade/slide/whip), color grade per gaya + **warna seragam antar klip** (pencilan gelap/terang & rona cahaya dikoreksi sebelum look; `color_match` per gaya), **stabilisasi** adegan goyang (vidstab), **crop pengikut subjek** (deteksi objek NanoDet: motor/orang/mobil diikuti sepanjang adegan, bukan geser lurus), **skor momen** (bagian adegan dengan subjek utuh, tajam & stabil dipilih untuk potongan b-roll), **efek suara transisi** buatan sendiri (whoosh/thump/pop; `sfx_db` per gaya), speed-up kronologis, mode before–after (wipe + label Sebelum/Sesudah), blur wajah & pelat (opsional), caption & hashtag, loudness. Uji before–after dengan footage konstruksi asli (kondisi awal + hasil jadi) masih menunggu footage |
| 3 | Video berbicara (transkrip, subtitle) | ✅ transkrip per kata + kosakata brand, koreksi salah dengar (AI + periksa manusia), alur **narasi dulu**, alur **video bicara** (`--bicara` / web "Video bicara"): buang take ulang, **ringkas** (AI memilih kalimat 30–45 dtk) atau **utuh** (ikut panjang video, maks 3 menit), **cold open** (klausa 1,5–5 dtk paling menohok diputar di depan sebagai teaser, lalu video berjalan urut), sinkron bibir, crop fokus ke pembicara aktif (gerak bibir, per shot kamera), cut antar potongan, subtitle karaoke (angka/harga/promo/nama tempat ditekankan: warna + pop), teks hook otomatis menjauhi wajah pembicara, sisip b-roll (kode mencocokkan kata di ucapan dengan deskripsi adegan → saran per frasa; hook/cold open/penutup wajib wajah, maks 2 b-roll berurutan, pembicara ≥ 60%). **Cari cuplikan**: video panjang (podcast/kuliah) → semua bagian yang layak (maks 20, skor tertinggi di atas; "Cari ulang" memberi bagian lain) → beberapa Reel sekaligus. Diuji dengan kuliah umum & podcast (rekaman staf Brand menyusul) |
| 4 | Critic loop & evaluasi | ✅ Critic menilai EDL dengan rubrik 1–5, Director merevisi maks 2 putaran, versi terbaik dipakai; skor hook ≥ 4 wajib di checklist; **cek visual video jadi**: setelah render, model vision melihat 6 frame `reel.mp4` (teks terbaca/menutupi wajah, crop, frame gelap) → masalah berat = perlu tinjau; tab **Penilaian AI** di web; `autoreels eval` → `eval/report.md` + `results.csv`: set uji 7 skenario, perbandingan **dengan vs tanpa revisi Critic** dan **antar model Director** dengan penilai tetap (2026-11-24: Gemini 3.5 Flash Lite terbaik, lalu Runcrate GPT-OSS-120B, Cohere Command A+). Riset mesin lokal: [eval/riset_mesin_lokal_2026-11-20.md](eval/riset_mesin_lokal_2026-11-20.md); **belajar dari editan Anda**: versi AI disimpan (`edl_ai.json`), tiap render ulang perbedaannya dicatat (`edits.json`), lalu dirangkum jadi `config/preferensi.md` (web *Bahan AI → Preferensi* / `autoreels preferensi --rangkum`) yang dibaca Director di job berikutnya |
| 5 | Antarmuka | ✅ Racik Studio (React) menggantikan rencana Gradio |
| 6 | Posting terjadwal & koneksi Instagram (API resmi) | ⏳ |

## Instalasi (Windows)

Prasyarat: **Python 3.11+** dan **FFmpeg** (`winget install Gyan.FFmpeg`; lokasi winget terdeteksi otomatis).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt    # semua paket (versi teruji) + perintah `autoreels`
copy .env.example .env             # lalu isi API key
python main.py --web               # buka Racik Studio
```

Penjelasan tiap paket ada di [requirements.txt](requirements.txt). Alternatif per kebutuhan:
`pip install -e ".[dev,analysis,web]"` (sama dengan requirements.txt, versi tidak dikunci),
`pip install -e ".[speech]"` (Tahap 3: transkripsi).

### Kunci API & model cadangan

Isi kunci di `.env` (contoh lengkap di [.env.example](.env.example)). Minimal **Gemini** (vision + cadangan) dan **Groq**
(Director & Critic). Bila model utama kena limit, sistem mencoba model cadangan **berurutan**:

```
LLM_FALLBACK_MODEL=gemini/gemini-3.5-flash-lite,runcrate/openai/gpt-oss-120b,cohere_chat/command-a-plus-05-2026
VISION_FALLBACK_MODEL=gemini/gemini-3.5-flash-lite,cohere_chat/command-a-vision-07-2025,groq/qwen/qwen3.8-27b
```

- Jatah **harian** habis → langsung pindah ke model berikutnya; limit per menit → tunggu ±1 menit lalu pindah.
- Penyedia yang didukung: Gemini, Groq, Cohere (`cohere_chat/…`), **Runcrate** (`runcrate/<id katalog>`, gerbang
  OpenAI-compatible; akun gratis hanya model gratis seperti `openai/gpt-oss-120b`), **AionLabs** (`aionlabs/<id>`;
  butuh kartu pembayaran terverifikasi), Anthropic, OpenAI, DeepSeek.
- Mesin lokal (Ollama) tidak pernah diam-diam pindah ke API.

> Setelah `git pull` atau mengubah kode Python, **tutup lalu jalankan ulang** `python main.py --web`.
> Tampilan web memuat file baru dari disk, tetapi server lama tetap memakai kode lama sampai di-restart.

### Opsional: mesin AI lokal (Ollama, uji coba)

Untuk mencoba tanpa API (mis. saat kuota habis) di laptop ber-GPU. API tetap default.

```powershell
# pasang Ollama dari ollama.com, lalu:
ollama pull qwen3:4b                # Director & caption (teks)
ollama pull qwen3-vl:4b-instruct    # Describe (gambar) — pakai varian -instruct, bukan tag polos qwen3-vl:4b
```

Pilih **Mesin AI → Lokal (Ollama)** di langkah *Atur*, atau `autoreels run … --engine local`. Model bisa diganti
lewat `.env` (`LOCAL_LLM_MODEL`, `LOCAL_VISION_MODEL`, `LOCAL_NUM_CTX`). Di RTX 4050 6 GB: ±6 menit per video
(API ±2 menit); `qwen3:8b` tidak muat penuh di VRAM dan terlalu lambat. Detail: [riset 2026-11-20](eval/riset_mesin_lokal_2026-11-20.md).

## Pemakaian

### Cara termudah — tampilan web (Racik Studio)
```powershell
python main.py --web
```
Browser terbuka otomatis di `http://127.0.0.1:8000`. Isinya:

- **Buat video** — wizard 4 langkah:
  1. *Footage*: pilih pilar (Rental, Konstruksi, Profil, Lowongan, atau **Konten Umum** untuk konten di luar unit
     usaha seperti klip kuliah/podcast), unggah video atau pilih folder, **centang klip yang dipakai** dan **klik
     thumbnail untuk preview**.
  2. *Atur*: **alur** (Video dulu / Narasi dulu / Video bicara), instruksi, gaya, durasi, teks hook/CTA (atau biar AI),
     voice over, **musik** (otomatis sesuai gaya / **tanpa musik** / pilih lagu per suasana). Panel lipat **Pengaturan
     lanjutan**: tujuan (otomatis / promosi dengan CTA + WhatsApp / informasi tanpa CTA), **watermark**, **privasi**
     (blur wajah/pelat), **mesin AI (API/lokal)**. Ringkasan di samping hanya menampilkan nilai yang bukan bawaan.
     Bila footage tidak cocok dengan alur (mis. podcast panjang di Video dulu), muncul saran/peringatan sejak awal.
  3. *Proses*: progres real-time + log teknis; beberapa Reel dari cuplikan tampil berurutan (selesai/gagal/sedang/menunggu).
  4. *Hasil*: video 9:16, **strip struktur video** (hook/isi/CTA; klik untuk lompat), caption siap salin,
     edit teks + **edit subtitle karaoke per frasa** + render ulang tanpa biaya AI, voice over, checklist siap unggah.
     **Buat varian**: dari proyek yang sama buat versi 15/20/30/45 dtk (Video dulu), versi tanpa CTA, atau ringkas/utuh
     (Video bicara) — analisis & deskripsi adegan diambil dari cache, hanya penyusun edit AI yang dipanggil ulang
     (`POST /api/jobs/{id}/variants`; permintaan asli disimpan di `work/<job>/request.json`).
- **Riwayat** (berisi tombol *Impor video dari editor lain* — video dari CapCut/video-use dinormalkan, diberi watermark,
  CTA, caption, lalu dicek checklist) dan grup lipat **Bahan untuk AI**: pustaka hook, hashtag & keyword, brief tren
  (ada pengingat bila > 7 hari tidak diperbarui), brand & caption.
- Daftar panjang (subtitle, lagu, cuplikan) memakai kotak setinggi tetap + saring/cari agar halaman tidak memanjang.
- **Video yang sedang dibuat tidak hilang** saat pindah halaman atau refresh: indikator progres tampil di navigasi
  dan di atas Riwayat (klik untuk kembali ke layar Proses); bila selesai saat Anda di halaman lain, muncul
  notifikasi *Lihat hasil* (Anda tidak dipindahkan paksa).
- Tema terang/gelap mengikuti Windows; halaman aktif tersimpan di URL (`?page=`, `?job=`).

**Voice over**: di langkah *Atur* pilih *Suara sendiri* (utama) atau *Suara AI*. AI menulis naskah sesuai durasi & layanan
resmi; di halaman *Hasil* naskah bisa diedit, lalu **rekam sambil video diputar** (teleprompter, di laptop) atau
**unggah rekaman** dari HP. Musik otomatis turun saat ada suara; subtitle dibuat dari naskah. Suara AI: aktifkan label
*AI info* saat unggah ke Instagram. Kuota gratis suara AI: ±10 video/hari.

**Buka dari HP** (HP & laptop di Wi-Fi yang sama):
```powershell
python main.py --hp
```
Terminal menampilkan alamat (mis. `http://192.168.x.x:8000`) dan **PIN 6 digit** acak. Buka alamat itu di browser HP,
masukkan PIN. Video bisa langsung diunggah dari galeri/kamera HP. Laptop harus tetap menyala selama dipakai.

**Frontend**: React + Vite + Tailwind di `frontend/`. Hasil build (`frontend/dist`) ikut di-commit, jadi memakai UI
**tidak butuh Node.js**. Node.js 18+ hanya perlu bila ingin mengubah tampilan:
```powershell
cd frontend
npm install
npm run dev      # mode pengembangan di http://localhost:5173 (backend python main.py --web harus jalan)
npm run build    # perbarui frontend/dist setelah mengubah kode — lalu commit dist/
```
Tambahkan `?mock=1` di URL untuk mencoba UI dengan data simulasi tanpa backend.
Bila `frontend/dist` tidak ada, server memakai versi cadangan tanpa build di `ui/` (Alpine.js).

### Menu interaktif di terminal
```powershell
python main.py
```
Menu: buat Reel, kelola hook, hashtag & keyword, brief tren, harga/CTA, panduan caption,
edit teks & render ulang, lihat hasil, pantau progress. Semua isian punya default — tekan Enter untuk memakainya.

### Lewat perintah (CLI)

```powershell
autoreels --help
autoreels status                                   # pantau progress job secara real-time
autoreels analyze --input footage\rental          # cek kualitas footage (tanpa AI)
autoreels styles                                   # daftar style preset
autoreels validate output\<job_id>\edl.json        # cek EDL
autoreels run --input footage\rental --pillar rental `
  --brief "Promo sewa motor untuk wisatawan libur akhir tahun" `
  --style rental_energik --duration 20
autoreels run ... --clip a.mp4 --clip b.mp4        # hanya proses klip tertentu dari folder
autoreels run ... --engine local                   # pakai model lokal Ollama (uji coba)
autoreels run ... --blur-wajah --blur-pelat        # samarkan wajah / pelat nomor (default mati)
autoreels run ... --tanpa-critic                  # lewati Critic (hemat biaya / pembanding evaluasi)
autoreels run --bicara <video> --pillar umum --brief "..."     # video bicara → Reel ringkas 30–45 dtk (fokus ke pembicara)
autoreels run --bicara <video> ... --utuh         # video bicara utuh: durasi ikut panjang ucapan (maks 3 menit)
autoreels run ... --tanpa-musik --tanpa-watermark # tanpa musik latar / tanpa logo di pojok
autoreels cuplikan --input <video panjang>                      # cari 3–5 cuplikan 1–3 menit terbaik (podcast/kuliah)
autoreels cuplikan --input <video panjang> --pilih 1,3 --buat    # potong cuplikan terpilih & jadikan Reel masing-masing
autoreels run ... --tujuan informasi              # promosi (CTA + WhatsApp) | informasi (tanpa CTA, musik 35%); kosong = otomatis
autoreels run ... --narasi footage\_narasi\suara.m4a   # alur narasi dulu: gambar ikut kalimat narasi, durasi = narasi
autoreels transcribe --input <audio/video> --demo  # transkrip per kata + video contoh subtitle karaoke
autoreels render --edl output\<job_id>\edl.json   # render ulang setelah edit teks di edl.json (tanpa biaya AI)
autoreels import --video <folder>\edit\final.mp4 --pillar profil   # impor video jadi (video-use/editor lain)
autoreels eval                                    # rangkum semua job → eval/report.md (tanpa biaya AI)
autoreels prepare --input footage\rental --pillar rental --brief "..."   # mode Claude sebagai sutradara (lihat bawah)
autoreels finish --job <job_id> [--cek] [--critic <file>]               # validasi EDL tulisan Claude → render → checklist
autoreels eval --jalankan --bandingkan-critic     # set uji (eval/testset/manifest.csv): nilai saja vs revisi Critic
autoreels eval --jalankan --model gemini/gemini-3.5-flash-lite --model runcrate/openai/gpt-oss-120b `
  --penilai cohere_chat/command-a-03-2025         # bandingkan model Director dengan penilai yang sama
```

Catatan: perintah CLI berjalan **di luar antrean server web**. Jangan menjalankan job dari CLI bersamaan dengan job
dari web — keduanya akan berebut CPU/GPU (lihat risiko R3 di [docs/arsitektur](docs/arsitektur/README.md#5-risiko--mitigasi)).

**Tiga alur di Racik Studio (langkah Atur → Alur):**

- **Video dulu** (default) — montase ikut ketukan musik, durasi Anda tentukan; voice over opsional direkam belakangan.
- **Narasi dulu** — unggah rekaman suara (disimpan di `footage/_narasi/`, tidak di-commit). Kata pengisi & jeda panjang
  dibuang, narasi dipecah per frasa (1–3,5 dtk; frasa pertama ≤ 3 dtk sebagai hook), Director memilih satu adegan per
  frasa, durasi video = panjang narasi (maks 90 dtk), subtitle karaoke otomatis, musik diredam di bawah suara.
  Sebelum video dibuat, klik **Transkrip & periksa**: salah dengar dikoreksi AI (hanya kata yang salah dengar,
  tanpa menambah kata), lalu Anda periksa/betulkan teks per frasa sambil memutar suaranya. Waktu audio tetap,
  jadi subtitle karaoke tetap pas. Lewat CLI (`--narasi`), koreksi AI berjalan otomatis tanpa pemeriksaan.
- **Video bicara** — orang bicara ke kamera (penjelasan, testimoni, podcast, kuliah). Pembicara diambil dari klip yang
  dipilih di langkah Footage (klip lain jadi b-roll). Pilih **Panjang Reel**: *Ringkas* (AI memilih kalimat terkuat jadi
  30–45 dtk) atau *Utuh* (seluruh ucapan, maks 3 menit); keduanya dibuka *cold open* — ucapan paling menohok sebagai teaser. Gambar dikunci ke ucapan (sinkron bibir), crop
  9:16 fokus ke orang yang sedang bicara, antar potongan pembicara selalu cut, subtitle karaoke. Video > 10 menit wajib
  lewat **Cari cuplikan terbaik**: AI mengusulkan 3–5 bagian 1–3 menit yang utuh (judul, rentang waktu, alasan, pratinjau),
  centang beberapa lalu **Buat N Reel** — dibuat satu per satu, halaman Proses menampilkan "Reel 2 dari 3" dan lanjut
  otomatis. Transkripsi pertama ±13 menit per jam video, lalu tersimpan. CLI: `autoreels cuplikan`.
  **Transkrip & periksa subtitle** (opsional, disarankan): AI memilih kalimat & membetulkan salah dengar, Anda periksa
  per frasa (saring *Perlu dicek*, cari kata, ikuti suara) sebelum render. Reel dari cuplikan dibetulkan subtitlenya di
  halaman Hasil lalu render ulang. Klip > 10 menit ditolak di alur Video dulu/Narasi (arahkan ke Video bicara).

**Pilar Konten Umum** (konten di luar unit usaha): bawaan tujuan *informasi* (tanpa CTA/WhatsApp, musik pelan), tanpa
hashtag Brand, kredit sumber di caption bila disebut di instruksi, gaya bawaan **Klip Informatif** (potongan tenang,
cut/fade, warna bersih). Konten pihak ketiga (kuliah/podcast orang lain) hanya untuk uji, jangan diposting.

**Claude Code sebagai sutradara** (tanpa biaya Director API, memakai kuota langganan lewat chat): ketik
`/racik-sutradara` di Claude Code. Claude menyiapkan bahan (`autoreels prepare`), melihat lembar kontak adegan,
menulis deskripsi + EDL + penilaian rubrik, lalu `autoreels finish` memvalidasi, merender, dan menjalankan Checklist
Siap Unggah. Panduan langkahnya di [.claude/skills/racik-sutradara/SKILL.md](.claude/skills/racik-sutradara/SKILL.md).

Video bicara/spesial bisa diedit lewat chat dengan **video-use**, lalu diimpor — lihat [docs/video-use.md](docs/video-use.md).

## Struktur folder

```
racik-reels/
├── main.py             # menu interaktif (python main.py) · --web = Racik Studio · --hp = akses dari HP
├── autoreels/          # kode Python (paket utama)
│   ├── cli.py          #   perintah: run, cuplikan, prepare, finish, import, render, transcribe, analyze, validate, styles,
│   │                   #   status, studio, eval, version
│   ├── server.py       #   backend FastAPI + antrean job (1 worker) + penyaji frontend & media
│   ├── pipeline.py     #   orkestrasi semua langkah + laporan
│   ├── edl.py          #   skema EDL (kontrak LLM ↔ renderer)
│   ├── llm.py          #   wrapper litellm + klien Ollama + cache + catatan biaya
│   ├── config.py       #   pemuat .env & YAML, pilihan mesin AI (api/local)
│   ├── checklist.py    #   Checklist Siap Unggah
│   ├── importer.py     #   impor video jadi
│   ├── voiceover.py    #   naskah, rekaman & suara AI
│   ├── narration.py    #   alur narasi dulu: transkrip bersih, koreksi AI, draf diperiksa manusia
│   ├── talk.py         #   video bicara: kalimat, buang take ulang, ringkas/utuh, sinkron bibir
│   ├── highlights.py   #   cari cuplikan: video panjang → beberapa bagian 1–3 menit
│   ├── critic.py       #   penilai rubrik 1–5 + catatan revisi
│   ├── evaluate.py     #   evaluasi set uji → eval/report.md
│   ├── manual.py       #   mode Claude Code sebagai sutradara (skill /racik-sutradara)
│   ├── analyze/        #   adegan, kualitas, subjek, audio, transkrip
│   └── render/         #   potong, reframe, fokus pembicara, teks & karaoke, overlay, transisi, privasi, audio
├── frontend/           # Racik Studio (React + Vite + Tailwind)
│   ├── src/
│   │   ├── App.jsx           # kerangka: navigasi, dialog, toast
│   │   ├── state/studio.jsx  # semua state & aksi (pemanggilan API)
│   │   ├── pages/            # Buat video (create/), Riwayat (+ impor), Bahan AI (materials/)
│   │   ├── components/       # komponen UI dasar, kerangka navigasi, pilihan mesin AI
│   │   ├── lib/              # konstanta, format, data simulasi (?mock=1)
│   │   └── assets/fonts/     # font lokal (Barlow Condensed, Plus Jakarta Sans; OFL)
│   ├── public/favicon.png    # logo Brand di tab browser
│   └── dist/                 # hasil build (di-commit)
├── ui/                 # UI cadangan tanpa build (Alpine.js)
├── prompts/            # prompt LLM (.md) — diedit tanpa menyentuh kode
├── config/             # brand, pilar, hook, style preset (YAML) — dikelola pengguna
├── trends/brief.md     # brief tren mingguan (diisi manual)
├── assets/             # logo, font, musik bebas royalti per mood
├── docs/               # arsitektur (diagram, ADR, risiko), panduan video-use, brief UI
├── footage/            # video mentah per pilar (tidak di-commit)
├── eval/               # set uji, rubrik, skrip evaluasi, catatan riset
├── tests/              # pytest
├── work/               # cache & file antara (tidak di-commit)
└── output/             # hasil video + edl.json + caption + report (tidak di-commit)
```

## Yang perlu diisi pemilik proyek

- `config/brand.yaml` → warna & font brand, harga sewa, handle akun rental (bertanda `[ISI]`)
- `assets/music/<mood>/` → musik **bebas royalti** + catat sumber & lisensinya di `assets/music/LISENSI.md`
  (lihat [assets/music/README.md](assets/music/README.md))
- `trends/brief.md` → setiap minggu
- `.env` → API key LLM (Gemini, Groq; opsional Cohere/Runcrate/AionLabs sebagai cadangan, model lokal Ollama)

## Tes

```powershell
pytest
```

## Referensi & kredit

- **[video-use](https://github.com/browser-use/video-use)** (browser-use, lisensi MIT) — editor video berbasis percakapan untuk
  Claude Code. Dipakai sebagai **mode kedua** untuk video bicara/spesial (edit lewat chat, lalu diimpor dengan
  `autoreels import`, lihat [docs/video-use.md](docs/video-use.md)), sekaligus rujukan desain: aturan potong di batas kata,
  fade audio di setiap potongan, color grade per klip, dan pemeriksaan hasil render di setiap titik potong.
- Rujukan riset arsitektur (LAVE, EditDuet, VC-LLM, CutClaw, Write-A-Video, SnapUGC, dll.) ada di `CLAUDE.md` bagian 10.
- Musik: Mixkit (Mixkit Free License) — daftar di `assets/music/LISENSI.md`. Font: lisensi OFL/FFL di masing-masing folder font.
- Model lokal opsional: Qwen3 / Qwen3-VL lewat [Ollama](https://ollama.com).
