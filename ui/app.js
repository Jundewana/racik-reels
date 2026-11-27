/**
 * AutoReels Studio — Frontend Logic (Alpine.js 3.14.1)
 * Contoh Brand
 *
 * USE_MOCK otomatis: dibuka langsung sebagai file (file://) → mode simulasi;
 * disajikan oleh backend (http://localhost:8000) → API sungguhan. Tambahkan ?mock=1 untuk memaksa simulasi.
 */
const USE_MOCK = location.protocol === 'file:' || new URLSearchParams(location.search).has('mock');

/* ==========================================================================
 * DATA CONTOH & SIMULATOR UNTUK MODE MOCK
 * ========================================================================== */
const MOCK_STORE = {
  options: {
    pillars: [
      {
        id: 'rental',
        label: 'Rental Motor',
        default_style: 'rental_energik',
        default_brief: 'Promo sewa motor untuk wisatawan yang mau keliling Garut'
      },
      {
        id: 'konstruksi',
        label: 'Konstruksi',
        default_style: 'proyek_profesional',
        default_brief: 'Tampilkan progres proyek dari awal sampai selesai'
      },
      {
        id: 'profil',
        label: 'Profil & Jasa',
        default_style: 'info_lowongan',
        default_brief: 'Perkenalkan layanan Contoh Brand'
      },
      {
        id: 'lowongan',
        label: 'Lowongan',
        default_style: 'info_lowongan',
        default_brief: 'Info lowongan kerja di Contoh Brand'
      }
    ],
    styles: [
      {
        id: 'rental_energik',
        description: 'Energik untuk promo rental motor',
        cut_pace_sec: [0.6, 1.2],
        music_mood_default: 'upbeat'
      },
      {
        id: 'wisata_sinematik',
        description: 'Sinematik untuk suasana perjalanan wisata Garut',
        cut_pace_sec: [1.5, 3.0],
        music_mood_default: 'santai'
      },
      {
        id: 'proyek_profesional',
        description: 'Tegas dan rapi untuk dokumentasi progres konstruksi',
        cut_pace_sec: [1.0, 2.0],
        music_mood_default: 'korporat'
      },
      {
        id: 'info_lowongan',
        description: 'Jelas dan informatif untuk pengumuman & profil perusahaan',
        cut_pace_sec: [1.2, 2.2],
        music_mood_default: 'upbeat'
      }
    ],
    music: [
      {
        path: 'upbeat/mixkit-pop-05-695.mp3',
        mood: 'upbeat',
        name: 'mixkit-pop-05-695',
        url: '/media/music/upbeat/mixkit-pop-05-695.mp3'
      },
      {
        path: 'santai/mixkit-acoustic-breeze-112.mp3',
        mood: 'santai',
        name: 'mixkit-acoustic-breeze-112',
        url: '/media/music/santai/mixkit-acoustic-breeze-112.mp3'
      },
      {
        path: 'korporat/mixkit-tech-house-vibes-130.mp3',
        mood: 'korporat',
        name: 'mixkit-tech-house-vibes-130',
        url: '/media/music/korporat/mixkit-tech-house-vibes-130.mp3'
      }
    ],
    footage_folders: [
      { path: 'footage/rental', count: 9 },
      { path: 'footage/konstruksi', count: 5 },
      { path: 'footage/profil', count: 4 },
      { path: 'footage/lowongan', count: 3 }
    ],
    default_cta: {
      rental: 'Booking sekarang via WhatsApp (000) 0000000!',
      konstruksi: 'Konsultasi proyek via WhatsApp (000) 0000000!',
      profil: 'Hubungi tim Brand di WhatsApp (000) 0000000!',
      lowongan: 'Kirim lamaran sekarang via WhatsApp (000) 0000000!'
    },
    hook_limits: { max_words: 5, max_chars: 28 }
  },

  footageByFolder: {
    'footage/rental': [
      { name: 'mixkit-biker-starting-his-motorcycle.mp4', duration: 11.4, width: 1280, height: 720, size_mb: 6.1, thumb_url: '/media/thumbs/ab12cd.jpg' },
      { name: '101506-video-720.mp4', duration: 8.2, width: 1280, height: 720, size_mb: 4.5, thumb_url: '/media/thumbs/ef34gh.jpg' },
      { name: 'garut-gunung-papandayan-ride.mp4', duration: 14.0, width: 1920, height: 1080, size_mb: 11.2, thumb_url: '/media/thumbs/ij56kl.jpg' },
      { name: 'matic-beat-ready-parkir.mp4', duration: 6.5, width: 1080, height: 1920, size_mb: 5.0, thumb_url: '/media/thumbs/mn78op.jpg' },
      { name: 'helm-bersih-serah-terima.mp4', duration: 7.8, width: 1080, height: 1920, size_mb: 5.8, thumb_url: '/media/thumbs/qr90st.jpg' },
      { name: 'jalan-raya-cipanas-garut.mp4', duration: 12.1, width: 1920, height: 1080, size_mb: 9.4, thumb_url: '/media/thumbs/uv12wx.jpg' },
      { name: 'cek-mesin-sebelum-jalan.mp4', duration: 5.9, width: 1080, height: 1920, size_mb: 4.1, thumb_url: '/media/thumbs/yz34ab.jpg' },
      { name: 'wisatawan-senyum-motor.mp4', duration: 9.3, width: 1080, height: 1920, size_mb: 7.2, thumb_url: '/media/thumbs/cd56ef.jpg' },
      { name: 'sunset-situ-bagendit.mp4', duration: 10.6, width: 1920, height: 1080, size_mb: 8.7, thumb_url: '/media/thumbs/gh78ij.jpg' }
    ],
    'footage/konstruksi': [
      { name: 'site-visit-pagi-garut.mp4', duration: 10.2, width: 1920, height: 1080, size_mb: 8.9, thumb_url: '' },
      { name: 'pekerja-pakai-apd-lengkap.mp4', duration: 7.4, width: 1080, height: 1920, size_mb: 5.3, thumb_url: '' },
      { name: 'pengecoran-pondasi-utama.mp4', duration: 13.5, width: 1920, height: 1080, size_mb: 12.1, thumb_url: '' },
      { name: 'drone-area-proyek-energi.mp4', duration: 15.0, width: 1920, height: 1080, size_mb: 14.4, thumb_url: '' },
      { name: 'finishing-struktur-baja.mp4', duration: 9.1, width: 1080, height: 1920, size_mb: 6.8, thumb_url: '' }
    ],
    'footage/profil': [
      { name: 'kantor-brand-garut.mp4', duration: 8.5, width: 1920, height: 1080, size_mb: 6.7, thumb_url: '' },
      { name: 'briefing-tim-lapangan.mp4', duration: 11.0, width: 1080, height: 1920, size_mb: 7.9, thumb_url: '' },
      { name: 'armada-operasional-siap.mp4', duration: 9.4, width: 1080, height: 1920, size_mb: 7.1, thumb_url: '' },
      { name: 'pelayanan-ramah-kantor.mp4', duration: 7.2, width: 1080, height: 1920, size_mb: 5.2, thumb_url: '' }
    ],
    'footage/lowongan': [
      { name: 'suasana-kerja-brand.mp4', duration: 9.0, width: 1080, height: 1920, size_mb: 6.4, thumb_url: '' },
      { name: 'tim-teknisi-lapangan.mp4', duration: 8.1, width: 1080, height: 1920, size_mb: 5.9, thumb_url: '' },
      { name: 'ajak-gabung-tim.mp4', duration: 6.8, width: 1080, height: 1920, size_mb: 4.8, thumb_url: '' }
    ]
  },

  jobsList: [
    {
      job_id: '20261118-155444-rental',
      created: '2026-11-18 15:54:44',
      pillar: 'rental',
      status: 'siap_unggah',
      hook_text: 'Keliling Garut Pakai Motor',
      duration: 20.3,
      cover_url: '/media/output/20261118-155444-rental/cover.jpg'
    },
    {
      job_id: '20261117-102015-konstruksi',
      created: '2026-11-17 10:20:15',
      pillar: 'konstruksi',
      status: 'perlu_tinjau',
      hook_text: 'Progres Proyek Minggu Ke-4',
      duration: 24.8,
      cover_url: '/media/output/20261117-102015-konstruksi/cover.jpg'
    },
    {
      job_id: '20261115-141209-profil',
      created: '2026-11-15 14:12:09',
      pillar: 'profil',
      status: 'siap_unggah',
      hook_text: 'Kenalan Sama Contoh Brand',
      duration: 18.5,
      cover_url: '/media/output/20261115-141209-profil/cover.jpg'
    }
  ],

  jobDetails: {
    '20261118-155444-rental': {
      job_id: '20261118-155444-rental',
      status: 'siap_unggah',
      pillar: 'rental',
      style: 'rental_energik',
      brief: 'Promo sewa motor untuk wisatawan yang mau keliling Garut',
      reel_url: '/media/output/20261118-155444-rental/reel.mp4',
      cover_url: '/media/output/20261118-155444-rental/cover.jpg',
      caption: 'Liburan ke Garut nggak perlu bingung soal kendaraan! Unit motor matic terawat, bersih, dan siap nemenin kamu keliling spot wisata favorit dari Cipanas sampai Papandayan.\n\n📲 Booking & info: WhatsApp (000) 0000000\n📍 Garut, Jawa Barat\n\n#rentalmotorgarut #wisatagarut #garut #sewamotorgarut',
      stats: {
        total_duration: 20.33,
        segments: 15,
        hook_duration: 2.13,
        beat_accuracy: 1.0,
        cost_usd: 0.0087,
        process_sec: 192
      },
      checklist: [
        { group: 'Video jadi', name: 'Resolusi 1080×1920', passed: true, required: true, detail: '1080×1920' },
        { group: 'Video jadi', name: 'Durasi sesuai target (±2 detik)', passed: true, required: true, detail: '20.33 dtk' },
        { group: 'Hook benar', name: 'Teks hook cukup besar (≥ 90 px, ≤ 2 baris)', passed: true, required: true, detail: '118 px, 2 baris' },
        { group: 'Hook benar', name: 'Panjang hook ≤ 5 kata / 28 huruf', passed: true, required: true, detail: '4 kata, 25 huruf' },
        { group: 'Style benar', name: 'Tempo potongan mengikuti beat musik', passed: true, required: true, detail: '100% pas beat' },
        { group: 'Style benar', name: 'Semua transisi bisa dirender', passed: false, required: false, detail: 'segmen [5] dirender sebagai cut' },
        { group: 'Teks & brand', name: 'Logo & CTA WhatsApp tampil jelas', passed: true, required: true, detail: 'CTA aktif' },
        { group: 'Siap posting', name: 'Caption & hashtag tersedia', passed: true, required: true, detail: '4 hashtag' }
      ],
      edl: {
        hook_text: 'Keliling Garut Pakai Motor',
        cta_text: 'Booking motor via WhatsApp sekarang!',
        segments: [
          { index: 0, role: 'hook', source_file: 'mixkit-biker-starting-his-motorcycle.mp4', start: 0.0, end: 2.13, overlay_text: null },
          { index: 1, role: 'isi', source_file: '101506-video-720.mp4', start: 10.44, end: 11.64, overlay_text: 'Unit Terawat & Aman' },
          { index: 2, role: 'isi', source_file: 'helm-bersih-serah-terima.mp4', start: 1.2, end: 2.75, overlay_text: 'Gratis 2 Helm Bersih' },
          { index: 3, role: 'isi', source_file: 'garut-gunung-papandayan-ride.mp4', start: 4.0, end: 6.1, overlay_text: 'Siap Gas ke Wisata Garut' }
        ]
      },
      report_md: '# Laporan Job `20261118-155444-rental`\n\n- **Pilar:** Rental Motor\n- **Style:** `rental_energik`\n- **Status:** Siap Unggah\n\n## Ringkasan Kualitas\n- Resolusi output `1080x1920` (30 fps, H.264)\n- Ketepatan potongan terhadap beat musik: **100%**\n- Catatan minor: segmen `[5]` memakai transisi `cut` langsung agar tidak memotong gerakan utama.'
    },

    '20261117-102015-konstruksi': {
      job_id: '20261117-102015-konstruksi',
      status: 'perlu_tinjau',
      pillar: 'konstruksi',
      style: 'proyek_profesional',
      brief: 'Tampilkan progres proyek dari awal sampai selesai',
      reel_url: '/media/output/20261117-102015-konstruksi/reel.mp4',
      cover_url: '/media/output/20261117-102015-konstruksi/cover.jpg',
      caption: 'Update progres pekerjaan konstruksi & infrastruktur energi bersama tim Contoh Brand. Mengutamakan keselamatan kerja dan ketepatan waktu.\n\n📲 Konsultasi proyek: WhatsApp (000) 0000000\n\n#konstruksigarut #brandenergi #infrastruktur',
      stats: {
        total_duration: 24.8,
        segments: 12,
        hook_duration: 2.4,
        beat_accuracy: 0.92,
        cost_usd: 0.0094,
        process_sec: 205
      },
      checklist: [
        { group: 'Video jadi', name: 'Resolusi 1080×1920', passed: true, required: true, detail: '1080×1920' },
        { group: 'Hook benar', name: 'Panjang hook ≤ 5 kata / 28 huruf', passed: false, required: true, detail: '29 huruf (sedikit melebihi batas)' },
        { group: 'Teks & brand', name: 'Logo & CTA WhatsApp tampil jelas', passed: true, required: true, detail: 'CTA aktif' },
        { group: 'Siap posting', name: 'Caption & hashtag tersedia', passed: true, required: true, detail: '3 hashtag' }
      ],
      edl: {
        hook_text: 'Progres Proyek Minggu Ke-4',
        cta_text: 'Konsultasi proyek via WhatsApp (000) 0000000!',
        segments: [
          { index: 0, role: 'hook', source_file: 'drone-area-proyek-energi.mp4', start: 0.0, end: 2.4, overlay_text: null },
          { index: 1, role: 'isi', source_file: 'pekerja-pakai-apd-lengkap.mp4', start: 1.0, end: 3.2, overlay_text: 'Standar K3 Terjaga' }
        ]
      },
      report_md: '# Laporan Job `20261117-102015-konstruksi`\n\n- **Status:** Perlu Tinjau\n- **Alasan:** Teks hook memiliki 29 karakter (disarankan maksimal 28 karakter). Silakan perpendek di panel **Edit Teks & Render Ulang**.'
    },

    '20261115-141209-profil': {
      job_id: '20261115-141209-profil',
      status: 'siap_unggah',
      pillar: 'profil',
      style: 'info_lowongan',
      brief: 'Perkenalkan layanan Contoh Brand',
      reel_url: '/media/output/20261115-141209-profil/reel.mp4',
      cover_url: '/media/output/20261115-141209-profil/cover.jpg',
      caption: 'Contoh Brand hadir di Garut untuk melayani kebutuhan transportasi rental motor hingga solusi proyek konstruksi dan energi terpercaya.\n\n📲 Info lengkap: WhatsApp (000) 0000000\n\n#brandenergi #garut #jasagarut',
      stats: {
        total_duration: 18.5,
        segments: 10,
        hook_duration: 2.0,
        beat_accuracy: 0.98,
        cost_usd: 0.0079,
        process_sec: 174
      },
      checklist: [
        { group: 'Video jadi', name: 'Resolusi 1080×1920', passed: true, required: true, detail: '1080×1920' },
        { group: 'Hook benar', name: 'Panjang hook ≤ 5 kata / 28 huruf', passed: true, required: true, detail: '4 kata, 26 huruf' },
        { group: 'Teks & brand', name: 'Logo & CTA WhatsApp tampil jelas', passed: true, required: true, detail: 'CTA aktif' },
        { group: 'Siap posting', name: 'Caption & hashtag tersedia', passed: true, required: true, detail: '3 hashtag' }
      ],
      edl: {
        hook_text: 'Kenalan Sama Contoh Brand',
        cta_text: 'Hubungi tim Brand di WhatsApp (000) 0000000!',
        segments: [
          { index: 0, role: 'hook', source_file: 'kantor-brand-garut.mp4', start: 0.0, end: 2.0, overlay_text: null },
          { index: 1, role: 'isi', source_file: 'briefing-tim-lapangan.mp4', start: 2.1, end: 4.5, overlay_text: 'Tim Profesional & Responsif' }
        ]
      },
      report_md: '# Laporan Job `20261115-141209-profil`\n\nSemua butir pemeriksaan wajib lolos.'
    }
  },

  configHooks: {
    rental: [
      { type: 'pertanyaan', text: 'Liburan ke Garut?' },
      { type: 'visual_wow', text: 'Keliling Garut Pakai Motor' },
      { type: 'harga', text: 'Sewa Motor Hemat Garut' }
    ],
    konstruksi: [
      { type: 'before_after', text: 'Dari Lahan Kosong Jadi Siap' },
      { type: 'angka', text: 'Update Proyek Minggu Ke-4' }
    ],
    profil: [
      { type: 'kontras', text: 'Satu Mitra Banyak Solusi' },
      { type: 'pertanyaan', text: 'Butuh Jasa di Garut?' }
    ],
    lowongan: [
      { type: 'pertanyaan', text: 'Lagi Cari Kerja di Garut?' },
      { type: 'angka', text: 'Dibuka 3 Posisi Baru!' }
    ]
  },

  configPillars: {
    rental: {
      hashtags: ['#rentalmotorgarut', '#sewamotorgarut', '#wisatagarut', '#garut'],
      keywords: ['sewa motor garut', 'rental motor dekat stasiun garut']
    },
    konstruksi: {
      hashtags: ['#konstruksigarut', '#kontraktorgarut', '#brandenergi'],
      keywords: ['jasa konstruksi garut', 'proyek infrastruktur energi']
    },
    profil: {
      hashtags: ['#brandenergi', '#perusahaangarut', '#garut'],
      keywords: ['pt brand energi indonesia', 'layanan jasa garut']
    },
    lowongan: {
      hashtags: ['#lokergarut', '#lowongankerjagarut', '#brandenergi'],
      keywords: ['lowongan kerja garut terbaru', 'loker pt brand']
    }
  },

  configTrends: {
    updated: '2026-11-19',
    formats: ['POV perjalanan pagi menuju wisata Garut', 'Transisi cepat mengikuti ketukan drum'],
    hooks: ['Pertanyaan singkat 3 kata di layar tengah', 'Teks kuning tebal dengan highlight kata kunci'],
    audio: ['Acoustic Sunda Chill Beat', 'Upbeat Travel Vlog Pop'],
    moments: ['Libur panjang akhir pekan', 'Musim wisata Gunung Papandayan & Cipanas'],
    notes: ['Utamakan klip dengan pencahayaan cerah pagi hari']
  },

  configBrand: {
    price_per_day: '[HARGA]',
    whatsapp: '(000) 0000000',
    instagram: '@contohbrand',
    default_cta: {
      rental: 'Booking sekarang via WhatsApp (000) 0000000!',
      konstruksi: 'Konsultasi proyek via WhatsApp (000) 0000000!',
      profil: 'Hubungi tim Brand di WhatsApp (000) 0000000!',
      lowongan: 'Kirim lamaran sekarang via WhatsApp (000) 0000000!'
    }
  },

  configCaptionGuide: {
    fields: {
      'Sapaan': 'kamu',
      'Emoji': 'secukupnya (2–3 emoji relevan)',
      'Bahasa Sunda': 'ya, ringan (mis. hayu, mangga)',
      'Kata dihindari': 'termurah, abal-abal',
      'Panjang': '2–4 kalimat singkat'
    },
    examples: [
      'Hayu keliling Garut tanpa ribet soal transportasi! Unit motor matic di Brand selalu dicek sebelum jalan biar perjalanan kamu nyaman.\n\n📲 Booking via WhatsApp (000) 0000000'
    ]
  },

  activeSimulations: {}
};

