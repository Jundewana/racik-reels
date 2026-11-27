# CLAUDE.md — AutoReels: AI-Powered Automated Video Editing untuk Instagram Reels Contoh Brand

> Simpan file ini sebagai `CLAUDE.md` di root repository. Claude Code otomatis membacanya di setiap sesi.
> Bagian bertanda **[ISI]** masih perlu dilengkapi pemilik proyek.

---

## 1. Konteks proyek

Kita membangun **AutoReels**, sistem yang mengubah **video mentah** menjadi **Instagram Reels siap unggah** berdasarkan instruksi pengguna dalam bahasa alami (bahasa Indonesia).

Sistem harus bisa:
- memilih footage dan memotong adegan terbaik,
- menyusun alur cerita dengan **hook kuat di 3 detik pertama**,
- menambahkan subtitle/teks animasi, transisi, musik latar, dan elemen visual (teks hook, judul, CTA, logo),
- mengikuti **gaya (style preset)** yang dipilih pengguna,
- mempertimbangkan **brief tren** yang diperbarui secara manual tiap minggu.

### Akun/brand target

**Contoh Brand** — brand contoh (placeholder) untuk usaha perdagangan dan jasa lokal. Ganti seluruh data di bawah dengan brand Anda lewat `config/brand.yaml`.
- **Alamat:** (isi di `config/brand.yaml`).
- **Instagram:** `@contohbrand`; unit rental motor (afiliasi, "Rental Motor"): `@contohrental`.
- **Unit usaha & pilar konten:**

| Pilar konten | Unit usaha | Target audiens | Tujuan konten |
|---|---|---|---|
| **A. Rental Motor** (prioritas) | penyewaan sepeda motor | wisatawan ke Garut, warga lokal, mahasiswa/perantau | booking via WhatsApp/DM |
| **B. Konstruksi & arsitektur** | konstruksi, rekonstruksi, infrastruktur (contoh: jaringan irigasi & drainase, gedung), desain arsitektur | instansi pemerintah/desa, pemilik proyek swasta, calon klien | kredibilitas & portofolio |
| **C. Jasa & operasional lain** | perdagangan, jasa, pengelolaan katering rumah sakit | mitra institusi | profil perusahaan & kepercayaan |
| **D. Employer branding** | seluruh perusahaan | pencari kerja Garut | info lowongan, budaya kerja |

- **Gaya bahasa:** bahasa Indonesia santai-sopan; untuk pilar A boleh sisipan bahasa Sunda ringan bila pemilik setuju ([ISI: ya]).
- **Warna & font brand, logo, nomor WhatsApp untuk CTA:** (isi di `config/brand.yaml`).

### Jenis video mentah yang dominan

Berdasarkan unit usahanya, mayoritas footage adalah **b-roll tanpa banyak ucapan**, dengan sebagian kecil video bicara:

| Jenis footage | Contoh | Ucapan? | Kebutuhan sistem |
|---|---|---|---|
| Unit motor | walkaround motor, detail fitur, motor berjajar di garasi | tidak | potongan cepat, teks overlay harga/fitur, musik |
| Perjalanan wisata | POV/rekaman berkendara ke destinasi wisata Garut, pemandangan | tidak (suara angin/bising) | stabil, buang bagian goyang/gelap, montase ikut beat |
| Serah terima & pelanggan | pelanggan mengambil motor, testimoni singkat | kadang | transkrip untuk testimoni; izin wajah pelanggan |
| Progres proyek | kondisi awal, pekerja di lapangan, kondisi akhir, drone (bila ada) | tidak (bising mesin) | before–after, urutan kronologis, timelapse/speed-up |
| Penjelasan/profil | staf/manajer menjelaskan layanan, info lowongan | ya | penyuntingan berbasis transkrip, buang jeda & kata pengisi |

Konsekuensinya: **montase b-roll + teks overlay + musik adalah alur utama (Tahap 1)**, sedangkan video bicara menjadi Tahap 3. Audio asli b-roll sering bising, jadi default-nya diredam/diganti musik.

### Prinsip utama
1. **Modal minim, API sebagai default.** Semua komponen harus tetap berjalan di laptop biasa (CPU) + API. Model lokal via **Ollama** boleh sebagai **opsi uji coba** (mesin `local`, dipilih per job di web/CLI; keputusan pemilik 2026-11-20, laptop RTX 4050 6 GB), tapi tidak boleh menjadi syarat: mesin `api` tetap default dan semua fitur harus jalan tanpa GPU. Jangan menambah dependensi Python yang butuh GPU (PyTorch GPU, dsb.); Ollama dipanggil lewat HTTP.
   **Pengecualian — Racik Animasi** (keputusan pemilik 2026-11-26, atas arahan mentor): video animasi 2D flat penuh dibuat Claude Code dengan **Remotion** (Node, folder `animasi/`, web: halaman Animasi di Racik Studio), murni tanpa API LLM (naskah, koreksi transkrip, caption ditulis Claude Code; transkripsi faster-whisper lokal). Gaya 2D jalan di CPU; **3D** (keputusan pemilik 2026-11-26) = `animasi/src/kit3d` (three.js + React Three Fiber via `@remotion/three`, dunia toon bergaris tinta, memakai GPU laptop; `prepare --dimensi 3d`), contoh `src/videos/rental-garut-3d`. Lisensi Remotion: gratis untuk perorangan/≤3 karyawan, pemakaian Brand butuh Company License (lihat `animasi/README.md`). Rujukan: `vendor/` (git clone, tidak di-commit; utama `claude-animated-shorts`).
