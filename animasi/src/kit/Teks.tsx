// Teks khas kit: judul kinetik bergaris tinta (muncul kata demi kata) & subtitle karaoke.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useData, useDetik} from './data';
import {keluar, pop} from './gerak';
import {AMAN, FONT_JUDUL, GAYA, TINTA, WARNA, bayang, gayaHuruf, pelatJudul, sudut, tepi, warna} from './tema';

/** Masuknya satu kata sesuai karakter gaya: pantul (flat/kertas), naik halus (garis-tipis), dari balik masker
 * (tipografi), berkedip menyala (neon). p = kemajuan 0..1 (pegas). */
const masukKata = (p: number, t: number, tm: number): React.CSSProperties => {
  switch (GAYA.id) {
    case 'garis-tipis':
      return {transform: `translateY(${(1 - Math.min(1, p)) * 30}px)`, opacity: Math.min(1, p * 1.6)};
    case 'tipografi-tebal':
      return {transform: `translateY(${(1 - Math.min(1, p)) * 105}%)`};
    case 'neon-malam': {
      const d = t - tm;
      const kedip = d < 0 ? 0 : d < 0.05 ? 1 : d < 0.09 ? 0.2 : d < 0.13 ? 1 : d < 0.16 ? 0.45 : 1;
      return {transform: `scale(${0.9 + 0.1 * Math.min(1, p)})`, opacity: kedip};
    }
    default:
      return {transform: `translateY(${(1 - p) * 60}px) scale(${0.3 + 0.7 * p}) rotate(${(1 - p) * -12}deg)`, opacity: Math.min(1, p * 3)};
  }
};

export type BarisJudul = {teks: string; warna?: string; ukuran?: number};

/**
 * Judul besar. Tiap kata "pop" di waktunya: `waktu` (detik per kata, mis. dari waktuTiapKata) atau
 * `mulai` + `jeda` antar kata. `sampai` = detik mulai menghilang.
 */
