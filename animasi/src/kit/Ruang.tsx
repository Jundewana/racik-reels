// Properti ruangan & diagram: meja kerja + monitor + kursi (tampak samping), dan diagram panggul (postur).
import React from 'react';
import {useDetik} from './data';
import {goyang, masuk, pop} from './gerak';
import {FONT_JUDUL, TINTA, WARNA, garisSvg, warna} from './tema';

const G = garisSvg(9);

/** Kursi kerja tampak samping (sandaran di kiri). x,y = titik tengah dudukan di lantai. */
export const Kursi: React.FC<{x: number; y: number; skala?: number; warna?: string}> = ({x, y, skala = 1, warna: w = 'ungu'}) => (
  <svg width={360 * skala} height={620 * skala} viewBox="0 0 360 620" style={{position: 'absolute', left: x - 180 * skala, top: y - 620 * skala, overflow: 'visible'}}>
    <path d="M60 40 C40 40 30 60 32 90 L52 360 L100 360 L92 80 C92 55 80 40 60 40 Z" fill={warna(w)} {...G} />
    <rect x={40} y={340} width={280} height={52} rx={22} fill={warna(w)} {...G} />
    <path d="M180 392 L180 520" {...G} strokeWidth={22} />
    <path d="M60 560 L300 560 M180 520 L180 560" {...G} strokeWidth={16} />
    <circle cx={70} cy={590} r={22} fill={TINTA} />
    <circle cx={290} cy={590} r={22} fill={TINTA} />
  </svg>
);

/** Meja + monitor menyala (layar menghadap kiri, ke tokoh). x,y = kaki meja kanan di lantai. */
export const MejaMonitor: React.FC<{x: number; y: number; skala?: number}> = ({x, y, skala = 1}) => {
  const t = useDetik();
  const kedip = 0.55 + 0.25 * Math.abs(goyang(t, 1, 0.8));
  return (
    <svg width={420 * skala} height={760 * skala} viewBox="0 0 420 760" style={{position: 'absolute', left: x - 420 * skala, top: y - 760 * skala, overflow: 'visible'}}>
      {/* cahaya layar */}
      <path d="M150 120 L-120 40 L-120 420 L150 330 Z" fill={WARNA.langit} opacity={kedip * 0.35} />
      {/* monitor */}
      <path d="M150 100 L190 90 L190 350 L150 340 Z" fill={WARNA.abu} {...G} />
      <rect x={150} y={100} width={14} height={240} fill={WARNA.langit} />
      <path d="M190 220 L250 230 L250 420" fill="none" {...G} strokeWidth={18} />
      <path d="M210 420 L300 420" {...G} strokeWidth={16} />
      {/* meja */}
      <rect x={20} y={430} width={400} height={40} rx={10} fill="#B07A45" {...G} />
      <path d="M60 470 L60 750 M380 470 L380 750" {...G} strokeWidth={22} />
      {/* keyboard & gelas */}
      <rect x={40} y={410} width={110} height={20} rx={6} fill={WARNA.abu} {...G} strokeWidth={6} />
      <rect x={300} y={360} width={46} height={70} rx={8} fill={WARNA.merah} {...G} strokeWidth={7} />
    </svg>
  );
};

/**
 * Diagram postur tampak samping: tulang belakang + panggul. Panggul miring ke depan (anterior tilt) dari `mulaiMiring`
 * selama `durasi`; panah merah menunjukkan arah. `label` muncul di `mulaiLabel`.
 */
export const DiagramPanggul: React.FC<{
  x: number;
  y: number;
  ukuran?: number;
  mulai: number;
  mulaiMiring: number;
  durasi?: number;
  sudut?: number;
  label?: string;
  mulaiLabel?: number;
}> = ({x, y, ukuran = 640, mulai, mulaiMiring, durasi = 1.2, sudut = 22, label, mulaiLabel}) => {
  const t = useDetik();
  const p = pop(t, mulai, 160, 13);
  if (p <= 0) return null;
  const m = masuk(t, mulaiMiring, durasi) * sudut;
  const tulang = '#FFF8E8';
  const lbl = label && mulaiLabel !== undefined ? pop(t, mulaiLabel, 240, 12) : 0;
  return (
    <svg width={ukuran} height={ukuran * 1.3} viewBox="0 0 500 650" style={{position: 'absolute', left: x - ukuran / 2, top: y - ukuran * 0.65, overflow: 'visible', transform: `scale(${p})`}}>
      {/* siluet badan */}
      <path d="M170 30 C120 30 110 90 130 130 L150 180 C110 240 120 330 150 380 C130 440 140 520 160 640 L340 640 C350 520 360 440 330 380 C370 300 370 220 330 170 L340 120 C360 70 320 30 270 30 Z" fill={WARNA.krem} {...G} opacity={0.9} />
      {/* tulang belakang (kurva lumbar makin melengkung saat panggul miring) */}
      <path
        d={`M250 60 C${236 - m * 0.3} 150 ${268 + m * 0.6} 230 ${250 - m * 0.2} 300 C${226 - m * 1.4} 340 ${232 - m * 1.6} 370 ${262 - m * 0.4} 400`}
        fill="none"
        stroke={TINTA}
        strokeWidth={34}
        strokeLinecap="round"
      />
      <path
        d={`M250 60 C${236 - m * 0.3} 150 ${268 + m * 0.6} 230 ${250 - m * 0.2} 300 C${226 - m * 1.4} 340 ${232 - m * 1.6} 370 ${262 - m * 0.4} 400`}
        fill="none"
        stroke={tulang}
        strokeWidth={20}
        strokeLinecap="round"
        strokeDasharray="22 8"
      />
      {/* panggul: mangkuk yang berotasi ke depan (kanan = depan) */}
      <g transform={`rotate(${m} 255 440)`}>
        <path d="M170 400 C160 470 200 520 255 520 C310 520 350 470 340 400 C300 430 210 430 170 400 Z" fill={tulang} {...G} />
        <path d="M195 420 C230 445 280 445 315 420" fill="none" {...G} strokeWidth={6} opacity={0.5} />
        <circle cx={255} cy={500} r={18} fill={WARNA.merah} opacity={m > 2 ? 0.8 : 0} />
      </g>
      {/* tulang paha */}
      <path d="M230 520 L215 640 M290 520 L300 640" stroke={TINTA} strokeWidth={34} strokeLinecap="round" />
      <path d="M230 520 L215 640 M290 520 L300 640" stroke={tulang} strokeWidth={20} strokeLinecap="round" />
      {/* panah arah miring */}
      {m > 1 ? (
        <g opacity={Math.min(1, m / 8)}>
          <path d="M390 380 C430 430 430 480 395 525" fill="none" stroke={WARNA.merah} strokeWidth={16} strokeLinecap="round" />
          <path d="M375 505 L398 532 L420 500" fill="none" stroke={WARNA.merah} strokeWidth={16} strokeLinecap="round" strokeLinejoin="round" />
        </g>
      ) : null}
      {lbl > 0 ? (
        <g transform={`translate(250 600) scale(${lbl})`}>
          <rect x={-230} y={-40} width={460} height={80} rx={20} fill={warna('merah')} {...G} />
          <text x={0} y={16} textAnchor="middle" fontFamily={FONT_JUDUL} fontWeight={800} fontSize={44} fill={WARNA.putih}>
            {label}
          </text>
        </g>
      ) : null}
    </svg>
  );
};
