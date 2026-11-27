# Brief Desain: Web UI "AutoReels Studio"

> Salin seluruh isi file ini ke Gemini. Tugas Gemini: **frontend saja** (HTML/CSS/JS).
> Backend API sudah/akan dibuat terpisah dan mengikuti kontrak di bagian 5 — **jangan ubah nama endpoint atau bentuk JSON-nya.**

---

## 1. Konteks

**AutoReels** adalah sistem internal **Contoh Brand** (Garut, Jawa Barat) yang mengubah **video mentah** menjadi **Instagram Reels siap unggah** secara otomatis: AI memilih adegan terbaik, membuat hook 3 detik pertama, memotong mengikuti beat musik, menambah teks, logo, CTA WhatsApp, lalu memeriksa kualitas dengan *Checklist Siap Unggah*.

Saat ini semuanya dijalankan lewat terminal — membingungkan bagi pengguna. Kita butuh **web UI lokal** yang interaktif, cantik, dan mudah.

**Pengguna:** staf marketing/SEO non-teknis. Bahasa antarmuka: **Bahasa Indonesia** santai-sopan. Dipakai di laptop (desktop utama), tetap rapi di layar kecil.

**Pilar konten:** `rental` (Rental Motor — prioritas), `konstruksi`, `profil`, `lowongan`.

---

## 2. Batasan teknis

- **Tanpa build step.** File statis saja di folder `ui/`:
  - `ui/index.html`
  - `ui/app.js`
  - `ui/styles.css` (opsional, bila Tailwind tidak cukup)
- Boleh pakai CDN (versi dikunci):
  - Tailwind CSS Play CDN: `https://cdn.tailwindcss.com`
  - Alpine.js 3.14.1: `https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js`
  - Font Google: **Plus Jakarta Sans** (UI) dan **Montserrat** (judul/aksen)
  - Ikon: Lucide 0.460.0 (`https://unpkg.com/lucide@0.460.0/dist/umd/lucide.min.js`) atau SVG inline
- **Jangan** pakai React/Vue CLI/npm/bundler. Jangan membuat kode backend.
- Semua request ke API memakai path relatif `/api/...` (UI dan API disajikan dari server lokal yang sama, mis. `http://localhost:8000`).
- **Wajib ada mode MOCK**: `const USE_MOCK = true;` di awal `app.js`. Bila `true`, semua panggilan API memakai data contoh di bagian 5 (termasuk simulasi progress 0→100% selama ±20 detik) agar UI bisa dicoba tanpa backend. Bila `false`, panggil API sungguhan.
- Satu fungsi pusat `api(method, path, body)` untuk semua request; tampilkan error dengan rapi (toast) memakai field `error` dari respons.

---

## 3. Arah desain visual

- **Nuansa:** studio kreatif modern — bersih, lega, profesional, sedikit "playful" saat proses berjalan. Bukan dashboard korporat yang kaku.
- **Warna brand** (dari logo Brand):
  - Hijau `#00953F` → aksi utama, sukses
  - Ungu tua `#2B176E` → header/aksen, latar mode gelap
  - Merah `#D9261C` → gagal/peringatan kritis (hemat dipakai)
  - Kuning sorotan `#FFC400` → highlight (sama dengan warna highlight teks di video)
  - Netral: putih, abu-abu lembut; dukung **mode gelap** (toggle, ingat pilihan di `localStorage`).
- **Tipografi:** Montserrat ExtraBold untuk judul besar, Plus Jakarta Sans untuk isi.
- Sudut membulat (rounded-2xl), bayangan halus, animasi transisi ringan (≤ 200 ms). Hormati `prefers-reduced-motion`.
- **Preview video** selalu dalam **bingkai ponsel 9:16** (mockup HP sederhana), dengan toggle **"Tampilkan zona aman Reels"** yang menggelapkan ±15% atas dan ±20% bawah layar.
- Aksesibilitas: kontras cukup, semua tombol bisa dipakai keyboard, label pada setiap input.