2. **Tidak melatih model sendiri** di tahap awal. Gunakan model pralatih (zero-shot) + prompt + aturan.
3. **LLM memutuskan, FFmpeg mengeksekusi.** LLM hanya menghasilkan *naskah edit* (Edit Decision List/EDL) berformat JSON. Semua rendering dilakukan oleh kode deterministik.
4. **Manusia tetap memegang kendali.** Setiap hasil bisa ditinjau dan dirender ulang dari EDL tanpa memproses ulang semuanya.
5. **Hemat biaya API.** Kirim frame beresolusi kecil, cache semua respons, catat estimasi biaya per job.
6. **Patuh aturan platform & privasi.** Jangan membuat scraper Instagram. Data tren dimasukkan manual lewat `trends/brief.md`. Musik hanya dari folder lokal berisi musik bebas royalti; musik trending hanya bisa ditambahkan manual di aplikasi Instagram (tidak tersedia lewat API). Koneksi ke Instagram **hanya lewat API resmi Meta** (Instagram Graph API). Sediakan opsi blur wajah pelanggan dan pelat nomor kendaraan.
7. **Hasil wajib benar-benar jadi.** Output akhir adalah video yang langsung bisa diunggah tanpa diedit lagi: hook benar, style benar, teks terbaca, CTA ada. Setiap job harus lolos *Checklist Siap Unggah* (lihat bawah); bila gagal, sistem memperbaiki/merender ulang otomatis atau menandai job `perlu_tinjau` dengan alasan yang jelas — jangan pernah diam-diam menghasilkan video setengah jadi.

### Checklist Siap Unggah (wajib lolos sebelum video boleh dijadwalkan)
| Aspek | Syarat |
|---|---|
| **Video jadi** | 1080×1920, 30 fps, H.264/AAC, durasi target ±10%, tanpa frame hitam/beku, tanpa adegan `unusable`, audio tidak clipping (≈ −14 LUFS) |
| **Hook benar** | segmen pertama ≤ 3 detik; teks hook muncul di detik 0 dan terbaca ≥ 1,5 detik; tipe hook sesuai pilar & diambil/diadaptasi dari `config/hooks.yaml`; visual hook adalah adegan ber-`hook_potential` tertinggi; Critic memberi skor hook ≥ 4 |
| **Style benar** | tempo potongan, transisi, font, warna teks, mood musik, dan volume audio asli sesuai `config/styles/<preset>.yaml` — dicek otomatis oleh kode (bukan LLM) terhadap EDL & hasil render |
| **Teks & brand** | teks di zona aman, maks 2 baris, tanpa placeholder `[HARGA]`/`[ISI]` yang tersisa, logo & CTA (nomor WhatsApp dari `brand.yaml`) tampil |
| **Siap posting** | `caption.txt` + hashtag tersedia, thumbnail/cover dipilih, status job = `siap_unggah` |

---

## 2. Tech stack (tanpa GPU)

| Fungsi | Pilihan default | Catatan |
|---|---|---|
| Bahasa | Python 3.11+ | type hints, `pydantic` v2 |
| LLM "sutradara" & critic | API via `litellm` (Gemini / Groq / Claude / OpenAI) | provider & model dipilih via `.env`. Opsi uji coba: model lokal Ollama (`LOCAL_LLM_MODEL`, `LOCAL_VISION_MODEL`, mis. `ollama/qwen3:4b`, `ollama/qwen3-vl:4b-instruct`; lihat eval/riset_mesin_lokal_2026-11-20.md) dipanggil langsung ke API Ollama oleh `llm.py`. Groq (mis. `groq/openai/gpt-oss-120b`) cocok untuk Director/Critic (teks, cepat & murah); vision tetap via Gemini |
| Deskripsi visual (vision) | model multimodal via API yang sama | frame diperkecil ke ≤ 768 px, 1–3 frame per adegan |
| Transkripsi | `faster-whisper` di CPU (`small`, `compute_type="int8"`, bahasa `id`; model via `TRANSCRIBE_MODEL`) | audio didekode lewat ffmpeg; prompt kosakata dari `brand.yaml` (`transcribe_vocab`, layanan) & keyword pilar. Fallback opsional: API speech-to-text bila CPU terlalu lambat |
| Deteksi adegan | `PySceneDetect` (ContentDetector) | CPU |
| Kualitas frame | OpenCV: blur (variance of Laplacian), kecerahan, goyangan (optical flow sederhana) | CPU, untuk membuang footage jelek |
| Deteksi wajah & pelat (blur privasi) | YuNet & LPD-YuNet via OpenCV (`cv2.FaceDetectorYN`, `cv2.dnn`), model di `assets/models/` | CPU, tanpa paket baru; menggantikan rencana `mediapipe` (konflik `cv2`, tanpa detektor pelat) — lihat docs/arsitektur/adr/ADR-009 |
| Deteksi objek (crop pengikut subjek) | NanoDet-Plus (opencv_zoo, Apache 2.0) via `cv2.dnn`, model di `assets/models/` | CPU ±20 ms/frame proxy; motor/orang/mobil diikuti sepanjang adegan; tanpa model → saliency |
| Analisis audio | ffmpeg `silencedetect`, `librosa` (beat, energi) | |
| Render | `ffmpeg` (via `subprocess`, filter_complex) | subtitle/teks `.ass` via libass |
| CLI | `typer` | |
| UI sederhana (Tahap 5) | `gradio` | |
| Publikasi IG (Tahap 6) | Instagram Graph API resmi (Content Publishing, `media_type=REELS`) via `httpx` | butuh akun IG Profesional (Bisnis/Kreator) + Meta App + access token; tanpa library tidak resmi/otomasi browser |
| Penjadwalan (Tahap 6) | antrean lokal `publish/queue.json` + Windows Task Scheduler menjalankan `autoreels publish --due` tiap 5–10 menit | API IG tidak menyediakan jadwal bawaan; laptop harus menyala & online saat jadwal tiba |
| Animasi penuh (Racik Animasi) | Remotion 4 + React (Node), kit gaya `animasi/src/kit/` | `autoreels animasi prepare/stills/render`; skill `.claude/skills/racik-animasi`; render → importer (loudness, logo, caption dari file, checklist) |
| Footage + Remotion (Buat video, mesin "Claude + Remotion") | Remotion + `animasi/src/kit/Klip.tsx` & `TeksFootage.tsx`, `autoreels/footage_remotion.py` | `autoreels animasi footage` (ingest+analisis+klip H.264 kerja → `public/<nama>/data.json` mode `footage`), Claude Code headless (skill `.claude/skills/racik-footage`) memilih potongan dari lembar kontak & menulis komposisi, lalu `animasi render` → importer. Pilihan "Penyusun edit" di wizard (alur montase); keputusan pemilik 2026-11-26 karena style & potongan Gemini/Groq kurang bagus; Ruang Kerja menampilkan kerjanya |
| Tes | `pytest` | |
| Config | YAML (`pyyaml`) | |

