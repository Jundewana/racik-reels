// Rumah flat yang dibangun bertahap: fondasi → dinding naik → jendela → atap jatuh → pintu (+ kilau selesai).
// `mulai`/`durasi` mengatur pembangunan; `rusak` = versi miring & retak (untuk adegan masalah).
import React, {useId} from 'react';
import {useDetik} from './data';
import {getar, masuk, pop} from './gerak';
import {TINTA, WARNA, garisSvg, warna} from './tema';

const G = garisSvg(9);

export const Rumah: React.FC<{
  x: number;
  y: number; // y = tanah
  ukuran?: number;
  mulai?: number;
  durasi?: number;
  warnaDinding?: string;
  warnaAtap?: string;
  rusak?: boolean;
}> = ({x, y, ukuran = 600, mulai = 0, durasi = 1.6, warnaDinding = 'krem', warnaAtap = 'merah', rusak = false}) => {
  const t = useDetik();
  const klip = `dinding-${useId().replace(/:/g, '')}`;
  const tahap = (a: number, b: number) => masuk(t, mulai + durasi * a, durasi * (b - a));
  const fondasi = tahap(0, 0.15);
  const dinding = tahap(0.12, 0.5);
  const jendela = pop(t, mulai + durasi * 0.5, 260, 12);
  const atapP = tahap(0.55, 0.8);
  const atapY = (1 - atapP) * -700;
  const hentak = getar(t, mulai + durasi * 0.8, 10, 0.3);
  const pintu = pop(t, mulai + durasi * 0.85, 260, 12);
  const selesai = pop(t, mulai + durasi, 200, 10);
  if (t < mulai) return null;
  const s = ukuran / 600;
  const miring = rusak ? -6 + getar(t, mulai + durasi, 3, 2) : 0;
  return (
    <svg
      width={ukuran}
      height={ukuran}
      viewBox="0 -60 600 600"
      style={{position: 'absolute', left: x - ukuran / 2, top: y - ukuran * (520 / 600), overflow: 'visible', transform: `translateY(${hentak * s}px)`}}
    >
      <ellipse cx={300} cy={468} rx={280 * fondasi} ry={18} fill={TINTA} opacity={0.18} />
      {/* fondasi */}
      <rect x={300 - 250 * fondasi} y={440} width={500 * fondasi} height={28} rx={6} fill={WARNA.abu} {...G} />
      <g transform={`rotate(${miring} 300 440)`}>
        {/* dinding naik dari bawah */}
        <g>
          <clipPath id={klip}>
            <rect x={60} y={440 - 260 * dinding} width={480} height={260 * dinding + 2} />
          </clipPath>
          <g clipPath={`url(#${klip})`}>
            <rect x={90} y={180} width={420} height={260} fill={warna(warnaDinding)} {...G} />
            {[220, 270, 320, 370, 420].map((yy) => (
              <path key={yy} d={`M95 ${yy} L505 ${yy}`} stroke={TINTA} strokeOpacity={0.12} strokeWidth={5} />
            ))}
          </g>
        </g>
        {/* jendela */}
        {[150, 380].map((wx) => (
          <g key={wx} transform={`translate(${wx + 35} 280) scale(${jendela}) translate(${-wx - 35} -280)`}>
            <rect x={wx} y={245} width={70} height={70} rx={8} fill={WARNA.langit} {...G} />
            <path d={`M${wx + 35} 245 L${wx + 35} 315 M${wx} 280 L${wx + 70} 280`} {...G} strokeWidth={6} />
          </g>
        ))}
        {/* pintu */}
        <g transform={`translate(300 440) scale(1 ${pintu}) translate(-300 -440)`}>
          <rect x={262} y={320} width={76} height={120} rx={10} fill={WARNA.kuning} {...G} />
          <circle cx={322} cy={385} r={7} fill={TINTA} />
        </g>
        {/* atap jatuh */}
        <g transform={`translate(0 ${atapY})`} opacity={atapP > 0 ? 1 : 0}>
          <path d="M50 195 L300 40 L550 195 Z" fill={warna(warnaAtap)} {...G} />
          <rect x={395} y={70} width={50} height={80} fill={WARNA.abu} {...G} />
          {rusak ? null : <path d="M115 180 L300 66 L485 180" fill="none" stroke={WARNA.putih} strokeWidth={8} strokeOpacity={0.5} strokeLinecap="round" />}
        </g>
        {/* retak */}
        {rusak && dinding > 0.9 ? (
          <>
            <path d="M200 190 L220 240 L205 270 L235 330" fill="none" {...G} strokeWidth={7} />
            <path d="M470 330 L450 370 L475 400" fill="none" {...G} strokeWidth={7} />
          </>
        ) : null}
      </g>
      {/* kilau selesai */}
      {!rusak && selesai > 0
        ? [
            [80, 80],
            [540, 120],
            [560, 330],
          ].map(([kx, ky], i) => (
            <path
              key={i}
              transform={`translate(${kx} ${ky}) scale(${selesai * 0.5})`}
              d="M0 -60 C6 -15 15 -6 60 0 C15 6 6 15 0 60 C-6 15 -15 6 -60 0 C-15 -6 -6 -15 0 -60 Z"
              fill={WARNA.kuning}
              {...G}
              strokeWidth={8}
            />
          ))
        : null}
    </svg>
  );
};