---

## 4. Struktur halaman & alur

Navigasi samping (sidebar; di layar kecil jadi menu bawah):
1. **Buat Reel** (halaman utama)
2. **Riwayat**
3. **Pustaka Hook**
4. **Hashtag & Keyword**
5. **Brief Tren**
6. **Brand & Caption**

### 4.1 Buat Reel — wizard 4 langkah (stepper di atas)

**Langkah 1 — Footage**
- Pilih pilar (4 kartu besar dengan ikon: motor, helm/crane, gedung, koper/kerja).
- Dua cara memberi footage:
  - **Unggah** drag-and-drop banyak file video (.mp4/.mov) → `POST /api/footage/upload`, tampilkan progress unggah per file.
  - **Pakai folder yang ada** → dropdown dari `GET /api/options` (`footage_folders`, tampilkan jumlah video).
- Tampilkan grid thumbnail klip (`GET /api/footage?folder=...`) dengan durasi & resolusi. Bila 0 klip → pesan ramah + tombol unggah.

**Langkah 2 — Atur**
- **Instruksi** (textarea, terisi default sesuai pilar, mis. "Promo sewa motor untuk wisatawan yang mau keliling Garut").
- **Style** — kartu pilihan per preset (nama, deskripsi, tempo potongan, mood musik); default sesuai pilar.
- **Durasi** — slider 8–90 detik (default 20) + chip cepat 15 / 20 / 30 / 45.
- **Teks hook** (opsional) — placeholder "Kosongkan → dipilih AI". **Penghitung langsung**: kata (maks 5) & huruf (maks 28); berubah merah + pesan "Kepanjangan, teks akan tampil kecil" bila lewat. Di bawahnya chip saran dari pustaka hook pilar tsb (klik → isi).
- **Teks CTA** (opsional) — placeholder memakai CTA default brand.
- **Musik** — "Otomatis sesuai style" (default) atau pilih lagu (dengan tombol ▶ putar 10 detik pratinjau dari `url`).
- Panel ringkasan di kanan + tombol besar **"Buat Reel 🎬"** → `POST /api/jobs`.

**Langkah 3 — Proses** (polling `GET /api/jobs/{id}/progress` tiap 1 detik)
- Lingkaran/bar progress besar dengan **persen**, **waktu berjalan**, dan **label langkah aktif** (6 langkah: Ingest & proxy → Analisis adegan & musik → Deskripsi visual (AI) → Director menyusun edit (AI) → Render video → Checklist Siap Unggah).
- Timeline vertikal 6 langkah: selesai (✓ hijau), aktif (animasi), menunggu (abu).
- Teks `detail` di bawah (mis. "adegan 9–16 dari 38").
- Pesan menunggu yang ramah bila log berisi "[menunggu]" (rate limit AI): "AI sedang sibuk, sistem menunggu lalu mencoba lagi otomatis…".
- Panel **Log** yang bisa dibuka/tutup (font monospace, auto-scroll).
- `state`: `berjalan` | `selesai` | `gagal`. Saat `selesai` → otomatis ke Langkah 4. Saat `gagal` → kartu error berisi `error` + tombol "Coba lagi" dan "Lihat detail" (menampilkan `log`).