Jangan menambah dependensi berat (PyTorch GPU, framework agent besar, model lokal) tanpa bertanya dulu.

---

## 3. Arsitektur pipeline

```
video mentah (1..n file) + instruksi pengguna + pilar konten
        │
        ▼
[1] INGEST ──── normalisasi (fps, audio 48k, rotasi), proxy 480p untuk analisis
        │
        ▼
[2] ANALYZE ─── adegan · skor kualitas (blur/gelap/goyang) · wajah & bbox · beat musik · (bila ada ucapan) transkrip per kata
        │        └─► work/<job_id>/analysis.json  (di-cache per hash file)
        ▼
[3] DESCRIBE ── vision LLM mendeskripsikan tiap adegan layak pakai: objek (motor, bangunan, pemandangan), aksi, suasana, potensi hook
        │        └─► work/<job_id>/descriptions.json
        ▼
[4] DIRECTOR ── LLM membaca: analysis + descriptions + instruksi + pilar konten + style preset + hook library + brand + brief tren
        │        └─► edl.json  (divalidasi skema pydantic, retry bila gagal)
        ▼
[5] VALIDATE ── aturan keras: timestamp valid, durasi sesuai target, hook ≤ 3 detik, potongan jatuh di beat (montase) atau batas kata (video bicara)
        │
        ▼
[6] CRITIC ──── (Tahap 4) LLM kedua menilai EDL dengan rubrik → saran revisi → DIRECTOR merevisi (maks 2 putaran)
        │
        ▼
[7] RENDER ──── potong · speed-ramp/timelapse · reframe 9:16 · teks overlay/subtitle · transisi · musik + ducking · logo · CTA · loudnorm
        │
        ▼
output/<job_id>/reel.mp4  +  edl.json  +  caption.txt (caption IG + hashtag lokal)  +  report.md (biaya, durasi proses)
```

### Detail per modul

**[1] Ingest** — terima satu atau beberapa file. Buat proxy 480p untuk analisis. Simpan metadata (durasi, fps, resolusi, rotasi, ada/tidaknya ucapan berdasarkan VAD).

**[2] Analyze**
- Adegan: `{scene_id, start, end}` via PySceneDetect.
- Skor kualitas per adegan: ketajaman, kecerahan, goyangan → adegan di bawah ambang ditandai `unusable`.
- Wajah/bbox per sampel frame (5 fps) → crop 9:16 mengikuti subjek, dihaluskan (moving average). Bila tidak ada wajah, gunakan *saliency* sederhana atau center crop.
- Beat & tempo dari musik yang dipilih → titik potong montase.
- Bila VAD mendeteksi ucapan: transkrip per kata, tandai kata pengisi ("eee", "emm", "anu") dan jeda > 0,6 detik.

**[3] Describe** — hanya untuk adegan layak pakai. Kirim 1–3 frame kecil per adegan. Output JSON per adegan: `subject`, `action`, `setting` (garasi, jalan, destinasi wisata, lokasi proyek, dapur), `mood`, `hook_potential` (0–5), `suggested_text` (opsional). Jangan mengarang nama tempat; bila tidak yakin, tulis `"tidak diketahui"`.

**[4] Director** — prompt dibangun dari `prompts/director.md` + template per pilar (`prompts/pillars/rental.md`, `konstruksi.md`, `profil.md`, `lowongan.md`). Output wajib JSON sesuai skema EDL (bagian 4). Gunakan *structured output*/JSON mode bila provider mendukung; jika tidak, parse + validasi + retry maks 3 kali dengan pesan error dimasukkan kembali ke prompt.