// Urutan langkah sama dengan autoreels/progress.py (step_index 1–6)
const CREATE_PROCESS_STEPS = [
  { key: 'ingest', label: 'Ingest & proxy' },
  { key: 'analyze', label: 'Analisis adegan & musik' },
  { key: 'describe', label: 'Deskripsi visual (AI)' },
  { key: 'direct', label: 'Director menyusun edit (AI)' },
  { key: 'render', label: 'Render video' },
  { key: 'checklist', label: 'Checklist Siap Unggah' }
];
const IMPORT_PROCESS_STEPS = [
  { key: 'ingest', label: 'Periksa video' },
  { key: 'analyze', label: 'Analisis adegan (tidak perlu untuk impor)' },
  { key: 'describe', label: 'Deskripsi visual (tidak perlu untuk impor)' },
  { key: 'direct', label: 'Tulis caption & hashtag (AI)' },
  { key: 'render', label: 'Normalisasi + logo + CTA' },
  { key: 'checklist', label: 'Checklist Siap Unggah' }
];

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

/* ==========================================================================
 * APLIKASI ALPINE.JS UTAMA
 * ========================================================================== */
function autoReelsApp() {
  return {
    isMockMode: USE_MOCK,
    darkMode: false,
    currentPage: 'create',
    wizardStep: 1,

    navItems: [
      { id: 'create', label: 'Buat Reel', shortLabel: 'Buat', icon: 'clapperboard' },
      { id: 'import', label: 'Impor Video', shortLabel: 'Impor', icon: 'file-video' },
      { id: 'history', label: 'Riwayat', shortLabel: 'Riwayat', icon: 'history' },
      { id: 'hooks', label: 'Pustaka Hook', shortLabel: 'Hook', icon: 'sparkles' },
      { id: 'hashtags', label: 'Hashtag & Keyword', shortLabel: 'Hashtag', icon: 'hash' },
      { id: 'trends', label: 'Brief Tren', shortLabel: 'Tren', icon: 'trending-up' },
      { id: 'brand', label: 'Brand & Caption', shortLabel: 'Brand', icon: 'badge-check' }
    ],

    wizardSteps: [
      { num: 1, label: 'Footage' },
      { num: 2, label: 'Atur' },
      { num: 3, label: 'Proses' },
      { num: 4, label: 'Hasil' }
    ],

    processSteps: CREATE_PROCESS_STEPS,

    // Impor video jadi (video-use / editor lain)
    importCandidates: [],
    importForm: {
      video_path: '',
      pillar: 'profil',
      brief: '',
      hook_text: '',
      cta_text: '',
      add_logo: true,
      add_cta: true
    },
    submittingImport: false,
    importUploading: false,
    lastSubmitKind: 'create',

    hookTypes: [
      { id: 'visual_wow', desc: 'Aksi visual langsung menarik di 1 detik awal', badgeClass: 'bg-purple-100 text-purple-800 dark:bg-purple-900/60 dark:text-purple-200' },
      { id: 'pertanyaan', desc: 'Memancing rasa ingin tahu penonton', badgeClass: 'bg-sky-100 text-sky-800 dark:bg-sky-900/60 dark:text-sky-200' },
      { id: 'harga', desc: 'Menonjolkan promo atau nilai hemat', badgeClass: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200' },
      { id: 'before_after', desc: 'Perbandingan sebelum dan sesudah', badgeClass: 'bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200' },
      { id: 'angka', desc: 'Fakta, jumlah, atau durasi spesifik', badgeClass: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-200' },
      { id: 'kontras', desc: 'Pernyataan tak terduga / pematah anggapan', badgeClass: 'bg-rose-100 text-rose-800 dark:bg-rose-900/60 dark:text-rose-200' }
    ],

    trendSections: [
      { key: 'formats', label: 'Format yang sedang ramai', placeholder: 'Mis. Transisi cepat mengikuti ketukan musik…' },
      { key: 'hooks', label: 'Gaya hook yang naik', placeholder: 'Mis. Pertanyaan 3 kata di tengah layar…' },
      { key: 'audio', label: 'Audio trending (judul saja)', placeholder: 'Mis. Acoustic Sunda Chill Beat…' },
      { key: 'moments', label: 'Momen musiman/event Garut', placeholder: 'Mis. Libur panjang akhir pekan…' },
      { key: 'notes', label: 'Catatan lain', placeholder: 'Catatan tambahan untuk AI…' }
    ],

    // Data Options & State Wizard
    options: {
      pillars: [],
      styles: [],
      music: [],
      footage_folders: [],
      default_cta: {},
      hook_limits: { max_words: 5, max_chars: 28 }
    },

    form: {
      pillar: 'rental',
      input_path: 'footage/rental',
      brief: '',
      style: 'rental_energik',
      duration: 20,
      hook_text: '',
      cta_text: '',
      music_file: null
    },

    clips: [],
    loadingClips: false,
    isDragging: false,
    uploadQueue: [],

    // Audio Preview
    audioPlayer: null,
    audioPreviewTimer: null,
    playingTrackPath: null,

    // Job & Progress Polling
    submittingJob: false,
    activeJobId: null,
    jobState: 'idle',
    pollTimer: null,
    showProcessLog: false,
    progress: {
      job_id: '',
      percent: 0,
      step: 'ingest',
      step_label: 'Ingest & proxy',
      step_index: 1,
      steps_total: 6,
      detail: '',
      elapsed_sec: 0,
      state: 'berjalan',
      error: null,
      log: []
    },

    // Hasil Job
    currentJob: null,
    videoLoadError: false,
    showSafeZone: false,
    showReportModal: false,
    collapsedChecklistGroups: {},
    rerendering: false,
    rerenderForm: {
      hook_text: '',
      cta_text: '',
      segment_texts: {}
    },

    // Riwayat
    jobs: [],
    historyFilter: {
      pillar: 'all',
      status: 'all'
    },

    // Config States
    hasUnsavedConfig: false,
    savingConfig: false,
    unsavedModal: {
      open: false,
      targetPage: null
    },

    activeConfigPillar: 'rental',
    hooksConfig: { rental: [], konstruksi: [], profil: [], lowongan: [] },
    newHook: { text: '', type: 'pertanyaan' },
    editingHookIndex: null,
    editingHookDraft: { text: '', type: 'pertanyaan' },

    activeSeoPillar: 'rental',
    pillarSeoConfig: {
      rental: { hashtags: [], keywords: [] },
      konstruksi: { hashtags: [], keywords: [] },
      profil: { hashtags: [], keywords: [] },
      lowongan: { hashtags: [], keywords: [] }
    },
    newHashtagInput: '',
    newKeywordInput: '',

    trendsConfig: {
      updated: '',
      formats: [],
      hooks: [],
      audio: [],
      moments: [],
      notes: []
    },
    trendInputs: {
      formats: '',
      hooks: '',
      audio: '',
      moments: '',
      notes: ''
    },

    brandConfig: {
      price_per_day: '[HARGA]',
      whatsapp: '(000) 0000000',
      instagram: '@contohbrand',
      default_cta: {}
    },

    captionGuideConfig: {
      fields: {},
      examples: []
    },

    // Toast Notifications
    toasts: [],

    /* ----------------------------------------------------------------------
     * INISIALISASI
     * ---------------------------------------------------------------------- */
    async init() {
      const savedDark = localStorage.getItem('autoreels_dark_mode');
      this.darkMode = savedDark === 'true';

      this.setupLucideObserver();

      window.addEventListener('beforeunload', (e) => {
        if (this.hasUnsavedConfig) {
          e.preventDefault();
          e.returnValue = '';
        }
      });

      await Promise.all([
        this.loadOptions(),
        this.loadHooksConfig(),
        this.loadJobs(),
        this.loadPillarSeoConfig('rental'),
        this.loadTrendsConfig(),
        this.loadBrandConfig(),
        this.loadCaptionGuideConfig(),
        this.loadImportCandidates()
      ]);

      this.selectPillar(this.form.pillar, true);
    },

    setupLucideObserver() {
      const renderIcons = () => {
        if (window.lucide && document.querySelector('i[data-lucide]')) {
          window.lucide.createIcons();
        }
      };
      renderIcons();
      const observer = new MutationObserver(() => renderIcons());
      observer.observe(document.body, { childList: true, subtree: true });
    },

    toggleDarkMode() {
      this.darkMode = !this.darkMode;
      localStorage.setItem('autoreels_dark_mode', String(this.darkMode));
    },

    /* ----------------------------------------------------------------------
     * FUNGSI PUSAT API: api(method, path, body)
     * ---------------------------------------------------------------------- */
    async api(method, path, body = null) {
      if (USE_MOCK) {
        return this.mockApi(method, path, body);
      }

      try {
        const fetchOptions = {
          method,
          headers: {}
        };

        if (body instanceof FormData) {
          fetchOptions.body = body;
        } else if (body !== null) {
          fetchOptions.headers['Content-Type'] = 'application/json';
          fetchOptions.body = JSON.stringify(body);
        }

        const res = await fetch(path, fetchOptions);
        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
          const errMsg = data.error || `Permintaan gagal (${res.status})`;
          this.showToast(errMsg, 'error');
          throw new Error(errMsg);
        }

        return data;
      } catch (err) {
        // fetch() gagal total (server mati/jaringan) melempar TypeError tanpa respons
        if (err instanceof TypeError || !err.message) {
          this.showToast('Gagal terhubung ke server lokal. Pastikan AutoReels Studio sedang berjalan.', 'error');
        }
        throw err;
      }
    },

    /* ----------------------------------------------------------------------
     * MOCK BACKEND ROUTER (LENGKAP SESUAI KONTRAK BAGIAN 5)
     * ---------------------------------------------------------------------- */
    async mockApi(method, path, body) {
      await new Promise((r) => setTimeout(r, 140));

      // GET /api/options
      if (method === 'GET' && path === '/api/options') {
        return deepClone(MOCK_STORE.options);
      }

      // GET /api/footage?folder=...
      if (method === 'GET' && path.startsWith('/api/footage')) {
        const urlObj = new URL(path, 'http://localhost');
        const folder = urlObj.searchParams.get('folder') || 'footage/rental';
        return {
          folder,
          clips: deepClone(MOCK_STORE.footageByFolder[folder] || [])
        };
      }

      // POST /api/footage/upload
      if (method === 'POST' && path === '/api/footage/upload') {
        const pillar = body.get('pillar') || 'rental';
        const folder = `footage/${pillar}`;
        const files = body.getAll('files[]');
        if (!MOCK_STORE.footageByFolder[folder]) {
          MOCK_STORE.footageByFolder[folder] = [];
        }
        const uploadedNames = [];
        files.forEach((f) => {
          uploadedNames.push(f.name);
          MOCK_STORE.footageByFolder[folder].unshift({
            name: f.name,
            duration: +(6 + Math.random() * 9).toFixed(1),
            width: 1080,
            height: 1920,
            size_mb: +Math.max(1.2, f.size / (1024 * 1024)).toFixed(1),
            thumb_url: ''
          });
        });
        const folderEntry = MOCK_STORE.options.footage_folders.find((x) => x.path === folder);
        if (folderEntry) {
          folderEntry.count = MOCK_STORE.footageByFolder[folder].length;
        }
        return { folder, files: uploadedNames };
      }

      // GET /api/import/candidates
      if (method === 'GET' && path === '/api/import/candidates') {
        return {
          candidates: [
            { path: 'footage/profil/testimoni-pelanggan/edit/final.mp4', name: 'testimoni-pelanggan/final.mp4',
              size_mb: 14.2, modified: '2026-11-19 09:40', has_transcript: true, source: 'video-use' }
          ]
        };
      }

      // POST /api/import
      if (method === 'POST' && path === '/api/import') {
        const jobId = `${new Date().toISOString().replace(/[-:T]/g, '').slice(0, 8)}-${new Date().toTimeString().slice(0, 8).replace(/:/g, '')}-${body.pillar}`;
        MOCK_STORE.activeSimulations[jobId] = {
          startedAt: Date.now(),
          durationSec: 10,
          payload: { ...deepClone(body), input_path: body.video_path, duration: 30 },
          isRerender: false
        };
        return { job_id: jobId };
      }

      // POST /api/jobs
      if (method === 'POST' && path === '/api/jobs') {
        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
        const jobId = `${stamp}-${body.pillar || 'rental'}`;

        MOCK_STORE.activeSimulations[jobId] = {
          startedAt: Date.now(),
          durationSec: 20, // Simulasi ±20 detik dari 0 -> 100%
          payload: deepClone(body),
          isRerender: false
        };

        return { job_id: jobId };
      }

      // POST /api/jobs/{id}/rerender
      if (method === 'POST' && /^\/api\/jobs\/[^/]+\/rerender$/.test(path)) {
        const jobId = path.split('/')[3];
        const detail = MOCK_STORE.jobDetails[jobId];
        if (detail) {
          detail.edl.hook_text = body.hook_text || detail.edl.hook_text;
          detail.edl.cta_text = body.cta_text || detail.edl.cta_text;
          if (body.segment_texts) {
            detail.edl.segments.forEach((seg) => {
              if (Object.prototype.hasOwnProperty.call(body.segment_texts, String(seg.index))) {
                seg.overlay_text = body.segment_texts[String(seg.index)];
              }
            });
          }
          const words = detail.edl.hook_text.trim().split(/\s+/).filter(Boolean).length;
          const chars = detail.edl.hook_text.trim().length;
          const hookCheck = detail.checklist.find((c) => c.name.includes('Panjang hook'));
          if (hookCheck) {
            hookCheck.passed = words <= 5 && chars <= 28;
            hookCheck.detail = `${words} kata, ${chars} huruf`;
          }
          const anyRequiredFail = detail.checklist.some((c) => c.required && !c.passed);
          detail.status = anyRequiredFail ? 'perlu_tinjau' : 'siap_unggah';

          const listEntry = MOCK_STORE.jobsList.find((j) => j.job_id === jobId);
          if (listEntry) {
            listEntry.hook_text = detail.edl.hook_text;
            listEntry.status = detail.status;
          }
        }

        MOCK_STORE.activeSimulations[jobId] = {
          startedAt: Date.now(),
          durationSec: 8, // Render ulang lebih cepat (±8 detik)
          payload: detail || {},
          isRerender: true
        };

        return { job_id: jobId };
      }

      // GET /api/jobs/{id}/progress
      if (method === 'GET' && /^\/api\/jobs\/[^/]+\/progress$/.test(path)) {
        const jobId = path.split('/')[3];
        const sim = MOCK_STORE.activeSimulations[jobId];
        if (!sim) {
          return {
            job_id: jobId,
            percent: 100,
            step: 'checklist',
            step_label: 'Checklist Siap Unggah',
            step_index: 6,
            steps_total: 6,
            detail: 'Selesai',
            elapsed_sec: 20,
            state: 'selesai',
            error: null,
            log: [`Job ${jobId}`, 'Selesai memproses Reels.']
          };
        }

        const elapsed = (Date.now() - sim.startedAt) / 1000;
        const ratio = Math.min(1, elapsed / sim.durationSec);
        const percent = +(ratio * 100).toFixed(1);

        const stepStages = [
          { key: 'ingest', label: 'Ingest & proxy', detail: 'Memeriksa resolusi & membuat proxy klip…' },
          { key: 'analyze', label: 'Analisis adegan & musik', detail: 'Mendeteksi ketukan musik (118 BPM)…' },
          { key: 'describe', label: 'Deskripsi visual (AI)', detail: 'adegan 18–26 dari 32' },
          { key: 'direct', label: 'Director menyusun edit (AI)', detail: 'Menyusun hook 3 detik & urutan adegan' },
          { key: 'render', label: 'Render video', detail: 'Merender 1080×1920 + teks highlight kuning' },
          { key: 'checklist', label: 'Checklist Siap Unggah', detail: 'Memverifikasi zona aman & kualitas audio' }
        ];

        const idx = sim.isRerender
          ? (ratio < 0.7 ? 4 : 5)
          : Math.min(5, Math.floor(ratio * 6));
        const stage = stepStages[idx];
        const isDone = ratio >= 1;

        const logs = [
          `Job ${jobId}`,
          `[1/6] Ingest footage dari ${sim.payload.input_path || 'footage/rental'}…`,
          `[2/6] Musik terpilih: ${sim.payload.music_file || 'upbeat/mixkit-pop-05-695.mp3'} — 118 BPM`
        ];
        if (idx >= 2) logs.push('[3/6] Analisis visual adegan dengan AI…');
        if (ratio >= 0.35 && ratio <= 0.55) {
          logs.push('[menunggu] Rate limit API sementara, jeda otomatis 2 detik…');
        }
        if (idx >= 3) logs.push('[4/6] Menyusun EDL & hook 3 detik pertama…');
        if (idx >= 4) logs.push('[5/6] Render video 9:16 (1080x1920)…');
        if (isDone) logs.push('[6/6] Checklist Siap Unggah lolos. Selesai!');

        if (isDone && !MOCK_STORE.jobDetails[jobId]) {
          const hookUsed = (sim.payload.hook_text && sim.payload.hook_text.trim()) || 'Keliling Garut Pakai Motor';
          const ctaUsed = (sim.payload.cta_text && sim.payload.cta_text.trim()) ||
            MOCK_STORE.options.default_cta[sim.payload.pillar] ||
            'Booking sekarang via WhatsApp (000) 0000000!';
          const words = hookUsed.trim().split(/\s+/).filter(Boolean).length;
          const chars = hookUsed.trim().length;
          const hookOk = words <= 5 && chars <= 28;

          const newDetail = {
            job_id: jobId,
            status: hookOk ? 'siap_unggah' : 'perlu_tinjau',
            pillar: sim.payload.pillar || 'rental',
            style: sim.payload.style || 'rental_energik',
            brief: sim.payload.brief || '',
            reel_url: `/media/output/${jobId}/reel.mp4`,
            cover_url: `/media/output/${jobId}/cover.jpg`,
            caption: `${sim.payload.brief || 'Promo spesial dari Contoh Brand!'}\n\n📲 ${ctaUsed}\n📍 Garut, Jawa Barat\n\n${(MOCK_STORE.configPillars[sim.payload.pillar]?.hashtags || ['#brandenergi', '#garut']).join(' ')}`,
            stats: {
              total_duration: Number(sim.payload.duration) || 20,
              segments: 14,
              hook_duration: 2.1,
              beat_accuracy: 0.98,
              cost_usd: 0.0085,
              process_sec: Math.round(elapsed)
            },
            checklist: [
              { group: 'Video jadi', name: 'Resolusi 1080×1920', passed: true, required: true, detail: '1080×1920' },
              { group: 'Hook benar', name: 'Teks hook cukup besar (≥ 90 px, ≤ 2 baris)', passed: true, required: true, detail: '116 px, 2 baris' },
              { group: 'Hook benar', name: 'Panjang hook ≤ 5 kata / 28 huruf', passed: hookOk, required: true, detail: `${words} kata, ${chars} huruf` },
              { group: 'Style benar', name: 'Semua transisi bisa dirender', passed: true, required: true, detail: 'Beat sync aktif' },
              { group: 'Teks & brand', name: 'CTA WhatsApp tampil di akhir', passed: true, required: true, detail: 'Tampil 3 dtk' },
              { group: 'Siap posting', name: 'Caption & hashtag SEO siap', passed: true, required: true, detail: 'Siap salin' }
            ],
            edl: {
              hook_text: hookUsed,
              cta_text: ctaUsed,
              segments: [
                { index: 0, role: 'hook', source_file: 'clip_01.mp4', start: 0.0, end: 2.1, overlay_text: null },
                { index: 1, role: 'isi', source_file: 'clip_02.mp4', start: 2.1, end: 5.4, overlay_text: 'Kualitas Terjamin' },
                { index: 2, role: 'isi', source_file: 'clip_03.mp4', start: 5.4, end: 9.0, overlay_text: 'Pelayanan Cepat Garut' }
              ]
            },
            report_md: `# Laporan Job \`${jobId}\`\n\n- **Pilar:** ${sim.payload.pillar}\n- **Durasi Target:** ${sim.payload.duration} detik\n- **Hook:** "${hookUsed}"\n\n## Catatan Produksi\nVideo berhasil dirangkai mengikuti ketukan musik dengan rasio vertikal 9:16.`
          };

          MOCK_STORE.jobDetails[jobId] = newDetail;
          MOCK_STORE.jobsList.unshift({
            job_id: jobId,
            created: new Date().toISOString().replace('T', ' ').slice(0, 19),
            pillar: newDetail.pillar,
            status: newDetail.status,
            hook_text: hookUsed,
            duration: newDetail.stats.total_duration,
            cover_url: newDetail.cover_url
          });
        }

        return {
          job_id: jobId,
          percent,
          step: stage.key,
          step_label: stage.label,
          step_index: idx + 1,
          steps_total: 6,
          detail: stage.detail,
          elapsed_sec: +elapsed.toFixed(1),
          state: isDone ? 'selesai' : 'berjalan',
          error: null,
          log: logs
        };
      }

      // GET /api/jobs
      if (method === 'GET' && path === '/api/jobs') {
        return { jobs: deepClone(MOCK_STORE.jobsList) };
      }

      // GET /api/jobs/{id}
      if (method === 'GET' && /^\/api\/jobs\/[^/]+$/.test(path)) {
        const jobId = path.split('/')[3];
        const detail = MOCK_STORE.jobDetails[jobId] || Object.values(MOCK_STORE.jobDetails)[0];
        return deepClone(detail);
      }

      // Config: Hooks
      if (path === '/api/config/hooks') {
        if (method === 'GET') return deepClone(MOCK_STORE.configHooks);
        if (method === 'PUT') {
          MOCK_STORE.configHooks = deepClone(body);
          return { ok: true };
        }
      }

      // Config: Pillars SEO
      if (path.startsWith('/api/config/pillars/')) {
        const pillar = path.split('/').pop();
        if (method === 'GET') {
          return deepClone(MOCK_STORE.configPillars[pillar] || { hashtags: [], keywords: [] });
        }
        if (method === 'PUT') {
          MOCK_STORE.configPillars[pillar] = deepClone(body);
          return { ok: true };
        }
      }

      // Config: Trends
      if (path === '/api/config/trends') {
        if (method === 'GET') return deepClone(MOCK_STORE.configTrends);
        if (method === 'PUT') {
          MOCK_STORE.configTrends = {
            ...deepClone(body),
            updated: new Date().toISOString().slice(0, 10)
          };
          return { ok: true };
        }
      }

      // Config: Brand
      if (path === '/api/config/brand') {
        if (method === 'GET') return deepClone(MOCK_STORE.configBrand);
        if (method === 'PUT') {
          MOCK_STORE.configBrand.price_per_day = body.price_per_day;
          MOCK_STORE.configBrand.default_cta = deepClone(body.default_cta);
          MOCK_STORE.options.default_cta = deepClone(body.default_cta);
          return { ok: true };
        }
      }

      // Config: Caption Guide
      if (path === '/api/config/caption-guide') {
        if (method === 'GET') return deepClone(MOCK_STORE.configCaptionGuide);
        if (method === 'PUT') {
          MOCK_STORE.configCaptionGuide = deepClone(body);
          return { ok: true };
        }
      }

      return { ok: true };
    },

    /* ----------------------------------------------------------------------
     * NAVIGASI & KONFIRMASI UNSAVED CHANGES
     * ---------------------------------------------------------------------- */
    navigateTo(pageId) {
      if (this.currentPage === pageId) return;

      if (this.hasUnsavedConfig) {
        this.unsavedModal = { open: true, targetPage: pageId };
        return;
      }

      this.currentPage = pageId;
      if (pageId === 'history') {
        this.loadJobs();
      }
      if (pageId === 'import') {
        this.loadImportCandidates();
      }
    },

    /* ----------------------------------------------------------------------
     * IMPOR VIDEO JADI (video-use / editor lain)
     * ---------------------------------------------------------------------- */
    async loadImportCandidates() {
      const data = await this.api('GET', '/api/import/candidates');
      this.importCandidates = data.candidates || [];
      if (!this.importForm.video_path && this.importCandidates.length > 0) {
        this.importForm.video_path = this.importCandidates[0].path;
      }
    },

    async uploadImportFile(event) {
      const file = (event.target?.files || [])[0];
      event.target.value = '';
      if (!file) return;
      this.importUploading = true;
      try {
        const fd = new FormData();
        fd.append('pillar', 'impor');
        fd.append('files[]', file);
        const res = USE_MOCK
          ? await this.mockApi('POST', '/api/footage/upload', fd)
          : await this.uploadWithProgress('/api/footage/upload', fd, () => {});
        await this.loadImportCandidates();
        if (res.files && res.files[0]) {
          this.importForm.video_path = `${res.folder}/${res.files[0]}`;
        }
        this.showToast('Video jadi berhasil diunggah!');
      } finally {
        this.importUploading = false;
      }
    },

    async submitImport() {
      if (this.submittingImport || !this.importForm.video_path.trim()) return;
      this.submittingImport = true;
      this.lastSubmitKind = 'import';
      try {
        const payload = {
          video_path: this.importForm.video_path.trim(),
          pillar: this.importForm.pillar,
          brief: this.importForm.brief.trim(),
          hook_text: this.importForm.hook_text.trim() || null,
          cta_text: this.importForm.add_cta ? (this.importForm.cta_text.trim() || null) : null,
          add_logo: this.importForm.add_logo,
          add_cta: this.importForm.add_cta
        };
        const res = await this.api('POST', '/api/import', payload);
        this.currentPage = 'create';
        this.startPollingProgress(res.job_id, 'import');
      } finally {
        this.submittingImport = false;
      }
    },

    confirmDiscardChanges() {
      const target = this.unsavedModal.targetPage;
      this.hasUnsavedConfig = false;
      this.unsavedModal.open = false;
      if (target) {
        this.currentPage = target;
      }
    },

    /* ----------------------------------------------------------------------
     * WIZARD LANGKAH 1 & 2: FOOTAGE & PENGATURAN
     * ---------------------------------------------------------------------- */
    async loadOptions() {
      const data = await this.api('GET', '/api/options');
      this.options = data;
    },

    selectPillar(pillarId, isInit = false) {
      this.form.pillar = pillarId;
      const pObj = this.options.pillars.find((p) => p.id === pillarId);
      if (pObj) {
        this.form.style = pObj.default_style;
        this.form.brief = pObj.default_brief;
      }

      const matchingFolder = this.options.footage_folders.find((f) => f.path === `footage/${pillarId}`);
      if (matchingFolder) {
        this.form.input_path = matchingFolder.path;
      } else if (this.options.footage_folders.length > 0 && isInit) {
        this.form.input_path = this.options.footage_folders[0].path;
      }

      this.loadFootage(this.form.input_path);
    },

    async loadFootage(folder) {
      this.loadingClips = true;
      try {
        const data = await this.api('GET', `/api/footage?folder=${encodeURIComponent(folder)}`);
        this.clips = data.clips || [];
      } finally {
        this.loadingClips = false;
      }
    },

    handleFileDrop(event) {
      this.isDragging = false;
      const files = Array.from(event.dataTransfer?.files || []);
      if (files.length > 0) {
        this.uploadFiles(files);
      }
    },

    handleFileSelect(event) {
      const files = Array.from(event.target?.files || []);
      if (files.length > 0) {
        this.uploadFiles(files);
      }
      event.target.value = '';
    },

    async uploadFiles(files) {
      const validFiles = files.filter((f) => /\.(mp4|mov)$/i.test(f.name) || f.type.startsWith('video/'));
      if (validFiles.length === 0) {
        this.showToast('Pilih file video berformat .mp4 atau .mov.', 'error');
        return;
      }

      for (const file of validFiles) {
        const queueItem = {
          id: `${Date.now()}-${Math.random()}`,
          name: file.name,
          progress: 0,
          status: 'uploading'
        };
        this.uploadQueue.push(queueItem);

        const fd = new FormData();
        fd.append('pillar', this.form.pillar);
        fd.append('files[]', file);

        try {
          if (USE_MOCK) {
            for (let p = 20; p <= 100; p += 20) {
              await new Promise((r) => setTimeout(r, 90));
              queueItem.progress = p;
            }
            const res = await this.mockApi('POST', '/api/footage/upload', fd);
            queueItem.status = 'done';
            this.form.input_path = res.folder;
          } else {
            const res = await this.uploadWithProgress('/api/footage/upload', fd, (pct) => {
              queueItem.progress = pct;
            });
            queueItem.status = 'done';
            if (res.folder) this.form.input_path = res.folder;
          }
        } catch (err) {
          queueItem.status = 'error';
        }
      }

      await this.loadOptions();
      await this.loadFootage(this.form.input_path);
      this.showToast('Video berhasil diunggah!');
      setTimeout(() => {
        this.uploadQueue = this.uploadQueue.filter((q) => q.status !== 'done');
      }, 2500);
    },

    uploadWithProgress(url, formData, onProgress) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', url);
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            onProgress(Math.round((e.loaded / e.total) * 100));
          }
        };
        xhr.onload = () => {
          let json = {};
          try {
            json = JSON.parse(xhr.responseText || '{}');
          } catch (_) {}
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(json);
          } else {
            const msg = json.error || `Gagal unggah (${xhr.status})`;
            this.showToast(msg, 'error');
            reject(new Error(msg));
          }
        };
        xhr.onerror = () => {
          this.showToast('Koneksi terputus saat mengunggah video.', 'error');
          reject(new Error('Network error'));
        };
        xhr.send(formData);
      });
    },

    // Musik Preview 10 detik
    selectAutoMusic() {
      this.stopMusicPreview();
      this.form.music_file = null;
    },

    toggleMusicPreview(track) {
      if (this.playingTrackPath === track.path) {
        this.stopMusicPreview();
        return;
      }

      this.stopMusicPreview();
      this.playingTrackPath = track.path;

      const audio = new Audio(track.url);
      this.audioPlayer = audio;
      audio.play().catch(() => {
        this.playMockSynthPreview();
      });

      this.audioPreviewTimer = setTimeout(() => {
        this.stopMusicPreview();
      }, 10000);
    },

    playMockSynthPreview() {
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(330, ctx.currentTime);
        gain.gain.setValueAtTime(0.04, ctx.currentTime);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        setTimeout(() => {
          osc.stop();
          ctx.close();
        }, 600);
      } catch (_) {}
    },

    stopMusicPreview() {
      if (this.audioPreviewTimer) {
        clearTimeout(this.audioPreviewTimer);
        this.audioPreviewTimer = null;
      }
      if (this.audioPlayer) {
        this.audioPlayer.pause();
        this.audioPlayer = null;
      }
      this.playingTrackPath = null;
    },

    /* ----------------------------------------------------------------------
     * WIZARD LANGKAH 3 & 4: SUBMIT JOB, POLLING PROGRESS, HASIL & RERENDER
     * ---------------------------------------------------------------------- */
    canJumpToStep(stepNum) {
      if (stepNum === this.wizardStep) return true;
      if (this.jobState === 'berjalan') return stepNum === 3;
      if (stepNum === 1) return true;
      if (stepNum === 2) return this.clips.length > 0;
      if (stepNum === 4) return Boolean(this.currentJob);
      return false;
    },

    goToWizardStep(stepNum) {
      if (this.canJumpToStep(stepNum)) {
        this.wizardStep = stepNum;
      }
    },

    async submitCreateJob() {
      if (this.submittingJob) return;
      this.stopMusicPreview();
      this.submittingJob = true;
      this.lastSubmitKind = 'create';

      try {
        const payload = {
          input_path: this.form.input_path,
          pillar: this.form.pillar,
          brief: this.form.brief.trim(),
          style: this.form.style,
          duration: Number(this.form.duration) || 20,
          hook_text: this.form.hook_text.trim() || null,
          cta_text: this.form.cta_text.trim() || null,
          music_file: this.form.music_file || null
        };

        const res = await this.api('POST', '/api/jobs', payload);
        this.activeJobId = res.job_id;
        this.startPollingProgress(res.job_id);
      } finally {
        this.submittingJob = false;
      }
    },

    startPollingProgress(jobId, kind = 'create') {
      this.stopPolling();
      this.processSteps = kind === 'import' ? IMPORT_PROCESS_STEPS : CREATE_PROCESS_STEPS;
      this.wizardStep = 3;
      this.jobState = 'berjalan';
      this.progress = {
        job_id: jobId,
        percent: 0,
        step: 'ingest',
        step_label: 'Ingest & proxy',
        step_index: 1,
        steps_total: 6,
        detail: 'Memulai antrean produksi…',
        elapsed_sec: 0,
        state: 'berjalan',
        error: null,
        log: []
      };

      const pollOnce = async () => {
        try {
          const data = await this.api('GET', `/api/jobs/${encodeURIComponent(jobId)}/progress`);
          this.progress = data;
          this.jobState = data.state;

          if (data.state === 'berjalan') {
            document.title = `(${Math.round(data.percent)}%) AutoReels`;
          } else {
            document.title = 'AutoReels Studio — Contoh Brand';
          }

          this.$nextTick(() => {
            if (this.$refs.logContainer) {
              this.$refs.logContainer.scrollTop = this.$refs.logContainer.scrollHeight;
            }
          });

          if (data.state === 'selesai') {
            this.stopPolling();
            this.showToast('Reel selesai dibuat!');
            await this.openJobDetail(jobId);
          } else if (data.state === 'gagal') {
            this.stopPolling();
          }
        } catch (err) {
          this.stopPolling();
          this.jobState = 'gagal';
          this.progress.state = 'gagal';
          this.progress.error = err.message || 'Gagal memantau progres.';
        }
      };

      pollOnce();
      this.pollTimer = setInterval(pollOnce, 1000);
    },

    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
      document.title = 'AutoReels Studio — Contoh Brand';
    },

    retryFailedJob() {
      if (this.lastSubmitKind === 'import') {
        this.submitImport();
      } else {
        this.submitCreateJob();
      }
    },

    hasRateLimitWait() {
      return (this.progress.log || []).some((line) => line.includes('[menunggu]'));
    },

    async openJobDetail(jobId) {
      const data = await this.api('GET', `/api/jobs/${encodeURIComponent(jobId)}`);
      this.currentJob = data;
      this.activeJobId = jobId;
      this.videoLoadError = false;

      const segTexts = {};
      (data.edl?.segments || []).forEach((seg) => {
        if (seg.overlay_text !== null && seg.overlay_text !== undefined) {
          segTexts[seg.index] = seg.overlay_text;
        }
      });

      this.rerenderForm = {
        hook_text: data.edl?.hook_text || '',
        cta_text: data.edl?.cta_text || '',
        segment_texts: segTexts
      };

      const collapsed = {};
      this.groupedChecklist().forEach((g) => {
        collapsed[g.group] = g.allPassed;
      });
      this.collapsedChecklistGroups = collapsed;

      this.currentPage = 'create';
      this.wizardStep = 4;
    },

    async submitRerender() {
      if (!this.currentJob || this.rerendering) return;
      this.rerendering = true;

      try {
        const payload = {
          hook_text: this.rerenderForm.hook_text.trim(),
          cta_text: this.rerenderForm.cta_text.trim(),
          segment_texts: { ...this.rerenderForm.segment_texts }
        };

        const res = await this.api('POST', `/api/jobs/${encodeURIComponent(this.currentJob.job_id)}/rerender`, payload);
        this.startPollingProgress(res.job_id || this.currentJob.job_id,
          this.currentJob.source === 'import' ? 'import' : 'create');
      } finally {
        this.rerendering = false;
      }
    },

    resetWizardToNew() {
      this.stopPolling();
      this.jobState = 'idle';
      this.currentJob = null;
      this.form.hook_text = '';
      this.form.cta_text = '';
      this.wizardStep = 1;
    },

    /* ----------------------------------------------------------------------
     * HELPER HASIL & CHECKLIST
     * ---------------------------------------------------------------------- */
    groupedChecklist() {
      const items = this.currentJob?.checklist || [];
      const map = new Map();

      items.forEach((item) => {
        if (!map.has(item.group)) {
          map.set(item.group, []);
        }
        map.get(item.group).push(item);
      });

      return Array.from(map.entries()).map(([group, grpItems]) => {
        const passedCount = grpItems.filter((i) => i.passed).length;
        return {
          group,
          items: grpItems,
          passedCount,
          allPassed: passedCount === grpItems.length
        };
      });
    },

    toggleChecklistGroup(groupName) {
      this.collapsedChecklistGroups[groupName] = !this.collapsedChecklistGroups[groupName];
    },

    failedChecklistItems() {
      return (this.currentJob?.checklist || []).filter((item) => !item.passed);
    },

    editableSegments() {
      return (this.currentJob?.edl?.segments || []).filter(
        (seg) => seg.overlay_text !== null && seg.overlay_text !== undefined
      );
    },

    getFirstSegmentOverlay() {
      const seg = this.editableSegments()[0];
      return seg ? seg.overlay_text : (this.currentJob?.brief || 'Potongan otomatis sesuai beat');
    },

    async copyCaption() {
      const text = this.currentJob?.caption || '';
      try {
        await navigator.clipboard.writeText(text);
        this.showToast('Tersalin!');
      } catch (_) {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        this.showToast('Tersalin!');
      }
    },

    handleMockDownload(event, label) {
      if (USE_MOCK) {
        event.preventDefault();
        this.showToast(`Mode simulasi: ${label} siap diunduh saat terhubung ke backend.`);
      }
    },

    /* ----------------------------------------------------------------------
     * HALAMAN 2: RIWAYAT
     * ---------------------------------------------------------------------- */
    async loadJobs() {
      const data = await this.api('GET', '/api/jobs');
      this.jobs = data.jobs || [];
    },

    filteredJobs() {
      return this.jobs.filter((j) => {
        const matchPillar = this.historyFilter.pillar === 'all' || j.pillar === this.historyFilter.pillar;
        const matchStatus = this.historyFilter.status === 'all' || j.status === this.historyFilter.status;
        return matchPillar && matchStatus;
      });
    },

    /* ----------------------------------------------------------------------
     * HALAMAN 3: PUSTAKA HOOK
     * ---------------------------------------------------------------------- */
    async loadHooksConfig() {
      const data = await this.api('GET', '/api/config/hooks');
      this.hooksConfig = {
        rental: data.rental || [],
        konstruksi: data.konstruksi || [],
        profil: data.profil || [],
        lowongan: data.lowongan || []
      };
    },

    addHookItem() {
      const text = this.newHook.text.trim();
      if (!text) return;
      if (!this.hooksConfig[this.activeConfigPillar]) {
        this.hooksConfig[this.activeConfigPillar] = [];
      }
      this.hooksConfig[this.activeConfigPillar].push({
        type: this.newHook.type,
        text
      });
      this.newHook.text = '';
      this.hasUnsavedConfig = true;
    },

    startEditHook(idx, item) {
      this.editingHookIndex = idx;
      this.editingHookDraft = { text: item.text, type: item.type };
    },

    applyEditHook(idx) {
      const text = this.editingHookDraft.text.trim();
      if (!text) return;
      this.hooksConfig[this.activeConfigPillar][idx] = {
        text,
        type: this.editingHookDraft.type
      };
      this.editingHookIndex = null;
      this.hasUnsavedConfig = true;
    },

    deleteHookItem(idx) {
      if (!window.confirm('Hapus hook ini dari daftar?')) return;
      this.hooksConfig[this.activeConfigPillar].splice(idx, 1);
      this.hasUnsavedConfig = true;
    },

    async saveHooksConfig() {
      this.savingConfig = true;
      try {
        await this.api('PUT', '/api/config/hooks', this.hooksConfig);
        this.hasUnsavedConfig = false;
        this.showToast('Pustaka hook berhasil disimpan!');
      } finally {
        this.savingConfig = false;
      }
    },

    getHookTypeBadgeClass(typeId) {
      const found = this.hookTypes.find((t) => t.id === typeId);
      return found ? found.badgeClass : 'bg-slate-100 text-slate-700';
    },

    /* ----------------------------------------------------------------------
     * HALAMAN 4: HASHTAG & KEYWORD
     * ---------------------------------------------------------------------- */
    async switchSeoPillar(pillarId) {
      this.activeSeoPillar = pillarId;
      await this.loadPillarSeoConfig(pillarId);
    },

    async loadPillarSeoConfig(pillarId) {
      const data = await this.api('GET', `/api/config/pillars/${encodeURIComponent(pillarId)}`);
      this.pillarSeoConfig[pillarId] = {
        hashtags: data.hashtags || [],
        keywords: data.keywords || []
      };
    },

    addHashtagChip() {
      const raw = this.newHashtagInput.trim().toLowerCase().replace(/\s+/g, '').replace(/^#+/, '');
      if (!raw) return;
      const formatted = `#${raw}`;
      const list = this.pillarSeoConfig[this.activeSeoPillar].hashtags;
      if (!list.includes(formatted)) {
        list.push(formatted);
        this.hasUnsavedConfig = true;
      }
      this.newHashtagInput = '';
    },

    removeHashtagChip(idx) {
      this.pillarSeoConfig[this.activeSeoPillar].hashtags.splice(idx, 1);
      this.hasUnsavedConfig = true;
    },

    addKeywordChip() {
      const phrase = this.newKeywordInput.trim().toLowerCase();
      if (!phrase) return;
      const list = this.pillarSeoConfig[this.activeSeoPillar].keywords;
      if (!list.includes(phrase)) {
        list.push(phrase);
        this.hasUnsavedConfig = true;
      }
      this.newKeywordInput = '';
    },

    removeKeywordChip(idx) {
      this.pillarSeoConfig[this.activeSeoPillar].keywords.splice(idx, 1);
      this.hasUnsavedConfig = true;
    },

    async savePillarSeoConfig() {
      this.savingConfig = true;
      try {
        const payload = this.pillarSeoConfig[this.activeSeoPillar];
        await this.api('PUT', `/api/config/pillars/${encodeURIComponent(this.activeSeoPillar)}`, payload);
        this.hasUnsavedConfig = false;
        this.showToast('Hashtag & keyword berhasil disimpan!');
      } finally {
        this.savingConfig = false;
      }
    },

    /* ----------------------------------------------------------------------
     * HALAMAN 5: BRIEF TREN
     * ---------------------------------------------------------------------- */
    async loadTrendsConfig() {
      const data = await this.api('GET', '/api/config/trends');
      this.trendsConfig = {
        updated: data.updated || '',
        formats: data.formats || [],
        hooks: data.hooks || [],
        audio: data.audio || [],
        moments: data.moments || [],
        notes: data.notes || []
      };
    },

    addTrendItem(key) {
      const val = (this.trendInputs[key] || '').trim();
      if (!val) return;
      this.trendsConfig[key].push(val);
      this.trendInputs[key] = '';
      this.hasUnsavedConfig = true;
    },

    removeTrendItem(key, idx) {
      this.trendsConfig[key].splice(idx, 1);
      this.hasUnsavedConfig = true;
    },

    clearAllTrends() {
      if (!window.confirm('Kosongkan semua daftar tren? AI akan mengabaikan konteks tren.')) return;
      this.trendSections.forEach((s) => {
        this.trendsConfig[s.key] = [];
      });
      this.hasUnsavedConfig = true;
    },

    async saveTrendsConfig() {
      this.savingConfig = true;
      try {
        await this.api('PUT', '/api/config/trends', this.trendsConfig);
        this.trendsConfig.updated = new Date().toISOString().slice(0, 10);
        this.hasUnsavedConfig = false;
        this.showToast('Brief tren berhasil disimpan!');
      } finally {
        this.savingConfig = false;
      }
    },

    /* ----------------------------------------------------------------------
     * HALAMAN 6: BRAND & CAPTION
     * ---------------------------------------------------------------------- */
    async loadBrandConfig() {
      const data = await this.api('GET', '/api/config/brand');
      this.brandConfig = {
        price_per_day: data.price_per_day ?? '[HARGA]',
        whatsapp: data.whatsapp || '(000) 0000000',
        instagram: data.instagram || '@contohbrand',
        default_cta: data.default_cta || {}
      };
    },

    async saveBrandConfig() {
      this.savingConfig = true;
      try {
        const payload = {
          price_per_day: this.brandConfig.price_per_day,
          default_cta: this.brandConfig.default_cta
        };
        await this.api('PUT', '/api/config/brand', payload);
        this.options.default_cta = { ...this.brandConfig.default_cta };
        this.hasUnsavedConfig = false;
        this.showToast('Pengaturan brand berhasil disimpan!');
      } finally {
        this.savingConfig = false;
      }
    },

    async loadCaptionGuideConfig() {
      const data = await this.api('GET', '/api/config/caption-guide');
      this.captionGuideConfig = {
        fields: data.fields || {},
        examples: data.examples || []
      };
    },

    addCaptionExample() {
      if (this.captionGuideConfig.examples.length >= 3) return;
      this.captionGuideConfig.examples.push('');
      this.hasUnsavedConfig = true;
    },

    removeCaptionExample(idx) {
      this.captionGuideConfig.examples.splice(idx, 1);
      this.hasUnsavedConfig = true;
    },

    async saveCaptionGuideConfig() {
      this.savingConfig = true;
      try {
        const cleanedExamples = this.captionGuideConfig.examples
          .map((e) => e.trim())
          .filter(Boolean);
        const payload = {
          fields: this.captionGuideConfig.fields,
          examples: cleanedExamples
        };
        await this.api('PUT', '/api/config/caption-guide', payload);
        this.captionGuideConfig.examples = cleanedExamples;
        this.hasUnsavedConfig = false;
        this.showToast('Panduan caption berhasil disimpan!');
      } finally {
        this.savingConfig = false;
      }
    },

    /* ----------------------------------------------------------------------
     * UTILITAS UMUM
     * ---------------------------------------------------------------------- */
    countHookWords(text) {
      return (text || '').trim().split(/\s+/).filter(Boolean).length;
    },

    countHookChars(text) {
      return (text || '').trim().length;
    },

    isHookOverLimit(text) {
      const maxW = this.options.hook_limits?.max_words || 5;
      const maxC = this.options.hook_limits?.max_chars || 28;
      return this.countHookWords(text) > maxW || this.countHookChars(text) > maxC;
    },

    hookStatsText(text) {
      const maxW = this.options.hook_limits?.max_words || 5;
      const maxC = this.options.hook_limits?.max_chars || 28;
      return `${this.countHookWords(text)}/${maxW} kata • ${this.countHookChars(text)}/${maxC} huruf`;
    },

    pillarIcon(pillarId) {
      const icons = {
        rental: 'bike',
        konstruksi: 'hard-hat',
        profil: 'building-2',
        lowongan: 'briefcase'
      };
      return icons[pillarId] || 'film';
    },

    getPillarLabel(pillarId) {
      const p = this.options.pillars.find((x) => x.id === pillarId);
      return p ? p.label : pillarId;
    },

    formatStyleName(styleId) {
      return (styleId || '')
        .split('_')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
    },

    getMusicName(path) {
      const found = this.options.music.find((m) => m.path === path);
      return found ? found.name : path;
    },

    formatElapsed(sec) {
      const total = Math.max(0, Math.floor(sec || 0));
      const m = String(Math.floor(total / 60)).padStart(2, '0');
      const s = String(total % 60).padStart(2, '0');
      return `${m}:${s}`;
    },

    renderSimpleMarkdown(md) {
      const escaped = (md || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      return escaped
        .split('\n')
        .map((line) => {
          if (line.startsWith('### ')) return `<h3>${line.slice(4)}</h3>`;
          if (line.startsWith('## ')) return `<h2>${line.slice(3)}</h2>`;
          if (line.startsWith('# ')) return `<h1>${line.slice(2)}</h1>`;
          if (line.trim() === '---') return '<hr />';
          if (line.startsWith('- ')) return `<ul><li>${line.slice(2)}</li></ul>`;
          return line ? `<p>${line}</p>` : '';
        })
        .join('')
        .replace(/<\/ul><ul>/g, '')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>');
    },

    showToast(message, type = 'success') {
      const id = `${Date.now()}-${Math.random()}`;
      this.toasts.push({ id, message, type });
      setTimeout(() => {
        this.toasts = this.toasts.filter((t) => t.id !== id);
      }, 3000);
    }
  };
}