**Langkah 4 — Hasil** (`GET /api/jobs/{id}`)
- Kiri: **video di bingkai ponsel** (autoplay muted, loop, kontrol) + toggle zona aman.
- Kanan atas: **badge status** besar — `siap_unggah` → "✅ Siap Unggah" (hijau); `perlu_tinjau` → "⚠️ Perlu Tinjau" (kuning) beserta daftar butir yang gagal.
- Kartu statistik: durasi, jumlah potongan, ketepatan beat (%), biaya API (USD), waktu proses.
- **Checklist** dikelompokkan per `group` (Video jadi / Hook benar / Style benar / Teks & brand / Siap posting) — ✅ lolos, ❌ gagal wajib, ⚠️ catatan (bila `required=false`). Grup yang semua lolos boleh dilipat.
- **Caption**: kotak teks + tombol **"Salin caption"** (caption + hashtag) dengan toast "Tersalin!".
- **Edit & render ulang** (tanpa biaya AI): input teks hook (dengan penghitung yang sama), CTA, dan teks overlay tiap segmen yang punya teks → `POST /api/jobs/{id}/rerender` → kembali ke tampilan Proses.
- Tombol: **Unduh MP4**, **Unduh cover**, **Buka laporan** (render `report_md` sebagai markdown sederhana di modal), **Buat Reel baru**.
- Catatan kecil: "Audio trending Instagram ditambahkan manual di aplikasi IG saat unggah."

### 4.2 Riwayat
- Grid kartu job terbaru (`GET /api/jobs`): cover 9:16, tanggal, pilar, hook, status badge, durasi. Klik → halaman Hasil job itu. Filter pilar & status.

### 4.3 Pustaka Hook (`GET/PUT /api/config/hooks`)
- Tab per pilar. Daftar hook (teks + tipe sebagai chip warna). Tambah (input + pilih tipe + penghitung 5 kata/28 huruf), edit inline, hapus (konfirmasi). Tombol **Simpan** (PUT seluruh objek).
- Penjelasan tipe hook singkat (tooltip): visual_wow, pertanyaan, harga, before_after, angka, kontras.