Struktur naratif default per pilar:
- **Rental motor:** hook visual (motor/pemandangan terbaik) → keunggulan (unit, harga, syarat mudah) → suasana perjalanan → CTA booking.
- **Konstruksi:** hook before–after singkat → proses kronologis (speed-up) → hasil akhir → kredibilitas → CTA konsultasi.
- **Profil/lowongan:** hook pertanyaan → poin utama (teks overlay) → CTA.

**[5] Validate** — aturan keras (bukan LLM): timestamp dalam rentang sumber; adegan `unusable` tidak boleh dipakai; durasi total ±10% dari target; segmen pertama ≤ 3 detik; potongan montase di-snap ke beat terdekat (±120 ms); potongan video bicara di-snap ke batas kata (±150 ms).

**[6] Critic** — rubrik 1–5: kekuatan hook, kesesuaian instruksi & pilar, alur/koherensi, tempo sesuai style, keterbacaan teks, kejelasan CTA, konsistensi brand. Rata-rata < 4 atau hook < 4 → catatan revisi ke Director (maks 2 putaran; revisi yang melanggar aturan keras ditolak). Versi dengan skor terbaik dipakai; hasil di `output/<job>/critic.json`. Critic gagal (API error) tidak menggagalkan job, tetapi dicatat di checklist.

**[7] Render**
- Output: 1080×1920, 30 fps, H.264 (`-preset veryfast -crf 20`), AAC 192 kbps.
- Reframe: crop mengikuti subjek; alternatif `blur_pad` untuk footage horizontal lebar (pemandangan, drone).
- Speed: `speed` per segmen (mis. 4–8× untuk progres proyek) via `setpts`.
- Teks/subtitle: file `.ass` sesuai style preset. Maks 2 baris, ±5 kata per baris. Zona aman: hindari ~15% atas dan ~20% bawah layar.
- Teks hook besar di 0–3 detik; teks harga/fitur/info sebagai overlay per segmen.
- Logo brand kecil di sudut (opsional, dari `config/brand.yaml`).
- Transisi: `xfade` sesuai style (cut, fade, slide, zoom-punch, whip).
- Audio: audio asli b-roll diredam (default −30 dB atau mute) bila bising; musik dari `assets/music/` berdasarkan `mood`; ducking otomatis saat ada ucapan (`sidechaincompress`); loudness akhir sekitar −14 LUFS (`loudnorm`, bisa diatur).
- Privasi: filter blur untuk wajah pelanggan/pelat nomor bila `privacy.blur_faces=true` di EDL.
- Render bisa diulang dari `edl.json` saja: `autoreels render --edl output/<job_id>/edl.json`.

---

## 4. Skema EDL (kontrak antara LLM dan renderer)

```json
{
  "version": "1.0",
  "pillar": "rental | konstruksi | profil | lowongan",
  "target_duration_sec": 20,
  "aspect": "9:16",
  "style_preset": "rental_energik",
  "hook": {
    "type": "visual_wow | pertanyaan | harga | before_after | angka | kontras",
    "overlay_text": "Liburan ke Garut? Nggak perlu bawa motor!",
    "source_segment_index": 0
  },
  "segments": [
    {
      "index": 0,
      "source_file": "raw_03.mp4",
      "start": 4.20,
      "end": 6.00,
      "role": "hook | isi | bukti | suasana | cta",
      "reason": "pemandangan terbaik dengan motor di depan, tajam dan terang",
      "reframe": "subject_track | center | blur_pad",
      "speed": 1.0,
      "transition_in": "cut | fade | slide_left | zoom_punch | whip",
      "overlay_text": null,
      "keep_original_audio": false
    }
  ],
  "subtitles": { "enabled": false, "style": "bold_putih_outline", "language": "id" },
  "music": { "mood": "upbeat | santai | inspiratif | dramatis | none", "volume_db": -14, "duck_under_speech": true, "cut_on_beat": true },
  "branding": { "logo": true, "position": "top_right" },
  "privacy": { "blur_faces": false, "blur_plates": false },
  "cta": { "text": "Booking sekarang via WhatsApp!", "at_sec": 17.0 },
  "caption_suggestion": "…",
  "hashtags": ["#rentalmotorgarut", "#wisatagarut", "#garut"],
  "notes_for_human": "Sarankan audio trending dari brief minggu ini ditambahkan manual saat unggah."
}
```

Definisikan skema ini sebagai model pydantic di `autoreels/edl.py` dan jadikan satu-satunya sumber kebenaran.

---

## 5. File konfigurasi yang dikelola pengguna

- `config/styles/*.yaml` — style preset. Field: `cut_pace_sec`, `transitions`, `text_style`, `font`, `colors`, `zoom_punch_on_emphasis`, `music_mood_default`, `original_audio_db`, `color_grade` (look), `color_match` (0–1, seragamkan warna antar klip), `subtitle_emphasis` (default true: angka/harga/promo/nama tempat di subtitle diberi warna `colors.emphasis` + pop; kata tambahan via `emphasis_words` di `brand.yaml`). Preset awal:
  - `rental_energik` — potongan cepat (0,6–1,2 dtk), ikut beat, zoom-punch, teks tebal.
  - `wisata_sinematik` — potongan lebih panjang (1,5–3 dtk), fade, warna hangat, musik santai/inspiratif.
  - `proyek_profesional` — before–after, speed-up, transisi bersih, teks rapi, musik inspiratif.
  - `info_lowongan` — teks overlay dominan, tempo sedang.
