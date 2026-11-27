// Stiker: kotak bergaris tinta + bayangan keras, muncul memantul, bergoyang pelan. Wadah ikon/teks/kartu fitur.
import React from 'react';
import {useDetik} from './data';
import {goyang, keluar, pop} from './gerak';
import {Ikon, NamaIkon} from './Ikon';
import {FONT_JUDUL, GAYA, TINTA, bayang, sudut, tepi, warna} from './tema';

export const Stiker: React.FC<{
  x: number;
  y: number;
  mulai: number;
  sampai?: number;
  warna?: string;
  miring?: number;
  lebar?: number;
  tinggi?: number;
  bulat?: number;
  padding?: number;
  dariArah?: 'bawah' | 'kiri' | 'kanan' | 'atas' | 'tengah';
  children: React.ReactNode;
}> = ({x, y, mulai, sampai, warna: w = 'putih', miring = 0, lebar, tinggi, bulat = 36, padding = 28, dariArah = 'tengah', children}) => {
  const t = useDetik();
  const p = pop(t, mulai);
  const h = sampai !== undefined ? keluar(t, sampai, 0.2) : 1;
  if (p <= 0 || h <= 0) return null;
  const jarak = 500 * (1 - p);
  const [dx, dy] = {
    tengah: [0, 0],
    bawah: [0, jarak],
    atas: [0, -jarak],
    kiri: [-jarak, 0],
    kanan: [jarak, 0],
  }[dariArah];
  const skala = dariArah === 'tengah' ? p : Math.min(1, 0.6 + p * 0.4);
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: lebar,
        height: tinggi,
        transform: `translate(-50%, -50%) translate(${dx}px, ${dy}px) scale(${skala * h}) rotate(${miring + goyang(t, 1.2, 0.5, x * 0.01)}deg)`,
        background: warna(w),
        border: tepi(7),
        borderRadius: sudut(bulat),
        boxShadow: bayang(14),
        padding,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 24,
        boxSizing: 'border-box',
      }}
    >
      {children}
    </div>
  );
};

/** Kartu fitur: ikon + teks dalam stiker (mis. "✓ Mesin terawat"). */
export const KartuFitur: React.FC<{
  ikon: NamaIkon;
  teks: string;
  x?: number;
  y: number;
  mulai: number;
  sampai?: number;
  warna?: string;
  warnaIkon?: string;
  warnaTeks?: string;
  lebar?: number;
  miring?: number;
  dariArah?: 'bawah' | 'kiri' | 'kanan' | 'atas' | 'tengah';
  ukuranTeks?: number;
}> = ({ikon, teks, x = 540, y, mulai, sampai, warna: w = 'putih', warnaIkon = 'hijau', warnaTeks = 'tinta', lebar = 820, miring = 0, dariArah = 'kanan', ukuranTeks = 64}) => (
  <Stiker x={x} y={y} mulai={mulai} sampai={sampai} warna={w} lebar={lebar} miring={miring} dariArah={dariArah} padding={22}>
    <Ikon nama={ikon} ukuran={120} warna={warnaIkon} mulai={mulai} />
    <div
      style={{
        flex: 1,
        fontFamily: FONT_JUDUL,
        fontWeight: 800,
        fontSize: ukuranTeks,
        lineHeight: 1.05,
        color: warna(warnaTeks),
        textTransform: 'uppercase',
      }}
    >
      {teks}
    </div>
  </Stiker>
);

/** Cap/stempel miring (mis. "GRATIS!") — muncul menghentak dari besar ke ukuran normal. */
export const Cap: React.FC<{teks: string; x: number; y: number; mulai: number; sampai?: number; warna?: string; ukuran?: number; miring?: number}> = ({
  teks,
  x,
  y,
  mulai,
  sampai,
  warna: w = 'merah',
  ukuran = 120,
  miring = -12,
}) => {
  const t = useDetik();
  if (t < mulai) return null;
  const h = sampai !== undefined ? keluar(t, sampai, 0.2) : 1;
  if (h <= 0) return null;
  const p = pop(t, mulai, 300, 14);
  const s = 2.4 - 1.4 * p;
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        transform: `translate(-50%, -50%) scale(${s * h}) rotate(${miring}deg)`,
        opacity: Math.min(1, p * 2) * h,
        fontFamily: FONT_JUDUL,
        fontWeight: 800,
        fontSize: ukuran,
        color: '#fff',
        background: warna(w),
        padding: `${ukuran * 0.08}px ${ukuran * 0.3}px`,
        border: tepi(9),
        borderRadius: sudut(24),
        boxShadow: bayang(14),
        WebkitTextStroke: GAYA.teks === 'garis' ? `${Math.round(ukuran * 0.09)}px ${TINTA}` : undefined,
        paintOrder: 'stroke fill',
        whiteSpace: 'nowrap',
        textTransform: 'uppercase',
      }}
    >
      {teks}
    </div>
  );
};