export const Judul: React.FC<{
  baris: (string | BarisJudul)[];
  mulai?: number;
  waktu?: number[];
  jeda?: number;
  sampai?: number;
  y?: number;
  ukuran?: number;
  warna?: string;
  miring?: number;
  /** false = huruf kalimat (sentence case) walau gaya memakai kapital; true = paksa kapital (satu momen penekanan). */
  kapital?: boolean;
  /** Perataan & posisi blok judul (variasikan antar adegan, jangan selalu tengah). */
  rata?: 'kiri' | 'tengah' | 'kanan';
}> = ({baris, mulai = 0, waktu, jeda = 0.09, sampai, y = 760, ukuran = 150, warna: w = 'putih', miring = -3, kapital, rata = 'tengah'}) => {
  const t = useDetik();
  const hilang = sampai !== undefined ? keluar(t, sampai, 0.2) : 1;
  if (hilang <= 0) return null;
  let n = 0;
  return (
    <AbsoluteFill style={{alignItems: rata === 'kiri' ? 'flex-start' : rata === 'kanan' ? 'flex-end' : 'center', paddingLeft: AMAN.kiri, paddingRight: 1080 - AMAN.kanan}}>
      <div
        style={{
          position: 'absolute',
          top: y,
          transform: `translateY(-50%) rotate(${miring}deg) scale(${0.85 + 0.15 * hilang})`,
          transformOrigin: rata === 'kiri' ? 'left center' : rata === 'kanan' ? 'right center' : 'center',
          opacity: hilang,
          display: 'flex',
          flexDirection: 'column',
          alignItems: rata === 'kiri' ? 'flex-start' : rata === 'kanan' ? 'flex-end' : 'center',
          gap: 6,
          width: AMAN.kanan - AMAN.kiri,
        }}
      >
        {baris.map((b, bi) => {
          const bb: BarisJudul = typeof b === 'string' ? {teks: b} : b;
          const uk = bb.ukuran ?? ukuran;
          const kataBaris = bb.teks.split(/\s+/);
          const awal = n;
          const tAwal = waktu?.[awal] ?? mulai + awal * jeda;
          const aksen = !!bb.warna && bb.warna !== 'putih';
          const pelat = pelatJudul(aksen);
          const pPelat = pop(t, tAwal - 0.04, 260, 18);
          const topeng = GAYA.id === 'tipografi-tebal';
          return (
            <div
              key={bi}
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                justifyContent: rata === 'kiri' ? 'flex-start' : rata === 'kanan' ? 'flex-end' : 'center',
                columnGap: uk * 0.28,
                ...(pelat
                  ? {
                      background: pelat.bg,
                      padding: `${uk * 0.06}px ${uk * 0.24}px ${uk * 0.1}px`,
                      borderRadius: sudut(uk * 0.3),
                      border: GAYA.id === 'garis-tipis' ? tepi(7) : 'none',
                      boxShadow: bayang(10),
                      transform: `scaleX(${Math.min(1, pPelat)}) rotate(${GAYA.id === 'kertas' ? (bi % 2 ? 1.6 : -1.4) : 0}deg)`,
                      opacity: pPelat > 0 ? 1 : 0,
                    }
                  : {}),
              }}
            >
              {kataBaris.map((kata, ki) => {
                const idx = n++;
                const tm = waktu?.[idx] ?? mulai + idx * jeda;
                const p = pop(t, tm, 220, 12);
                const minta = bb.warna ?? w;
                const isi = pelat ? pelat.fg : (GAYA.teks === 'pendar' || GAYA.teks === 'bersih') && minta === 'putih' ? TINTA : warna(minta);
                return (
                  <span key={ki} style={{display: 'inline-block', overflow: topeng ? 'hidden' : undefined, paddingBottom: topeng ? 4 : 0}}>
                    <span
                      style={{
                        ...gayaHuruf(uk, isi),
                        ...(kapital === undefined ? {} : {textTransform: kapital ? 'uppercase' : 'none', fontWeight: kapital ? GAYA.huruf.berat : Math.min(GAYA.huruf.berat, 700)}),
                        display: 'inline-block',
                        ...masukKata(p, t, tm),
                      }}
                    >
                      {kata}
                    </span>
                  </span>
                );
              })}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** Label kecil bergaris tinta (mis. nama tempat, keterangan). Posisi pusat x,y. */
export const Label: React.FC<{
  teks: string;
  x: number;
  y: number;
  mulai: number;
  sampai?: number;
  warna?: string;
  warnaTeks?: string;
  ukuran?: number;
  miring?: number;
}> = ({teks, x, y, mulai, sampai, warna: w = 'putih', warnaTeks = 'tinta', ukuran = 52, miring = 0}) => {
  const t = useDetik();
  const p = pop(t, mulai);
  const hilang = sampai !== undefined ? keluar(t, sampai, 0.2) : 1;
  if (p <= 0 || hilang <= 0) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        transform: `translate(-50%, -50%) scale(${p * hilang}) rotate(${miring}deg)`,
        background: warna(w),
        color: warna(warnaTeks),
        fontFamily: FONT_JUDUL,
        fontWeight: 800,
        fontSize: ukuran,
        padding: `${ukuran * 0.18}px ${ukuran * 0.45}px`,
        border: tepi(6),
        borderRadius: sudut(ukuran * 0.35),
        boxShadow: bayang(9),
        whiteSpace: 'nowrap',
        textTransform: 'uppercase',
      }}
    >
      {teks}
    </div>
  );
};

/**
 * Subtitle karaoke dari narasi: maks `maksKata` per tampilan, kata yang sedang diucapkan disorot.
 * `sembunyi`: rentang detik [a, b] tanpa subtitle (mis. saat judul besar sudah menulis kalimat yang sama).
 */
export const Subtitle: React.FC<{y?: number; maksKata?: number; sembunyi?: [number, number][]; ukuran?: number}> = ({
  y = 1400,
  maksKata = 4,
  sembunyi = [],
  ukuran = 62,
}) => {
  const data = useData();
  const t = useDetik();
  if (sembunyi.some(([a, b]) => t >= a && t < b)) return null;
  // kelompokkan kata per frasa lalu potong per maksKata
  const grup: {start: number; end: number; kata: typeof data.kata}[] = [];
  for (const f of data.frasa) {
    const ks = data.kata.filter((k) => (k.start + k.end) / 2 >= f.start && (k.start + k.end) / 2 < f.end);
    for (let i = 0; i < ks.length; i += maksKata) {
      const g = ks.slice(i, i + maksKata);
      grup.push({start: g[0].start, end: g[g.length - 1].end, kata: g});
    }
  }
  const aktif = grup.find((g, i) => t >= g.start - 0.05 && t < (grup[i + 1]?.start ?? g.end + 0.4) - 0.05);
  if (!aktif || t > aktif.end + 0.6) return null;
  const p = pop(t, aktif.start - 0.05, 260, 16);
  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <div
        style={{
          position: 'absolute',
          top: y,
          transform: `translateY(-50%) scale(${0.9 + 0.1 * p})`,
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: 14,
          maxWidth: 960,
        }}
      >
        {aktif.kata.map((k, i) => {
          const on = t >= k.start - 0.03 && t < k.end + 0.1;
          const lewat = t >= k.start - 0.03;
          return (
            <span
              key={i}
              style={{
                fontFamily: FONT_JUDUL,
                fontWeight: 800,
                fontSize: ukuran,
                padding: '2px 14px 6px',
                borderRadius: 14,
                color: on ? TINTA : WARNA.putih,
                background: on ? WARNA.kuning : 'transparent',
                border: on ? `5px solid ${TINTA}` : '5px solid transparent',
                WebkitTextStroke: on ? undefined : `9px ${TINTA}`,
                paintOrder: 'stroke fill',
                opacity: lewat ? 1 : 0.55,
                transform: on ? 'scale(1.08) rotate(-2deg)' : undefined,
              }}
            >
              {k.text.replace(/[.,!?;:]+$/, '')}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
