/* Data contoh & simulator backend untuk mode ?mock=1 (dipindah dari App.jsx). */
import { deepClone } from './format.js';

export const INITIAL_MOCK_STORE = {
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
      },
      {
        id: 'umum',
        label: 'Konten Umum',
        default_style: 'klip_informatif',
        default_brief: 'Potong bagian paling menarik jadi klip singkat yang informatif'
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
      },
      {
        id: 'klip_informatif',
        description: 'Bersih & fokus isi untuk konten umum: potongan tenang, tanpa efek ramai, musik santai',
        cut_pace_sec: [1.5, 3.0],
        music_mood_default: 'santai'
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
      { path: 'footage/lowongan', count: 3 },
      { path: 'footage/umum', count: 2 }
    ],
    default_cta: {
      rental: 'Booking sekarang via WhatsApp (000) 0000000!',
      konstruksi: 'Konsultasi proyek via WhatsApp (000) 0000000!',
      profil: 'Hubungi tim Brand di WhatsApp (000) 0000000!',
      lowongan: 'Kirim lamaran sekarang via WhatsApp (000) 0000000!'
    },
    hook_limits: { max_words: 5, max_chars: 28 },
    engines: [
      { id: 'api', label: 'API online', available: true, reason: '', llm: 'openai/gpt-oss-120b', vision: 'gemini-3.1-flash-lite' },
      { id: 'local', label: 'Lokal (Ollama)', available: true, reason: '', llm: 'qwen3:4b', vision: 'qwen3-vl:4b-instruct' }
    ],
    voices: [
      { id: 'Puck', description: 'ceria & bersemangat' },
      { id: 'Kore', description: 'tegas & jelas' },
      { id: 'Charon', description: 'tenang & informatif' }
    ]
  },

  footageByFolder: {
    'footage/rental': [
      { name: 'mixkit-biker-starting-his-motorcycle.mp4', duration: 11.4, width: 1280, height: 720, size_mb: 6.1, thumb_url: '' },
      { name: '101506-video-720.mp4', duration: 8.2, width: 1280, height: 720, size_mb: 4.5, thumb_url: '' },
      { name: 'garut-gunung-papandayan-ride.mp4', duration: 14.0, width: 1920, height: 1080, size_mb: 11.2, thumb_url: '' },
      { name: 'matic-beat-ready-parkir.mp4', duration: 6.5, width: 1080, height: 1920, size_mb: 5.0, thumb_url: '' },
      { name: 'helm-bersih-serah-terima.mp4', duration: 7.8, width: 1080, height: 1920, size_mb: 5.8, thumb_url: '' },
      { name: 'jalan-raya-cipanas-garut.mp4', duration: 12.1, width: 1920, height: 1080, size_mb: 9.4, thumb_url: '' },
      { name: 'cek-mesin-sebelum-jalan.mp4', duration: 5.9, width: 1080, height: 1920, size_mb: 4.1, thumb_url: '' },
      { name: 'wisatawan-senyum-motor.mp4', duration: 9.3, width: 1080, height: 1920, size_mb: 7.2, thumb_url: '' },
      { name: 'sunset-situ-bagendit.mp4', duration: 10.6, width: 1920, height: 1080, size_mb: 8.7, thumb_url: '' }
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
    ],
    'footage/umum': [
      { name: 'podcast_raditya_dika.mp4', duration: 3556.9, width: 1920, height: 1080, size_mb: 610.6, thumb_url: '' },
      { name: 'cuplikan-tips-youtuber.mp4', duration: 116.0, width: 1920, height: 1080, size_mb: 28.8, thumb_url: '' }
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
      cover_url: ''
    },
    {
      job_id: '20261117-102015-konstruksi',
      created: '2026-11-17 10:20:15',
      pillar: 'konstruksi',
      status: 'perlu_tinjau',
      hook_text: 'Progres Proyek Minggu Ke-4',
      duration: 24.8,
      cover_url: ''
    },
    {
      job_id: '20261115-141209-profil',
      created: '2026-11-15 14:12:09',
      pillar: 'profil',
      status: 'siap_unggah',
      hook_text: 'Kenalan Sama Contoh Brand',
      duration: 18.5,
      cover_url: ''
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
        subtitles: [
          { index: 0, start: 0, end: 2.4, text: 'Kalian termasuk YouTuber' },
          { index: 1, start: 2.4, end: 5.1, text: 'yang bertahan sangat lama sekali.' },
          { index: 2, start: 5.1, end: 8.0, text: 'Kuncinya konsisten sih.' }
        ],
        hook_text: 'Keliling Garut Pakai Motor',
        cta_text: 'Booking motor via WhatsApp sekarang!',
        segments: [
          { index: 0, role: 'hook', source_file: 'mixkit-biker-starting-his-motorcycle.mp4', start: 0.0, end: 2.13, overlay_text: null },
          { index: 1, role: 'isi', source_file: '101506-video-720.mp4', start: 10.44, end: 11.64, overlay_text: 'Unit Terawat & Aman' },
          { index: 2, role: 'isi', source_file: 'helm-bersih-serah-terima.mp4', start: 1.2, end: 2.75, overlay_text: 'Gratis 2 Helm Bersih' },
          { index: 3, role: 'isi', source_file: 'garut-gunung-papandayan-ride.mp4', start: 4.0, end: 6.1, overlay_text: 'Siap Gas ke Wisata Garut' }
        ]
      },
      variant: { available: true, flow: 'video', duration: 20, purpose: null, talk_full: false },
      visual: {
        model: 'gemini/gemini-3.5-flash-lite', score: 4, summary: 'Teks terbaca dan subjek utuh; satu frame isi agak gelap.',
        issues: [{ frame: 4, severity: 'ringan', problem: 'Frame isi agak gelap sehingga motor kurang menonjol.', fix: 'Pilih adegan yang lebih terang untuk segmen ini.' }],
        frames: [{ frame: 1, sec: 0.3, label: 'hook awal' }, { frame: 4, sec: 5.2, label: 'segmen isi' }]
      },
      critic: {
        chosen_round: 1,
        critic_revisions: 1,
        final: {
          round: 1, average: 4.3, hook: 5, passed: true,
          scores: { hook: 5, instruction_fit: 4, flow: 4, pace: 5, text_readability: 4, cta: 4, brand: 4 },
          hook_comment: 'Motor di depan pemandangan Papandayan langsung menarik perhatian wisatawan.',
          revision_notes: ['Segmen #5: teks harga bisa dipersingkat jadi 3 kata.'],
          summary: 'Alur jelas dari hook ke CTA; tempo cocok dengan gaya energik.'
        },
        rounds: [
          { round: 0, average: 3.6, hook: 3, passed: false },
          { round: 1, average: 4.3, hook: 5, passed: true }
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

  narrations: [
    { path: 'footage/_narasi/promo-rental-narasi.m4a', name: 'promo-rental-narasi.m4a', duration: 39.8, size_mb: 0.6, url: '' }
  ],

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

/** Router backend tiruan; store dimutasi langsung (seperti server sungguhan). */
export function createMockApi(storeRef) {
  return async (method, path, body) => {
    await new Promise((r) => setTimeout(r, 120));
    const store = storeRef.current;

    // Job yang masih berjalan (harus dicek sebelum rute /api/jobs/{id})
    if (method === 'GET' && path === '/api/jobs/active') {
      const now = Date.now();
      const jobs = Object.entries(store.activeSimulations)
        .filter(([, sim]) => (now - sim.startedAt) / 1000 < sim.durationSec)
        .map(([job_id, sim]) => ({
          job_id,
          state: 'berjalan',
          kind: sim.payload?.video_path ? 'import' : 'create',
          label: 'Simulasi',
          percent: Math.round(((now - sim.startedAt) / 1000 / sim.durationSec) * 100)
        }));
      return { jobs };
    }

    if (method === 'GET' && path === '/api/options') {
      return deepClone(store.options);
    }

    if (method === 'GET' && path.startsWith('/api/footage')) {
      const urlObj = new URL(path, 'http://localhost');
      const folder = urlObj.searchParams.get('folder') || 'footage/rental';
      return { folder, clips: deepClone(store.footageByFolder[folder] || []) };
    }

    if (method === 'POST' && path === '/api/footage/upload') {
      const pillar = body.get('pillar') || 'rental';
      const folder = `footage/${pillar}`;
      const files = body.getAll('files[]');
      if (!store.footageByFolder[folder]) store.footageByFolder[folder] = [];
      const uploadedNames = [];
      files.forEach((f) => {
        uploadedNames.push(f.name);
        store.footageByFolder[folder].unshift({
          name: f.name,
          duration: +(6 + Math.random() * 9).toFixed(1),
          width: 1080,
          height: 1920,
          size_mb: +Math.max(1.2, f.size / (1024 * 1024)).toFixed(1),
          thumb_url: ''
        });
      });
      const folderEntry = store.options.footage_folders.find((x) => x.path === folder);
      if (folderEntry) folderEntry.count = store.footageByFolder[folder].length;
      return { folder, files: uploadedNames };
    }

    if (method === 'GET' && path === '/api/narration') {
      return { files: deepClone(store.narrations || []) };
    }

    if (method === 'POST' && path === '/api/narration/transcribe') {
      const texts = [
        'Liburan ke Garut, tapi pusing transportasi?',
        'Jangan ribet, sewa motor aja',
        'di Rental Motor nomor satu.',
        'Ada matic dan manual, harian atau mingguan.',
        'Booking sekarang lewat WhatsApp.'
      ];
      const original = [...texts];
      original[0] = 'Liburan ke Garut, tapi ping transportasi';
      original[3] = 'adam etik dan manual, harian atau mingguan';
      store.draft = {
        id: '20261124-090000-mock',
        source: body.narration_path,
        reviewed: false,
        duration: 12.4,
        audio_url: '',
        phrases: texts.map((t, i) => ({ index: i, start: i * 2.5, end: i * 2.5 + 2.4, text: t, original: original[i], ai_fixed: t !== original[i] }))
      };
      return deepClone(store.draft);
    }

    if (method === 'POST' && path === '/api/talk/transcribe') {
      const texts = Array.from({ length: 30 }, (_, i) => `Frasa contoh nomor ${i + 1} dari podcast`);
      const original = texts.map((t, i) => (i % 7 === 3 ? t.replace('podcast', 'pot kas') : t));
      store.draft = {
        id: '20261125-090000-mock-bicara', kind: 'bicara', speaker_clip: body.talk_clip, talk_full: Boolean(body.talk_full),
        source: `${body.input_path}/${body.talk_clip}`, reviewed: false, duration: 8.0, audio_url: '',
        phrases: texts.map((t, i) => ({ index: i, start: i * 2.7, end: i * 2.7 + 2.6, text: t, original: original[i], ai_fixed: t !== original[i] }))
      };
      return deepClone(store.draft);
    }

    if (method === 'PUT' && path.startsWith('/api/narration/drafts/')) {
      store.draft = { ...store.draft, reviewed: true, phrases: store.draft.phrases.map((p, i) => ({ ...p, text: body.texts[i] })) };
      return deepClone(store.draft);
    }

    if (method === 'POST' && path === '/api/narration/upload') {
      const f = body.get('file');
      const item = { path: `footage/_narasi/${f.name}`, name: f.name, duration: 38.5, size_mb: 0.6, url: '' };
      store.narrations = [item, ...(store.narrations || [])];
      return { path: item.path, name: item.name };
    }

    if (method === 'GET' && path === '/api/import/candidates') {
      return { candidates: [{ path: 'footage/profil/testimoni-pelanggan/edit/final.mp4', name: 'testimoni-pelanggan/final.mp4', size_mb: 14.2, modified: '2026-11-19 09:40', has_transcript: true, source: 'video-use' }] };
    }

    if (method === 'POST' && path === '/api/import') {
      const jobId = `${Date.now()}-${body.pillar}`;
      store.activeSimulations[jobId] = { startedAt: Date.now(), durationSec: 10, payload: { ...deepClone(body), input_path: body.video_path, duration: 30 }, isRerender: false };
      return { job_id: jobId };
    }

    if (method === 'POST' && path === '/api/highlights') {
      store.highlight = { task_id: 'mock-cuplikan', startedAt: Date.now() };
      return { task_id: 'mock-cuplikan' };
    }

    if (method === 'GET' && path.startsWith('/api/highlights/')) {
      const pct = Math.min(100, Math.round(((Date.now() - (store.highlight?.startedAt || 0)) / 4000) * 100));
      const done = pct >= 100;
      return {
        task_id: 'mock-cuplikan',
        state: done ? 'selesai' : 'berjalan',
        percent: pct,
        detail: done ? '3 cuplikan ditemukan' : `transkripsi ${pct}%`,
        video_url: '',
        candidates: done
          ? [
              { rank: 1, title: 'Kunci jadi YouTuber: konsisten', reason: 'Tips singkat yang relatable dan berdiri sendiri.', score: 5, start: 3178, end: 3294, duration: 116, hook: 'Kuncinya konsisten.', preview: 'Kalau aku dari dulu kuncinya konsisten…' },
              { rank: 2, title: 'Risiko kesehatan main game seharian', reason: 'Pengalaman nyata soal postur dan back pain.', score: 5, start: 2606, end: 2786, duration: 180, hook: 'Duduk lama itu bahaya.', preview: 'Jadi sebenernya bukan penyakit…' },
              { rank: 3, title: 'Asal-usul kolaborasi parfum gaming', reason: 'Cerita di balik kolaborasi empat kreator.', score: 4, start: 1199, end: 1378, duration: 179, hook: 'Awalnya dari satu obrolan.', preview: 'Aku yang pertama kali kerja sama…' }
            ]
          : []
      };
    }

    if (method === 'POST' && /^\/api\/jobs\/[^/]+\/variants$/.test(path)) {
      const ids = (body.variants || []).map((v, i) => {
        const jobId = `mock-varian-${i + 1}-${Date.now() + i}`;
        store.activeSimulations[jobId] = { startedAt: Date.now(), durationSec: 15, payload: deepClone(v), isRerender: false };
        return jobId;
      });
      return { job_ids: ids };
    }

    if (method === 'POST' && /^\/api\/highlights\/[^/]+\/jobs$/.test(path)) {
      const ids = (body.ranks || []).map((r, i) => {
        const jobId = `mock-cuplikan-${r}-${Date.now() + i}`;
        store.activeSimulations[jobId] = { startedAt: Date.now(), durationSec: 20, payload: deepClone(body), isRerender: false };
        return jobId;
      });
      return { job_ids: ids, folder: 'footage/umum/cuplikan' };
    }

    if (method === 'POST' && path === '/api/jobs') {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, '0');
      const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
      const jobId = `${stamp}-${body.pillar || 'rental'}`;

      store.activeSimulations[jobId] = {
        startedAt: Date.now(),
        durationSec: 20, // Simulasi ±20 detik 0 -> 100%
        payload: deepClone(body),
        isRerender: false
      };
      return { job_id: jobId };
    }

    if (method === 'POST' && /^\/api\/jobs\/[^/]+\/voiceover(\/recording)?$/.test(path)) {
      const jobId = path.split('/')[3];
      store.activeSimulations[jobId] = { startedAt: Date.now(), durationSec: 8, payload: {}, isRerender: true };
      return { job_id: jobId };
    }

    if (method === 'POST' && /^\/api\/jobs\/[^/]+\/rerender$/.test(path)) {
      const jobId = path.split('/')[3];
      const detail = store.jobDetails[jobId];
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
        detail.status = detail.checklist.some((c) => c.required && !c.passed) ? 'perlu_tinjau' : 'siap_unggah';

        const listEntry = store.jobsList.find((j) => j.job_id === jobId);
        if (listEntry) {
          listEntry.hook_text = detail.edl.hook_text;
          listEntry.status = detail.status;
        }
      }

      store.activeSimulations[jobId] = {
        startedAt: Date.now(),
        durationSec: 8,
        payload: detail || {},
        isRerender: true
      };
      return { job_id: jobId };
    }

    if (method === 'GET' && /^\/api\/jobs\/[^/]+\/progress$/.test(path)) {
      const jobId = path.split('/')[3];
      const sim = store.activeSimulations[jobId];
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

      const idx = sim.isRerender ? (ratio < 0.7 ? 4 : 5) : Math.min(5, Math.floor(ratio * 6));
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

      if (isDone && !store.jobDetails[jobId]) {
        const hookUsed = (sim.payload.hook_text && sim.payload.hook_text.trim()) || 'Keliling Garut Pakai Motor';
        const ctaUsed =
          (sim.payload.cta_text && sim.payload.cta_text.trim()) ||
          store.options.default_cta[sim.payload.pillar] ||
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
          caption: `${sim.payload.brief || 'Promo spesial dari Contoh Brand!'}\n\n📲 ${ctaUsed}\n📍 Garut, Jawa Barat\n\n${(store.configPillars[sim.payload.pillar]?.hashtags || ['#brandenergi', '#garut']).join(' ')}`,
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

        store.jobDetails[jobId] = newDetail;
        store.jobsList.unshift({
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

    if (method === 'GET' && path === '/api/jobs') {
      return { jobs: deepClone(store.jobsList) };
    }

    if (method === 'GET' && /^\/api\/jobs\/[^/]+$/.test(path)) {
      const jobId = path.split('/')[3];
      const detail = store.jobDetails[jobId] || Object.values(store.jobDetails)[0];
      return deepClone(detail);
    }

    if (path === '/api/config/hooks') {
      if (method === 'GET') return deepClone(store.configHooks);
      if (method === 'PUT') {
        store.configHooks = deepClone(body);
        return { ok: true };
      }
    }

    if (path.startsWith('/api/config/pillars/')) {
      const pillar = path.split('/').pop();
      if (method === 'GET') return deepClone(store.configPillars[pillar] || { hashtags: [], keywords: [] });
      if (method === 'PUT') {
        store.configPillars[pillar] = deepClone(body);
        return { ok: true };
      }
    }

    if (path === '/api/config/trends') {
      if (method === 'GET') return deepClone(store.configTrends);
      if (method === 'PUT') {
        store.configTrends = { ...deepClone(body), updated: new Date().toISOString().slice(0, 10) };
        return { ok: true };
      }
    }

    if (path === '/api/config/brand') {
      if (method === 'GET') return deepClone(store.configBrand);
      if (method === 'PUT') {
        store.configBrand.price_per_day = body.price_per_day;
        store.configBrand.default_cta = deepClone(body.default_cta);
        store.options.default_cta = deepClone(body.default_cta);
        return { ok: true };
      }
    }

    if (path.startsWith('/api/config/preferences')) {
      store.configPreferences = store.configPreferences || {
        edited_jobs: 3, new_since_summary: 1, last_summarized: '2026-11-24 20:15:00',
        text: '## Ringkasan otomatis\n- [rental] Teks hook maks 6 kata dan sebut harga bila ada.\n- CTA pendek: "Chat WA sekarang".\n\n## Catatan manual\n- Tanpa emoji di teks video.\n'
      };
      if (method === 'PUT') store.configPreferences = { ...store.configPreferences, text: body.text };
      if (method === 'POST') store.configPreferences = { ...store.configPreferences, new_since_summary: 0 };
      return deepClone(store.configPreferences);
    }

    if (path === '/api/config/caption-guide') {
      if (method === 'GET') return deepClone(store.configCaptionGuide);
      if (method === 'PUT') {
        store.configCaptionGuide = deepClone(body);
        return { ok: true };
      }
    }

    return { ok: true };
  };
}