- `config/hooks.yaml` — 15–30 pola hook dalam bahasa Indonesia per pilar (mis. "Garut seindah ini kalau dijelajahi pakai motor", "Dari lahan kosong jadi…", "Sewa motor di Garut mulai Rp… /hari" [harga diisi manual]).
- `config/brand.yaml` — nama perusahaan, handle IG, warna, font, logo, nomor WhatsApp CTA, gaya bahasa, CTA default per pilar.
- `config/pillars.yaml` — daftar pilar, target audiens, struktur naratif default, hashtag dasar.
- `config/preferensi.md` — preferensi pemilik: "Ringkasan otomatis" (dirangkum AI dari editan, `autoreels preferensi --rangkum` / web Bahan AI → Preferensi) + "Catatan manual" (tidak pernah diubah AI). Dibaca Director.
- `trends/brief.md` — diisi manual mingguan: format yang sedang ramai, gaya hook yang naik, audio trending (judul saja), momen musiman (libur sekolah, long weekend, musim mudik, event di Garut). Director wajib membacanya dan **tidak boleh mengarang tren yang tidak tertulis**.
- `.env` — `LLM_PROVIDER`, `LLM_MODEL`, `VISION_MODEL`, API key (Gemini, Groq, dll.), serta untuk Tahap 6: `IG_TARGET` (`test`/`production`), `IG_TEST_USER_ID`, `IG_TEST_ACCESS_TOKEN` (akun decoy), `IG_USER_ID`, `IG_ACCESS_TOKEN` (`@contohbrand`). Jangan di-commit; sediakan `.env.example`.
- `config/schedule.yaml` — (Tahap 6) slot jam posting default per pilar (mis. rental: Jumat 18:00 & Sabtu 09:00 WIB), zona waktu `Asia/Jakarta`, dan aturan `require_approval: true`.

---

## 6. Struktur repository

