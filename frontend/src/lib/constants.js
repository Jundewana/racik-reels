import {
  Clapperboard,
  FileVideo,
  History,
  Sparkles,
  Hash,
  TrendingUp,
  BadgeCheck,
  SlidersHorizontal,
  Bike,
  HardHat,
  Building2,
  Briefcase,
  Film,
  Library,
  Wand2
} from 'lucide-react';

/** USE_MOCK: tambahkan ?mock=1 di URL untuk mode simulasi (tanpa backend). */
export const USE_MOCK = new URLSearchParams(window.location.search).has('mock');

/** Nama aplikasi — ganti di sini saja (juga judul tab di index.html). */
export const APP_NAME = 'Racik';
export const APP_TITLE = `${APP_NAME} — Contoh Brand`;

/* Navigasi: dua kelompok — produksi video dan bahan yang dibaca AI */
export const NAV_PRODUCTION = [
  { id: 'create', label: 'Buat video', short: 'Buat', Icon: Clapperboard },
  { id: 'animasi', label: 'Animasi', short: 'Animasi', Icon: Wand2 },
  { id: 'history', label: 'Riwayat', short: 'Riwayat', Icon: History }
];

export const NAV_MATERIALS = [
  { id: 'hooks', label: 'Pustaka hook', Icon: Sparkles, desc: 'Kalimat pembuka 3 detik pertama per pilar' },
  { id: 'hashtags', label: 'Hashtag & keyword', Icon: Hash, desc: 'Tagar dan frasa pencarian untuk caption' },
  { id: 'trends', label: 'Brief tren', Icon: TrendingUp, desc: 'Tren & momen Garut minggu ini' },
  { id: 'brand', label: 'Brand & caption', Icon: BadgeCheck, desc: 'Harga, CTA default, gaya bahasa caption' },
  { id: 'preferences', label: 'Preferensi', Icon: SlidersHorizontal, desc: 'Selera Anda, dipelajari dari editan' }
];

export const MATERIAL_PAGE_IDS = NAV_MATERIALS.map((n) => n.id);

/* Item menu bawah di HP (3 item; "Bahan AI" membuka daftar halaman bahan). Impor ada di halaman Riwayat. */
export const NAV_MOBILE = [
  ...NAV_PRODUCTION,
  { id: 'materials', label: 'Bahan AI', short: 'Bahan AI', Icon: Library }
];

export const WIZARD_STEPS = [
  { num: 1, label: 'Footage' },
  { num: 2, label: 'Atur' },
  { num: 3, label: 'Proses' },
  { num: 4, label: 'Hasil' }
];

export const PROCESS_STEPS = [
  { key: 'ingest', label: 'Menyiapkan footage' },
  { key: 'analyze', label: 'Menganalisis adegan & musik' },
  { key: 'describe', label: 'AI melihat tiap adegan' },
  { key: 'direct', label: 'AI menyusun urutan edit' },
  { key: 'render', label: 'Merender video' },
  { key: 'checklist', label: 'Memeriksa checklist siap unggah' }
];

// Alur impor video jadi (step_index sama dengan autoreels/progress.py)
export const IMPORT_PROCESS_STEPS = [
  { key: 'ingest', label: 'Memeriksa video' },
  { key: 'analyze', label: 'Analisis adegan (dilewati untuk impor)', skipped: true },
  { key: 'describe', label: 'Deskripsi visual (dilewati untuk impor)', skipped: true },
  { key: 'direct', label: 'AI menulis caption & hashtag' },
  { key: 'render', label: 'Menyesuaikan ukuran, logo & CTA' },
  { key: 'checklist', label: 'Memeriksa checklist siap unggah' }
];

export const HOOK_TYPES = [
  { id: 'visual_wow', label: 'Visual wow', desc: 'Gambar yang langsung menarik di detik pertama' },
  { id: 'pertanyaan', label: 'Pertanyaan', desc: 'Memancing rasa ingin tahu penonton' },
  { id: 'harga', label: 'Harga', desc: 'Menonjolkan promo atau nilai hemat' },
  { id: 'before_after', label: 'Sebelum–sesudah', desc: 'Perbandingan kondisi awal dan akhir' },
  { id: 'angka', label: 'Angka', desc: 'Fakta, jumlah, atau durasi yang spesifik' },
  { id: 'kontras', label: 'Kontras', desc: 'Pernyataan tak terduga yang mematahkan anggapan' }
];

export const hookTypeLabel = (id) => HOOK_TYPES.find((t) => t.id === id)?.label || id;

export const TREND_SECTIONS = [
  { key: 'formats', label: 'Format yang sedang ramai', placeholder: 'Mis. transisi cepat mengikuti ketukan musik' },
  { key: 'hooks', label: 'Gaya hook yang naik', placeholder: 'Mis. pertanyaan 3 kata di tengah layar' },
  { key: 'audio', label: 'Audio trending (judul saja)', placeholder: 'Mis. Acoustic Sunda Chill Beat' },
  { key: 'moments', label: 'Momen musiman & event Garut', placeholder: 'Mis. libur panjang akhir pekan' },
  { key: 'notes', label: 'Catatan lain', placeholder: 'Catatan tambahan untuk AI' }
];

export const PILLAR_ICONS = { rental: Bike, konstruksi: HardHat, profil: Building2, lowongan: Briefcase, umum: Sparkles };
export const pillarIcon = (id) => PILLAR_ICONS[id] || Film;

export const VOICEOVER_MODES = [
  { id: 'rekam', label: 'Suara sendiri', desc: 'Naskah ditulis AI, Anda rekam setelah video jadi' },
  { id: 'gemini', label: 'Suara AI', desc: 'Naskah dibacakan otomatis oleh Gemini' },
  { id: 'none', label: 'Tanpa voice over', desc: 'Musik dan teks saja' }
];

export const STATUS_LABEL = { siap_unggah: 'Siap unggah', perlu_tinjau: 'Perlu tinjau' };