### 4.4 Hashtag & Keyword (`GET/PUT /api/config/pillars/{pillar}`)
- Tab per pilar. Input **tag chip** untuk hashtag (otomatis huruf kecil, tanpa spasi, diawali #) dan keyword SEO (frasa). Simpan.

### 4.5 Brief Tren (`GET/PUT /api/config/trends`)
- 5 bagian daftar poin (tambah/hapus baris): Format yang sedang ramai, Gaya hook yang naik, Audio trending (judul saja), Momen musiman/event Garut, Catatan lain. Tampilkan `updated` ("Diperbarui: …"). Tombol "Kosongkan semua" (AI akan mengabaikan tren).

### 4.6 Brand & Caption
- `GET/PUT /api/config/brand`: harga sewa per hari (teks; info: "Biarkan [HARGA] bila belum pasti — AI tidak akan menyebut harga"), CTA default per pilar. Nomor WA & IG tampil read-only.
- `GET/PUT /api/config/caption-guide`: sapaan, emoji, bahasa Sunda, kata dihindari, panjang, dan 0–3 contoh caption.

---

## 5. Kontrak API (JSON)

Semua respons JSON. Error → status 4xx/5xx dengan `{ "error": "pesan bahasa Indonesia", "detail": "opsional (mis. stderr ffmpeg)" }`.

### `GET /api/options`
```json
{
  "pillars": [
    {"id": "rental", "label": "Rental Motor", "default_style": "rental_energik",
     "default_brief": "Promo sewa motor untuk wisatawan yang mau keliling Garut"},
    {"id": "konstruksi", "label": "Konstruksi", "default_style": "proyek_profesional",
     "default_brief": "Tampilkan progres proyek dari awal sampai selesai"},
    {"id": "profil", "label": "Profil & Jasa", "default_style": "info_lowongan",
     "default_brief": "Perkenalkan layanan Contoh Brand"},
    {"id": "lowongan", "label": "Lowongan", "default_style": "info_lowongan",
     "default_brief": "Info lowongan kerja di Contoh Brand"}
  ],
  "styles": [
    {"id": "rental_energik", "description": "Energik untuk promo rental motor",
     "cut_pace_sec": [0.6, 1.2], "music_mood_default": "upbeat"},
    {"id": "wisata_sinematik", "description": "Sinematik untuk suasana perjalanan wisata Garut",
     "cut_pace_sec": [1.5, 3.0], "music_mood_default": "santai"}
  ],
  "music": [
    {"path": "upbeat/mixkit-pop-05-695.mp3", "mood": "upbeat", "name": "mixkit-pop-05-695", "url": "/media/music/upbeat/mixkit-pop-05-695.mp3"}
  ],
  "footage_folders": [{"path": "footage/rental", "count": 9}],
  "default_cta": {"rental": "Booking sekarang via WhatsApp (000) 0000000!"},
  "hook_limits": {"max_words": 5, "max_chars": 28}
}
```

### `POST /api/footage/upload` (multipart: `pillar`, `files[]`)
```json
{"folder": "footage/rental", "files": ["klip1.mp4", "klip2.mp4"]}
```

### `GET /api/footage?folder=footage/rental`
```json
{"folder": "footage/rental", "clips": [
  {"name": "mixkit-biker-starting-his-motorcycle.mp4", "duration": 11.4, "width": 1280, "height": 720,
   "size_mb": 6.1, "thumb_url": "/media/thumbs/ab12cd.jpg"}
]}
```

### `POST /api/jobs`
Body:
```json
{"input_path": "footage/rental", "pillar": "rental", "brief": "Promo sewa motor …",
 "style": "rental_energik", "duration": 20, "hook_text": null, "cta_text": null, "music_file": null}
```
Respons: `{"job_id": "20261118-155444-rental"}`

### `GET /api/jobs/{job_id}/progress`
```json
{"job_id": "20261118-155444-rental", "percent": 43.9, "step": "describe",
 "step_label": "Deskripsi visual (AI)", "step_index": 3, "steps_total": 6,
 "detail": "adegan 25–32 dari 38", "elapsed_sec": 100.2, "state": "berjalan",
 "error": null,
 "log": ["Job 20261118-155444-rental", "[1/7] Ingest …", "  musik: mixkit-gimme-that-groove-872.mp3 — 112 BPM"]}
```
`step` ∈ `ingest | analyze | describe | direct | render | checklist`. `state` ∈ `berjalan | selesai | gagal`.

### `GET /api/jobs`
```json
{"jobs": [
  {"job_id": "20261118-155444-rental", "created": "2026-11-18 15:54:44", "pillar": "rental",
   "status": "siap_unggah", "hook_text": "Keliling Garut Pakai Motor", "duration": 20.3,
   "cover_url": "/media/output/20261118-155444-rental/cover.jpg"}
]}
```

### `GET /api/jobs/{job_id}`
```json
{
  "job_id": "20261118-155444-rental",
  "status": "siap_unggah",
  "pillar": "rental", "style": "rental_energik", "brief": "Promo sewa motor …",
  "reel_url": "/media/output/20261118-155444-rental/reel.mp4",
  "cover_url": "/media/output/20261118-155444-rental/cover.jpg",
  "caption": "Liburan akhir tahun di Garut nggak perlu bingung soal kendaraan…\n\n📲 Booking & info: WhatsApp (000) 0000000\n📍 Garut, Jawa Barat\n\n#rentalmotorgarut #wisatagarut #garut",
  "stats": {"total_duration": 20.33, "segments": 15, "hook_duration": 2.13,
            "beat_accuracy": 1.0, "cost_usd": 0.0087, "process_sec": 192},
  "checklist": [
    {"group": "Video jadi", "name": "Resolusi 1080×1920", "passed": true, "required": true, "detail": "1080×1920"},
    {"group": "Hook benar", "name": "Teks hook cukup besar (≥ 90 px, ≤ 2 baris)", "passed": true, "required": true, "detail": "118 px, 2 baris"},
    {"group": "Style benar", "name": "Semua transisi bisa dirender", "passed": false, "required": false, "detail": "segmen [5] dirender sebagai cut"}
  ],
  "edl": {
    "hook_text": "Keliling Garut Pakai Motor",
    "cta_text": "Booking motor via WhatsApp sekarang!",
    "segments": [
      {"index": 0, "role": "hook", "source_file": "mixkit-biker….mp4", "start": 0.0, "end": 2.13, "overlay_text": null},
      {"index": 1, "role": "isi", "source_file": "101506-video-720.mp4", "start": 10.44, "end": 11.64, "overlay_text": "Unit Terawat Aman"}
    ]
  },
  "report_md": "# Laporan Job …"
}
```

### `POST /api/jobs/{job_id}/rerender`
Body: `{"hook_text": "Liburan ke Garut?", "cta_text": "Hayu booking via WA!", "segment_texts": {"1": "Unit terawat"}}`
Respons: `{"job_id": "20261118-155444-rental"}` → lanjut polling progress.

### Config
| Method & path | Body / respons |
|---|---|
| `GET/PUT /api/config/hooks` | `{"rental": [{"type": "pertanyaan", "text": "Liburan ke Garut?"}], "konstruksi": [], "profil": [], "lowongan": []}` |
| `GET/PUT /api/config/pillars/{pillar}` | `{"hashtags": ["#rentalmotorgarut"], "keywords": ["sewa motor garut"]}` |
| `GET/PUT /api/config/trends` | `{"updated": "2026-11-19", "formats": [], "hooks": [], "audio": [], "moments": [], "notes": []}` |
| `GET/PUT /api/config/brand` | `{"price_per_day": "[HARGA]", "whatsapp": "(000) 0000000", "instagram": "@contohbrand", "default_cta": {"rental": "…", "konstruksi": "…", "profil": "…", "lowongan": "…"}}` (PUT: hanya `price_per_day` & `default_cta`) |
| `GET/PUT /api/config/caption-guide` | `{"fields": {"Sapaan": "kamu", "Emoji": "secukupnya", "Bahasa Sunda": "ya, ringan", "Kata dihindari": "termurah", "Panjang": "2–4 kalimat"}, "examples": ["…"]}` |

PUT berhasil → `{"ok": true}`.

---

## 6. Detail kecil yang membuat beda

- Penghitung hook (5 kata / 28 huruf) tampil di **semua** tempat input hook.
- Tombol utama tidak bisa diklik dua kali (disable + spinner saat request).
- Saat proses berjalan, judul tab browser menampilkan persen, mis. `(44%) AutoReels`.
- Konfirmasi sebelum meninggalkan halaman saat ada perubahan config yang belum disimpan.
- Toast sukses/gagal di pojok kanan bawah, hilang otomatis 3 detik.
- Empty state yang ramah dengan ilustrasi SVG sederhana (mis. ikon film + teks "Belum ada Reel. Yuk buat yang pertama!").
- Semua teks UI Bahasa Indonesia. Contoh microcopy:
  - "Tarik video ke sini, atau klik untuk memilih"
  - "Kosongkan → dipilih AI"
  - "Sedang memotong mengikuti beat musik…"
  - "Siap diunggah! Tinggal salin caption dan posting."

---

## 7. Yang harus diserahkan Gemini

1. `ui/index.html`, `ui/app.js` (dan `ui/styles.css` bila perlu) — lengkap, bisa langsung dibuka.
2. Mode MOCK berjalan penuh: semua halaman bisa diklik, wizard bisa dijalankan sampai Hasil memakai data contoh di atas (video contoh boleh memakai URL video publik atau placeholder kotak hitam 9:16).
3. Penjelasan singkat cara mengganti `USE_MOCK` ke `false`.

**Kriteria diterima:**
- Tidak ada build step; buka `ui/index.html` (mode MOCK) langsung jalan.
- Semua endpoint & field persis seperti bagian 5.
- Tampilan rapi di lebar 1440 px dan 390 px, mode terang & gelap.
- Seluruh teks Bahasa Indonesia.