```
autoreels/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── .env.example
├── main.py               # menu interaktif: buat Reel + ubah hook/hashtag/tren/brand/caption (default bila kosong); `--web` = buka Racik Studio; `--hp` = akses dari HP (PIN)
├── animasi/             # Racik Animasi: proyek Remotion (src/kit = kit + sistem gaya kit/gaya.json: racik-flat, garis-tipis, kertas, neon-malam, tipografi-tebal, pastel-ceria, grainy-gradient; aturan anti-PPT dari vendor/bang-motion di skill racik-animasi; src/videos/<nama>/ = kode per video ditulis Claude Code; public/ diisi `autoreels animasi prepare`, tidak di-commit)
├── vendor/              # rujukan pihak ketiga (git clone, di-.gitignore): claude-animated-shorts (utama), bang-motion (anti-PPT, arah gaya), remotion-skills (sumber skill remotion-best-practices), motion-skills, hyperframes, remotion-claude-video, awesome-claude-video, threejs-skills
├── frontend/             # Racik Studio UTAMA (nama UI "Racik" = APP_NAME di src/lib/constants.js): React + Vite + Tailwind; dist/ ikut di-commit
│   └── src/              # App.jsx (kerangka) · state/studio.jsx (state & API) · pages/ (create/, materials/, Riwayat + impor) · components/ (ui, PhraseEditor, …) · lib/ (konstanta, format, mock) · assets/fonts/
├── ui/                   # cadangan tanpa build (Alpine.js), dipakai server bila frontend/dist tidak ada; kontrak API di docs/gemini_ui_brief.md
├── docs/                 # arsitektur/ (README, diagram .mmd/.drawio/.xml, adr/), brief UI Gemini, panduan video-use
├── autoreels/
│   ├── cli.py            # typer: run (--engine, --clip, --blur-*, --narasi, --bicara, --tujuan, --tanpa-musik, --tanpa-logo, --tanpa-critic), cuplikan, prepare, finish, import, render, transcribe, analyze, validate, styles, status, studio, eval
│   ├── ingest.py
│   ├── analyze/
│   │   ├── scenes.py
│   │   ├── quality.py
│   │   ├── subjects.py   # saliency untuk crop (cadangan bila tak ada objek)
│   │   ├── objects.py    # NanoDet (opencv_zoo) → motor/orang/mobil; jalur crop pengikut subjek per adegan (Scene.crop_path)
│   │   ├── moments.py    # skor momen per sampel (subjek utuh, tajam, stabil) → Director tahu momen terbaik; validasi menggeser b-roll ke sana
│   │   ├── audio.py      # beat, VAD, silence
│   │   └── transcribe.py
│   ├── describe.py
│   ├── director.py
│   ├── critic.py         # rubrik 1–5 + catatan revisi; loop revisi (maks 2) dijalankan director.direct
│   ├── review.py         # cek visual video jadi: frame reel.mp4 → vision (prompts/visual_review.md) → visual_review.json + butir checklist (masalah berat = perlu tinjau)
│   ├── preferences.py    # belajar dari editan: edl_ai.json (versi AI) vs edl.json saat render ulang → edits.json → rangkum (prompts/preferences.md) → config/preferensi.md → konteks Director `preferensi_pemilik`
│   ├── evaluate.py       # `autoreels eval`: rangkum job/set uji → eval/report.md + results.csv
│   ├── animasi.py        # Racik Animasi: `animasi prepare` (narasi bersih + timing kata → animasi/public/<nama>/data.json; `--rentang` potong & sambung bagian rekaman, mis. podcast), `stills` (satu bundle, frame diam + lembar), `musik`, `cek` (tsc), `render` (Remotion → importer: caption.json, tanpa watermark default, pilar umum = informasi tanpa CTA; tanpa API)
│   ├── musik_sintesis.py # musik orisinal: Claude menulis partitur musik.json (bpm, kunci, progresi, bagian energi, aksen, sfx) → numpy (pad, bass, drum, arp, marimba) + trek SFX terpisah
│   ├── server_animasi.py # API web Racik Animasi (/api/animasi…): siapkan suara, edit transkrip, jalankan Claude Code headless (`claude -p`, login langganan — ANTHROPIC_API_KEY dibuang dari env anak), frame, render
│   ├── manual.py         # mode Claude Code sebagai sutradara (skill .claude/skills/racik-sutradara): `prepare` (bahan + lembar kontak + konteks.md) → Claude menulis deskripsi/EDL/critic → `finish` (validasi, render, checklist)
│   ├── validate.py
│   ├── edl.py            # skema pydantic
│   ├── render/
│   │   ├── cut.py
│   │   ├── reframe.py
│   │   ├── text_ass.py
│   │   ├── overlays.py   # hook, CTA, logo
│   │   ├── transitions.py
│   │   ├── privacy.py
│   │   ├── behind.py     # teks hook di belakang orang: mask PP-HumanSeg (opencv_zoo) selama hook, kepala menutup bagian bawah huruf saja; `hook_behind` per style, otomatis hook biasa bila tak pas
│   │   ├── speaker.py    # crop 9:16 ke pembicara aktif (YuNet + gerak bibir; per shot kamera)
│   │   ├── color.py      # warna seragam antar klip sebelum look gaya: pencilan kecerahan (gamma), rona dari piksel abu-abu (±5%), saturasi pucat; `color_match` per style
│   │   ├── sfx.py        # efek suara transisi buatan sendiri (whoosh/thump/pop, assets/sfx/); `sfx_db` per style. Stabilisasi adegan goyang (vidstab) di cut.py, `stabilize` per style
│   │   └── audio_mix.py
│   ├── publish/          # (Tahap 6)
│   │   ├── instagram.py  # klien Instagram Graph API (upload Reels, status, publish)
│   │   ├── queue.py      # antrean & status job: draft → siap_unggah → disetujui → terjadwal → terposting / gagal
│   │   └── scheduler.py  # `publish --due` + pendaftaran Windows Task Scheduler
│   ├── config_editor.py  # ubah config (hook, hashtag, brand, tren, caption) tanpa merusak komentar YAML
│   ├── highlights.py     # cari cuplikan: video bicara panjang → semua kandidat 1–3 menit yang layak (maks 20; "Cari ulang" mencari bagian lain) (prompts/highlight_find.md), batas kalimat, potong ke footage/<folder>/cuplikan/
│   ├── talk.py           # Tahap 3 video bicara: kalimat, buang take ulang, AI memilih kalimat (prompts/talk_select.md), frasa sinkron bibir (Phrase.src_start)
│   ├── narration.py      # alur "narasi dulu": rekaman narasi → transkrip bersih → koreksi AI (prompts/transcript_fix.md, hanya salah dengar) → draf diperiksa manusia di web (work/_narasi/<id>/) → frasa (segmen i ↔ frasa i), prompt prompts/director_narasi.md
│   ├── voiceover.py      # voice over: naskah AI (ditinjau manusia), rekaman suara sendiri (utama) / Gemini TTS, ducking, subtitle
│   ├── importer.py       # `autoreels import`: video jadi (video-use/editor lain) → normalisasi, logo, CTA, caption, checklist
│   ├── server.py         # backend FastAPI AutoReels Studio (127.0.0.1): API + antrean job + penyaji ui/ & media
│   ├── checklist.py      # Checklist Siap Unggah (video, hook, style, teks)
│   ├── pipeline.py       # orkestrasi ingest → render + report.md
│   ├── progress.py       # progress real-time (work/<job>/progress.json, `autoreels status`)
│   ├── media.py          # helper ffmpeg/ffprobe (perintah gagal → tampilkan perintah + stderr)
│   ├── llm.py            # wrapper litellm + retry + cache + pencatat biaya
│   └── config.py
├── prompts/
│   ├── director.md
│   ├── critic.md
│   ├── describe.md
│   └── pillars/ (rental.md, konstruksi.md, profil.md, lowongan.md)
├── config/  (styles/, hooks.yaml, brand.yaml, pillars.yaml)
├── trends/brief.md
├── assets/  (music/, fonts/, logo/)
├── eval/
│   ├── testset/manifest.csv   # daftar video uji (file video tidak di-commit)
│   ├── rubric.md
│   ├── run_eval.py
│   └── riset_*.md             # catatan riset (mis. mesin lokal vs API, 2026-11-20)
├── tests/
├── work/   (cache, di-.gitignore)
└── output/ (di-.gitignore)
```

---

## 7. Tahapan pengerjaan (kerjakan berurutan, satu tahap per sesi)

