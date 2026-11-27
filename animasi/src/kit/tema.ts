// Sistem gaya kit. Gaya aktif dipilih per video (data.json → "gaya", atau override saat render) lewat pakaiGaya().
// Token di bawah memakai `export let` (live binding): komponen membaca nilai terbaru saat render, jadi satu kode video
// bisa dirender dengan gaya berbeda. Daftar gaya: ./gaya.json (juga dibaca Python untuk font & pilihan di web).
import DAFTAR from './gaya.json';

export type NamaGaya = keyof typeof DAFTAR;
type Def = {
  nama: string;
  deskripsi: string;
  warna: Record<string, string>;
  langit: string[];
  garis: number;
  bayangan: 'keras' | 'lembut' | 'pendar' | 'none';
  sudut: number;
  font: {judul: string; isi: string};
  huruf: {besar: boolean; jarak: number; berat: number; skala?: number};
  teks: 'garis' | 'polos' | 'bayang' | 'pendar' | 'bersih';
  tekstur: 'none' | 'kertas' | 'scanline' | 'grain';
  transisi: 'pita' | 'garis' | 'sobek' | 'kilat' | 'blok';
  gerak: {kaku: number; redam: number; fps: number};
};
export const GAYA_DAFTAR = DAFTAR as unknown as Record<string, Def>;
export const GAYA_BAWAAN = 'racik-flat';

/** Palet aktif (objek tetap, isinya diganti saat gaya berubah). */
export const WARNA = {...GAYA_DAFTAR[GAYA_BAWAAN].warna} as {
  hijau: string; ungu: string; merah: string; tinta: string; putih: string; krem: string; kuning: string;
  langit: string; abu: string; kulit: string; hijauMuda: string; unguMuda: string;
};
export type NamaWarna = keyof typeof WARNA;

/** Gaya aktif lengkap. */
export let GAYA: Def & {id: string} = {...GAYA_DAFTAR[GAYA_BAWAAN], id: GAYA_BAWAAN};
/** Warna garis tinta. */
export let TINTA = WARNA.tinta;
/** Tebal garis tinta (px pada lebar 1080). */
export let GARIS = 7;
/** Jarak bayangan stiker (px). */
export let BAYANGAN = 14;

export function pakaiGaya(id: string | undefined | null): void {
  const nama = id && GAYA_DAFTAR[id] ? id : GAYA_BAWAAN;
  const g = GAYA_DAFTAR[nama];
  GAYA = {...g, id: nama};
  Object.assign(WARNA, g.warna);
  TINTA = WARNA.tinta;
  GARIS = 7 * g.garis;
  BAYANGAN = g.bayangan === 'none' ? 0 : 14;
}

export const FONT_JUDUL = 'RacikJudul';
export const FONT_ISI = 'RacikIsi';

/** Zona aman Reels (px): hindari ±15% atas & ±20% bawah. */
export const AMAN = {atas: 300, bawah: 1520, kiri: 60, kanan: 1020};

export const warna = (w: NamaWarna | string): string => (w in WARNA ? WARNA[w as NamaWarna] : w);

/** Warna isi objek/ikon: di gaya yang latarnya terang-pastel (garis-tipis) atau gelap (neon), "putih" berarti
 * permukaan & tidak terlihat sebagai objek → pakai tinta agar ikon tetap kontras. */
export const warnaObjek = (w: string): string =>
  w === 'putih' && (GAYA.id === 'garis-tipis' || GAYA.id === 'neon-malam' || GAYA.id === 'grainy-gradient') ? TINTA : warna(w);

/** Campur dua warna hex (p = porsi warna b). */
export const campur = (a: string, b: string, p: number): string => {
  const h = (x: string) => [1, 3, 5].map((i) => parseInt(x.slice(i, i + 2), 16));
  const [r1, g1, b1] = h(a);
  const [r2, g2, b2] = h(b);
  const c = (x: number, y: number) => Math.round(x + (y - x) * p).toString(16).padStart(2, '0');
  return `#${c(r1, r2)}${c(g1, g2)}${c(b1, b2)}`;
};

