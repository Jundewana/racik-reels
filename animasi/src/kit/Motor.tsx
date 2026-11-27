// Motor matic flat (tampak samping, menghadap kanan) + pengendara opsional. Digambar sendiri (SVG), bukan merek tertentu.
import React from 'react';
import {useDetik} from './data';
import {goyang} from './gerak';
import {TINTA, WARNA, garisSvg, warna} from './tema';

const G = garisSvg(9);

const Roda: React.FC<{cx: number; cy: number; sudut: number}> = ({cx, cy, sudut}) => (
  <g>
    <circle cx={cx} cy={cy} r={64} fill={TINTA} />
    <circle cx={cx} cy={cy} r={38} fill="#D8D8DE" {...G} strokeWidth={7} />
    <g transform={`rotate(${sudut} ${cx} ${cy})`}>
      {[0, 60, 120].map((a) => (
        <line key={a} x1={cx} y1={cy - 34} x2={cx} y2={cy + 34} stroke={TINTA} strokeWidth={8} strokeLinecap="round" transform={`rotate(${a} ${cx} ${cy})`} />
      ))}
    </g>
    <circle cx={cx} cy={cy} r={11} fill={WARNA.kuning} {...G} strokeWidth={6} />
  </g>
);

const Pengendara: React.FC<{helm: string; baju: string; t: number; senyum: boolean}> = ({helm, baju, t, senyum}) => {
  const ayun = goyang(t, 3, 2.2);
  return (
    <g transform={`translate(0 ${ayun * 0.5})`}>
      {/* kaki */}
      <path d="M205 160 L300 178 L318 250" fill="none" stroke="#2B4C7E" strokeWidth={36} strokeLinecap="round" strokeLinejoin="round" />
      <path d="M300 252 L345 252" stroke={TINTA} strokeWidth={22} strokeLinecap="round" />
      {/* badan */}
      <path d="M170 170 C160 120 175 50 215 40 C250 32 270 60 268 100 L262 172 Z" fill={warna(baju)} {...G} />
      {/* lengan ke setang */}
      <path d="M240 70 L330 95 L372 86" fill="none" stroke={TINTA} strokeWidth={40} strokeLinecap="round" strokeLinejoin="round" />
      <path d="M240 70 L330 95 L372 86" fill="none" stroke={warna(baju)} strokeWidth={24} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={376} cy={86} r={15} fill={WARNA.kulit} {...G} strokeWidth={6} />
      {/* kepala + helm */}
      <g transform={`rotate(${ayun} 225 -10)`}>
        <circle cx={232} cy={-8} r={50} fill={WARNA.kulit} {...G} />
        <path d="M176 -2 C170 -62 220 -82 252 -72 C285 -62 296 -30 290 -8 L240 -8 L236 -30 L182 -26 Z" fill={warna(helm)} {...G} />
        <circle cx={262} cy={-4} r={7} fill={TINTA} />
        {senyum ? <path d="M250 18 C258 28 272 28 280 16" fill="none" {...G} strokeWidth={6} /> : <path d="M255 22 L278 20" {...G} strokeWidth={6} />}
      </g>
    </g>
  );
};

/**
 * Motor di posisi x,y (pusat bawah roda), lebar `ukuran` px. `laju` = putaran roda (0 diam).
 * `arah` -1 = menghadap kiri. `pengendara` = tampilkan pengendara berhelm.
 */
export const Motor: React.FC<{
  x: number;
  y: number;
  ukuran?: number;
  warna?: string;
  laju?: number;
  arah?: 1 | -1;
  pengendara?: boolean;
  warnaHelm?: string;
  warnaBaju?: string;
  senyum?: boolean;
  miring?: number;
}> = ({x, y, ukuran = 600, warna: w = 'merah', laju = 0, arah = 1, pengendara = false, warnaHelm = 'kuning', warnaBaju = 'hijau', senyum = true, miring = 0}) => {
  const t = useDetik();
  const sudut = t * laju * 360;
  const bob = laju ? Math.abs(goyang(t, 5, laju * 1.5)) : 0;
  const badan = warna(w);
  return (
    <svg
      width={ukuran}
      height={ukuran * (500 / 600)}
      viewBox="0 -120 600 500"
      style={{
        position: 'absolute',
        left: x - ukuran / 2,
        top: y - ukuran * (500 / 600) * 0.988, // y = titik roda menyentuh tanah
        overflow: 'visible',
        transform: `scaleX(${arah}) rotate(${miring}deg)`,
        transformOrigin: `${ukuran / 2}px ${ukuran * (500 / 600) * 0.988}px`,
      }}
    >
      {/* bayangan tanah */}
      <ellipse cx={305} cy={378} rx={250 - bob * 4} ry={16} fill={TINTA} opacity={0.18} />
      <g transform={`translate(0 ${-bob})`}>
        <Roda cx={140} cy={310} sudut={sudut} />
        <Roda cx={470} cy={310} sudut={sudut} />
        {/* garpu depan */}
        <line x1={420} y1={135} x2={470} y2={310} stroke={TINTA} strokeWidth={20} strokeLinecap="round" />
        <line x1={420} y1={135} x2={470} y2={310} stroke="#9A9AA4" strokeWidth={8} strokeLinecap="round" />
        {/* badan belakang */}
        <path d="M60 262 C48 205 92 168 168 162 L322 160 C350 160 356 196 342 222 L318 266 Z" fill={badan} {...G} />
        <path d="M95 222 C130 210 220 208 300 214" fill="none" stroke={WARNA.putih} strokeWidth={10} strokeLinecap="round" opacity={0.75} />
        {/* dek kaki */}
        <rect x={205} y={246} width={190} height={32} rx={14} fill={WARNA.abu} {...G} />
        {/* pelindung kaki depan */}
        <path d="M330 268 C352 205 372 150 402 104 L446 112 C436 172 424 222 410 270 Z" fill={badan} {...G} />
        {/* spakbor depan */}
        <path d="M398 292 C404 232 536 232 542 292 L524 292 C516 256 428 256 418 292 Z" fill={badan} {...G} />
        {/* jok */}
        <path d="M112 162 C110 132 150 122 200 124 L304 128 C326 130 328 160 304 164 Z" fill="#2A2A30" {...G} />
        {/* lampu belakang */}
        <rect x={52} y={205} width={26} height={22} rx={6} fill={WARNA.merah} {...G} strokeWidth={6} />
        {/* setang & spion */}
        <path d="M404 104 L388 74" {...G} strokeWidth={16} />
        <path d="M362 72 L404 72" {...G} strokeWidth={20} />
        <path d="M392 72 L410 36" {...G} strokeWidth={7} />
        <ellipse cx={414} cy={30} rx={16} ry={11} fill={WARNA.langit} {...G} strokeWidth={6} />
        {/* lampu depan */}
        <ellipse cx={430} cy={128} rx={18} ry={14} fill={WARNA.kuning} {...G} strokeWidth={7} />
        {pengendara ? <Pengendara helm={warnaHelm} baju={warnaBaju} t={t} senyum={senyum} /> : null}
      </g>
    </svg>
  );
};

/** Skala koordinat bantu: tinggi tampilan motor untuk lebar tertentu. */
export const tinggiMotor = (ukuran: number) => ukuran * (500 / 600);