**Tahap 0 — Fondasi**
Setup repo, `pyproject.toml`, `.env.example`, skema EDL, wrapper LLM via API (tanpa Ollama), CLI kosong, tes dasar.
*Selesai bila:* `autoreels --help` berjalan dan tes skema EDL lulus.

**Tahap 1 — MVP montase b-roll (pilar Rental Motor)**
Ingest → deteksi adegan → skor kualitas → describe via vision API → Director memilih hook + urutan → potong ikut beat → reframe 9:16 → teks hook & CTA → musik.
*Selesai bila:* 5–15 klip mentah motor/perjalanan menjadi Reel 15–30 detik dalam satu perintah:
`autoreels run --input footage/rental/ --pillar rental --brief "Promo sewa motor untuk wisatawan libur akhir tahun" --style rental_energik --duration 20`

**Tahap 2 — Gaya, brand & pilar Konstruksi**
Style preset YAML, logo, transisi `xfade`, speed-up/timelapse, mode before–after, ducking & loudnorm, caption + hashtag, blur privasi.
*Selesai bila:* footage progres proyek menjadi Reel before–after, dan klip yang sama dirender dengan 2 preset berbeda menghasilkan nuansa yang jelas berbeda.

**Tahap 3 — Video berbicara**
Deteksi ucapan → transkrip CPU → buang jeda & kata pengisi → subtitle karaoke → gabung dengan b-roll (testimoni pelanggan, penjelasan layanan, info lowongan).
*Selesai bila:* video penjelasan 1–3 menit menjadi Reel 30–45 detik bersubtitle akurat dengan sisipan b-roll.

**Tahap 4 — Critic loop & evaluasi**
Critic dengan rubrik, revisi maks 2 putaran, skrip `eval/run_eval.py` → `eval/report.md`: waktu proses, biaya API, skor rubrik, jumlah revisi, error.

**Tahap 5 — UI sederhana**
Gradio: unggah video, pilih pilar & style, tulis instruksi, preview, edit teks hook/CTA di EDL, render ulang, unduh MP4 + caption.

**Tahap 6 — Posting terjadwal & koneksi Instagram**
- Prasyarat (dilakukan pemilik): `@contohbrand` **sudah akun Bisnis**. Buat Meta App di developers.facebook.com, dapatkan `IG_USER_ID` + access token jangka panjang dengan izin publikasi konten.
- **Dua akun terpisah:** akun **decoy** (uji coba, juga harus akun Profesional) dan akun **produksi** `@contohbrand`. Kredensial di `.env`: `IG_TEST_USER_ID`/`IG_TEST_ACCESS_TOKEN` dan `IG_USER_ID`/`IG_ACCESS_TOKEN`. Default selalu ke akun decoy (`IG_TARGET=test`); posting ke akun produksi hanya bila `IG_TARGET=production` diset eksplisit, dan CLI menampilkan nama akun tujuan sebelum posting. Semua uji pengembangan & otomatis wajib ke akun decoy.
- **Persetujuan manusia wajib** (keputusan pemilik): `require_approval: true` tidak boleh dimatikan untuk akun produksi.
- `autoreels schedule --job <id> --at "2026-12-20 18:00"` (atau slot otomatis dari `config/schedule.yaml`) → masuk antrean hanya bila job lolos Checklist Siap Unggah.
- **Persetujuan manusia** sebelum terposting: `autoreels approve --job <id>`; preview video + caption ditinjau dulu.
- `autoreels publish --due` (dipanggil Windows Task Scheduler): unggah video ke IG via API resmi (resumable upload), tunggu status `FINISHED`, publish dengan caption + hashtag, catat permalink & waktu posting ke `report.md`.
- Gagal (token kedaluwarsa, batas harian API, jaringan) → retry terbatas, status `gagal` + alasan; tidak ada posting ganda (idempoten).
- Pengingat token kedaluwarsa (token jangka panjang ±60 hari).
- Mode cadangan tanpa koneksi IG: ekspor paket unggah (MP4 + caption + jadwal) untuk dijadwalkan manual di Meta Business Suite.
- Keterbatasan: audio trending IG tidak bisa ditambahkan lewat API — video terposting otomatis memakai musik bebas royalti yang sudah dirender.
*Selesai bila:* satu Reel lolos checklist, disetujui, dan terposting otomatis ke **akun decoy** pada jam yang dijadwalkan; baru setelah itu pemilik boleh beralih ke `IG_TARGET=production`.

---

## 8. Aturan kerja untuk Claude Code