/** Atribut garis SVG yang mengikuti gaya aktif (getter: dibaca saat dispread ketika render). */
export const garisSvg = (lebar = 9) => ({
  get stroke() {
    return TINTA;
  },
  get strokeWidth() {
    return lebar * GAYA.garis;
  },
  strokeLinejoin: 'round' as const,
  strokeLinecap: 'round' as const,
});

/** CSS border tepi stiker/kartu sesuai gaya. */
export const tepi = (lebar = 7): string => (GAYA.garis <= 0 ? 'none' : `${Math.max(1.5, lebar * GAYA.garis)}px solid ${TINTA}`);

/** CSS box-shadow sesuai gaya: keras (stiker), lembut (kertas), pendar (neon), none. */
export const bayang = (jarak = 14, warnaPendar?: string): string => {
  switch (GAYA.bayangan) {
    case 'keras':
      return `${Math.round(jarak * 0.6)}px ${jarak}px 0 ${TINTA}`;
    case 'lembut':
      return `0 ${Math.round(jarak * 0.6)}px ${Math.round(jarak * 1.5)}px rgba(40,25,10,0.32), 0 2px 3px rgba(40,25,10,0.25)`;
    case 'pendar':
      return `0 0 ${jarak * 1.6}px ${warnaPendar ?? WARNA.ungu}, inset 0 0 ${jarak}px ${warnaPendar ?? WARNA.ungu}55`;
    default:
      return 'none';
  }
};

/** Sudut membulat sesuai gaya. */
export const sudut = (r: number): number => r * GAYA.sudut;

/** Gaya huruf judul (perlakuan teks per gaya). */
export const gayaHuruf = (ukuran: number, isi: string): React.CSSProperties => {
  const h = GAYA.huruf;
  const uk = ukuran * (h.skala ?? 1);
  const dasar: React.CSSProperties = {
    fontFamily: FONT_JUDUL,
    fontWeight: h.berat,
    fontSize: uk,
    lineHeight: GAYA.id === 'tipografi-tebal' ? 0.92 : 1.02,
    color: isi,
    textTransform: h.besar ? 'uppercase' : 'none',
    letterSpacing: h.jarak,
  };
  switch (GAYA.teks) {
    case 'garis':
      return {...dasar, WebkitTextStroke: `${Math.round(uk * 0.11)}px ${TINTA}`, paintOrder: 'stroke fill', filter: `drop-shadow(0 ${Math.round(uk * 0.1)}px 0 ${TINTA})`};
    case 'pendar':
      // inti terang + pendar warna (teks terang berpendar ungu, teks berwarna berpendar warnanya sendiri)
      return {...dasar, textShadow: `0 0 ${uk * 0.06}px ${isi}, 0 0 ${uk * 0.22}px ${isi === TINTA ? WARNA.ungu : isi}, 0 0 ${uk * 0.5}px ${isi === TINTA ? WARNA.ungu : isi}`};
    case 'bayang':
      return {...dasar, textShadow: `0 ${uk * 0.05}px ${uk * 0.08}px rgba(40,25,10,0.45)`};
    case 'bersih':
      // putih bersih + bayangan tipis (bang-motion Hukum #4: glow disimpan untuk objek, bukan judul)
      return {...dasar, textShadow: `0 ${uk * 0.03}px ${uk * 0.06}px rgba(0,0,0,0.45)`};
    default:
      return dasar;
  }
};

/**
 * Pelat di belakang tiap baris judul untuk gaya tanpa garis tinta (agar terbaca di latar warna apa pun):
 * garis-tipis = pil putih, kertas = potongan kertas, tipografi = blok tinta. null = gaya bergaris (tanpa pelat).
 * `aksen` = baris yang diberi warna penekanan (mis. kuning) di gaya bergaris.
 */
export const pelatJudul = (aksen: boolean): {bg: string; fg: string} | null => {
  if (GAYA.teks === 'garis' || GAYA.teks === 'pendar' || GAYA.teks === 'bersih') return null;
  if (GAYA.id === 'tipografi-tebal') return aksen ? {bg: WARNA.kuning, fg: TINTA} : {bg: TINTA, fg: WARNA.putih};
  return aksen ? {bg: WARNA.kuning, fg: TINTA} : {bg: WARNA.putih, fg: TINTA};
};

import type React from 'react';
