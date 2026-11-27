// Kalender streak "1 video / hari": kotak hari terisi ikon play satu per satu, lalu penghitung melonjak ke 3.650 video
// (= 10 tahun × 365 hari, sesuai ucapan "satu video satu hari dilakukan 10 tahun"). Khas video radityadika3d.
import React from 'react';
import {useDetik} from '../../kit/data';
import {keluar, pop} from '../../kit/gerak';
import {FONT_JUDUL, TINTA, WARNA, bayang, campur, garisSvg, sudut} from '../../kit/tema';
import {gelap, halus} from './objek3d';

const KOLOM = 7;
const BARIS = 4;
const titik = (n: number) => String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');

export const KalenderStreak: React.FC<{
  mulai: number;
  /** detik kotak mulai terisi */
  isi: number;
  /** penghitung naik dari `hitungDari` sampai `hitungSampai` */
  hitungDari: number;
  hitungSampai: number;
  sampai: number;
  y?: number;
}> = ({mulai, isi, hitungDari, hitungSampai, sampai, y = 600}) => {
  const t = useDetik();
  const p = pop(t, mulai, 220, 14);
  const h = keluar(t, sampai, 0.25);
  if (p <= 0 || h <= 0) return null;
  const L = 760;
  const H = 560;
  const sel = 86;
  const tinggiSel = 64;
  const jarak = (L - 2 * 44 - KOLOM * sel) / (KOLOM - 1);
  const total = KOLOM * BARIS;
  const terisi = Math.floor(Math.max(0, (t - isi) / ((hitungDari - isi) / total)));
  const q = halus((t - hitungDari) / (hitungSampai - hitungDari));
  const angka = t < hitungDari ? Math.min(total, terisi) : lerpAngka(total, 3650, 1 - Math.pow(1 - q, 3));
  const stempel = pop(t, hitungSampai - 0.1, 260, 12);
  const kosong = campur(WARNA.putih, TINTA, 0.12);
  return (
    <div
      style={{
        position: 'absolute',
        left: 540,
        top: y,
        transform: `translate(-50%, -50%) scale(${p * (0.9 + 0.1 * h)}) rotate(${-2 + 2 * p}deg)`,
        opacity: h,
      }}
    >
      <svg width={L} height={H} viewBox={`0 0 ${L} ${H}`} style={{overflow: 'visible', borderRadius: sudut(40), boxShadow: bayang(14)}}>
        <rect x={0} y={0} width={L} height={H} rx={sudut(40)} fill={WARNA.putih} {...garisSvg(7)} />
        <path d={`M0 ${sudut(40)} Q0 0 ${sudut(40)} 0 H${L - sudut(40)} Q${L} 0 ${L} ${sudut(40)} V108 H0 Z`} fill={WARNA.merah} {...garisSvg(7)} />
        {/* cincin kalender */}
        {[180, L - 180].map((x) => (
          <rect key={x} x={x - 14} y={-30} width={28} height={64} rx={14} fill={WARNA.kuning} {...garisSvg(6)} />
        ))}
        <text x={L / 2} y={72} textAnchor="middle" fontFamily={FONT_JUDUL} fontWeight={800} fontSize={56} fill={terangPada(WARNA.merah)}>
          1 video / hari
        </text>
        {Array.from({length: total}, (_, i) => {
          const c = i % KOLOM;
          const r = Math.floor(i / KOLOM);
          const x = 44 + c * (sel + jarak);
          const yy = 136 + r * (tinggiSel + 14);
          const on = i < terisi;
          const pk = on ? pop(t, isi + i * ((hitungDari - isi) / total), 320, 14) : 0;
          return (
            <g key={i}>
              <rect x={x} y={yy} width={sel} height={tinggiSel} rx={sudut(14)} fill={on ? (i % 3 === 2 ? WARNA.hijau : WARNA.kuning) : kosong} {...garisSvg(on ? 4 : 2)} />
              {on ? (
                <path
                  d="M-12 -15 L18 0 L-12 15 Z"
                  transform={`translate(${x + sel / 2} ${yy + tinggiSel / 2}) scale(${Math.min(1.25, pk)})`}
                  fill={gelap()}
                />
              ) : null}
            </g>
          );
        })}
        <text x={44} y={H - 42} fontFamily={FONT_JUDUL} fontWeight={800} fontSize={84} fill={TINTA}>
          {titik(angka)}
          <tspan fontSize={44} dx={14}>
            video
          </tspan>
        </text>
        {stempel > 0 ? (
          <g transform={`translate(${L - 150} ${H - 70}) rotate(-8) scale(${Math.max(0.01, 2 - stempel)})`} opacity={Math.min(1, stempel * 2)}>
            <rect x={-118} y={-46} width={236} height={92} rx={sudut(20)} fill={WARNA.ungu} {...garisSvg(6)} />
            <text x={0} y={20} textAnchor="middle" fontFamily={FONT_JUDUL} fontWeight={800} fontSize={58} fill={terangPada(WARNA.ungu)}>
              10 tahun
            </text>
          </g>
        ) : null}
      </svg>
    </div>
  );
};

const lerpAngka = (a: number, b: number, q: number) => a + (b - a) * Math.min(1, Math.max(0, q));

/** Warna teks yang terbaca di atas warna isi `latar` (pilih tinta atau "putih" gaya, mana yang lebih kontras). */
const terangPada = (latar: string) => {
  const l = (hex: string) => {
    const v = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
  };
  const a = TINTA;
  const b = WARNA.putih;
  return Math.abs(l(a) - l(latar)) > Math.abs(l(b) - l(latar)) ? a : b;
};