- Sebelum menulis kode di tiap tahap, tampilkan rencana singkat (file yang dibuat/diubah) lalu kerjakan.
- Uji setiap modul dengan video pendek; bila belum ada video asli, buat video sintetis dengan `ffmpeg -f lavfi`.
- Semua panggilan LLM lewat `autoreels/llm.py`; cache respons berdasarkan hash prompt + gambar; catat token dan estimasi biaya per job di `report.md`.
- Model lokal hanya lewat Ollama sebagai mesin opsional `local` (tidak pernah default, tanpa cadangan diam-diam ke API agar hasil uji murni). Bila suatu langkah terlalu lambat di CPU, usulkan alternatif API dan tanyakan dulu.
- Prompt LLM disimpan sebagai file di `prompts/`, bukan string panjang di kode.
- Bahasa antarmuka, log untuk pengguna, dan output caption: **bahasa Indonesia**. Nama variabel/fungsi: bahasa Inggris.
- Jangan menulis scraper media sosial, jangan mengunduh musik berhak cipta, jangan meng-commit API key atau token Instagram.
- Jangan pernah memposting ke Instagram tanpa job lolos Checklist Siap Unggah dan (bila `require_approval: true`) disetujui manusia.
- Jangan mengarang fakta bisnis (harga sewa, nama proyek, klien). Ambil dari `config/brand.yaml` atau instruksi pengguna; bila tidak ada, beri placeholder `[HARGA]`.
- Bila perintah FFmpeg gagal, tampilkan perintah lengkap dan stderr.
- Jangan menambah fitur di luar tahap yang sedang dikerjakan tanpa konfirmasi.
- Jaga kerapian file (permintaan pemilik): root hanya berisi file inti (`main.py`, `README.md`, `CLAUDE.md`, `pyproject.toml`, `requirements.txt`, `.env*`) dan folder proyek. Setiap file langsung ditaruh di foldernya; musik masuk `assets/music/<mood>/` (buat mood baru bila tidak ada yang cocok — ingat menambahkannya juga ke `MusicMood` di `edl.py` dan `MOOD_FALLBACK` di `analyze/audio.py`), nama file huruf kecil tanpa spasi.
- UI: daftar yang bisa > 8 baris (subtitle, lagu, cuplikan, dsb.) wajib ringkas — kotak setinggi tetap + saring/cari, tampilan bawaan sesingkat mungkin; opsi jarang dipakai masuk panel lipat (permintaan pemilik). Pakai komponen bersama (mis. `components/PhraseEditor.jsx`) dan skill `react-expert`/`frontend-design`.
- UI dwibahasa: komponen ditulis dalam bahasa Indonesia; terjemahan Inggris di `frontend/src/lib/en.js` (kunci = teks Indonesia, diterapkan `lib/i18n.js`). Setiap teks UI baru wajib ditambahkan ke `en.js`; isi buatan pengguna (caption, hook, tren, log) diberi `translate="no"`.
- Tangani kombinasi pilar × alur × footage (what-if): footage yang tidak cocok dengan alur harus diberi saran/ditolak sejak awal (web + server), bukan gagal di tengah job.
- Setelah mengubah frontend, jalankan `npm run build` agar `frontend/dist` ikut diperbarui; setelah mengubah backend, ingatkan pengguna untuk menjalankan ulang server (`python main.py --web`).

---

## 9. Evaluasi (untuk keperluan riset/laporan)

- **Set uji:** 20–50 kumpulan footage mentah Brand (minimal per pilar: rental, konstruksi, video bicara) + 10–20 Reels referensi gaya.
- **Metrik otomatis:** waktu proses, biaya API per video, ketepatan durasi, hook ≤ 3 detik, persentase potongan tepat di beat, akurasi transkrip (WER, Tahap 3).
- **Metrik manusia:** rubrik 1–5 oleh penilai (kesesuaian instruksi, daya tarik hook, alur, estetika, keterbacaan teks, kejelasan CTA), dibandingkan dengan baseline (CapCut auto-edit / editor manusia).
- **Metrik lapangan (setelah unggah):** retensi 3–5 detik pertama, rata-rata waktu tonton, share, save, serta jumlah chat/booking yang masuk dari Reels (khusus pilar rental). Konsep retensi awal sejalan dengan metrik *Engagement Continuation Rate* (penonton yang bertahan > 5 detik) pada riset SnapUGC (Li et al., ECCV 2024).

---

## 10. Rujukan desain (dasar ilmiah arsitektur)

- **LAVE** (Wang et al., IUI 2024) — footage dideskripsikan ke bahasa, lalu agen LLM merencanakan dan mengeksekusi aksi edit. → dasar modul Describe + Director.
- **EditDuet** (Sandoval-Castañeda et al., SIGGRAPH 2025) — agen Editor + agen Critic yang saling memberi umpan balik. → dasar modul Critic.
- **VC-LLM** (Qian et al., arXiv 2025) — video iklan pendek otomatis dari footage mentah dengan multimodal LLM. → paling dekat dengan pilar Rental (promosi produk/jasa dari b-roll).
- **CutClaw** (arXiv 2026) — editing footage panjang menjadi video pendek yang sinkron dengan ritme musik. → dasar potong-ikut-beat.
- **Write-A-Video** (Wang et al., ACM TOG 2019) — pencocokan teks–shot dan idiom sinematik untuk tempo. → dasar style preset.
- **Tools for Placing Cuts and Transitions in Interview Video** (Berthouzoz, Li & Agrawala, ACM TOG 2012) — penyuntingan berbasis transkrip. → dasar Tahap 3.
- **QVHighlights / Moment-DETR** (Lei et al., NeurIPS 2021) — deteksi momen & highlight berbasis kueri bahasa. → acuan bila nanti melatih model highlight.
- **SnapUGC** (Li et al., ECCV 2024) — pentingnya detik-detik awal video pendek. → dasar aturan hook.
- **video-use** (github.com/browser-use/video-use, MIT) — editor video berbasis percakapan (transkrip per kata + EDL + self-eval). → mode kedua untuk video bicara (diimpor via `autoreels import`) dan rujukan untuk Tahap 2–4: color grade (`grade.py`), fade audio 30 ms, potong di batas kata, cek render di tiap titik potong.
