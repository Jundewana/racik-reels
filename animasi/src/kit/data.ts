// Data video dari `autoreels animasi prepare` (public/<nama>/data.json) + helper waktu.
// Semua waktu di kit memakai DETIK ABSOLUT sejak awal video (sama dengan timing kata narasi).
import {createContext, useContext} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {GAYA} from './tema';

export type Kata = {start: number; end: number; text: string; /** video bicara: detik awal frasa di klip pembicara asli */ src_start?: number | null};

export type Brand = {
  nama: string;
  nama_pendek: string;
  warna: Record<string, string>;
  whatsapp: string;
  instagram: string;
  font: {heading?: string; body?: string};
  logo: string | null;
  harga_sewa_per_hari: string;
  layanan_rental: string[];
  cta_default: string;
};

export type VideoData = {
  nama: string;
  pilar: string;
  brief: string;
  fps: number;
  lebar: number;
  tinggi: number;
  durasi: number;
  durasi_narasi: number;
  audio: {narasi: string | null; musik: string | null; musik_db: number; sfx?: string | null; sfx_db?: number};
  kata: Kata[];
  frasa: Kata[];
  brand: Brand;
  /** id gaya di kit/gaya.json (kosong = racik-flat). */
  gaya?: string;
  /** '3d' = dunia three.js (kit3d) + overlay 2D. */
  dimensi?: '2d' | '3d';
  /** 'footage' = Claude + Remotion memotong footage asli (kit/Klip.tsx); tanpa narasi. */
  mode?: 'footage';
  /** mode footage: montase | narasi | bicara */
  alur?: 'montase' | 'narasi' | 'bicara';
  pembicara?: {file: string; nama: string; durasi: number; lebar: number; tinggi: number};
  cold_open_sec?: number;
};

export const DataCtx = createContext<VideoData | null>(null);

export const useData = (): VideoData => {
  const d = useContext(DataCtx);
  if (!d) throw new Error('Data video belum dimuat (DataCtx kosong).');
  return d;
};

/** Waktu sekarang dalam detik. Gaya stop-motion (gerak.fps > 0, mis. kertas 12 fps) memakai waktu yang dipatah-patah
 * sehingga semua gerak tampak seperti animasi kertas difoto bingkai demi bingkai (audio tetap 30 fps). */
export const useDetik = (): number => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps;
  const patah = GAYA.gerak.fps;
  return patah > 0 ? Math.floor(t * patah) / patah : t;
};

const norm = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');

/**
 * Detik mulai kata/kalimat `teks` di narasi (pencocokan longgar, tanpa tanda baca & spasi), dicari mulai `setelah`.
 * Dipakai untuk menyinkronkan animasi dengan ucapan: `waktuKata(data, 'jas hujan')`.
 * Tidak ketemu → error (agar salah ketik terlihat saat render, bukan animasi yang diam-diam meleset).
 */
export function waktuKata(data: VideoData, teks: string, setelah = 0): number {
  const target = norm(teks);
  const k = data.kata;
  for (let i = 0; i < k.length; i++) {
    if (k[i].start < setelah - 0.01) continue;
    let acc = '';
    for (let j = i; j < k.length && acc.length < target.length; j++) acc += norm(k[j].text);
    if (acc.startsWith(target)) return k[i].start;
  }
  throw new Error(`Kata "${teks}" (setelah ${setelah} dtk) tidak ada di narasi ${data.nama}.`);
}

/** Detik mulai tiap kata dari `teks` (untuk judul kinetik yang muncul kata demi kata sesuai ucapan). */
export function waktuTiapKata(data: VideoData, teks: string, setelah = 0): number[] {
  const out: number[] = [];
  let t = setelah;
  for (const w of teks.split(/\s+/).filter(Boolean)) {
    t = waktuKata(data, w, t);
    out.push(t);
    t += 0.01;
  }
  return out;
}

/** Sedang ada ucapan di detik t (untuk ducking musik). */
export const sedangBicara = (data: VideoData, t: number, pad = 0.12): boolean =>
  data.kata.some((w) => t >= w.start - pad && t <= w.end + pad);
