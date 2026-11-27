// Teks di atas footage asli (hook, harga, info, CTA): putih tebal + outline, pop masuk, di dalam zona aman Reels.
// Waktu dalam DETIK ABSOLUT sejak awal video, sama seperti kit lain.
import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {AMAN, FONT_JUDUL} from './tema';

export const TeksFootage: React.FC<{
  /** maks 2 baris (pisahkan dengan \n), ±5 kata per baris */
  teks: string;
  mulai: number;
  sampai: number;
  /** posisi vertikal: tengah-atas (hook) | tengah | bawah (info/harga); atau angka y piksel */
  posisi?: 'atas' | 'tengah' | 'bawah' | number;
  warna?: string;
  outline?: string;
  /** kata/angka yang diberi warna sorot (mis. harga) */
  sorot?: string[];
  warnaSorot?: string;
  ukuran?: number;
}> = ({teks, mulai, sampai, posisi = 'atas', warna = '#FFFFFF', outline = '#000000', sorot = [], warnaSorot = '#FFC400', ukuran = 92}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  if (t < mulai || t > sampai) return null;
  const masuk = spring({frame: frame - mulai * fps, fps, config: {damping: 12, stiffness: 180}});
  const keluar = interpolate(t, [sampai - 0.15, sampai], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const y = typeof posisi === 'number' ? posisi : posisi === 'atas' ? AMAN.atas + 60 : posisi === 'tengah' ? 860 : AMAN.bawah - 260;
  const baris = teks.split('\n').slice(0, 2);
  const warnaKata = (w: string) => (sorot.some((s) => w.toLowerCase().includes(s.toLowerCase())) ? warnaSorot : warna);
  return (
    <div
      style={{
        position: 'absolute',
        left: AMAN.kiri,
        width: AMAN.kanan - AMAN.kiri,
        top: y,
        textAlign: 'center',
        fontFamily: FONT_JUDUL,
        fontSize: ukuran,
        lineHeight: 1.08,
        fontWeight: 900,
        textTransform: 'uppercase',
        WebkitTextStroke: `${Math.round(ukuran / 11)}px ${outline}`,
        paintOrder: 'stroke fill',
        textShadow: `0 6px 0 ${outline}`,
        opacity: keluar,
        transform: `scale(${0.7 + 0.3 * masuk}) translateY(${(1 - masuk) * 30}px)`,
      }}
    >
      {baris.map((b, i) => (
        <div key={i}>
          {b.split(' ').map((w, j) => (
            <span key={j} style={{color: warnaKata(w)}}>
              {w}{' '}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
};
