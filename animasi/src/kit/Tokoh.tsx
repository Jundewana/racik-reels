// Tokoh kartun flat (kepala bulat, badan kacang, garis tinta): berkedip, bernapas, mulut ikut ucapan, beberapa aksi.
// Dipakai untuk tukang (konstruksi), pembawa acara/podcast (dua tokoh bergantian bicara), pelanggan, dsb.
import React from 'react';
import {useData, useDetik} from './data';
import {goyang} from './gerak';
import {TINTA, WARNA, garisSvg, warna} from './tema';

const G = garisSvg(9);

export type Ekspresi = 'senang' | 'biasa' | 'kaget' | 'bingung' | 'sedih';
export type Aksi = 'diam' | 'palu' | 'lambai' | 'tunjuk' | 'jempol' | 'gestur';
export type Topi = 'none' | 'helmProyek' | 'peci' | 'rambut' | 'rambutPanjang';

/** Mulut terbuka (0..1) saat ada kata di rentang [dari, sampai] — dipakai untuk menggerakkan mulut tokoh yang bicara. */
const bukaMulut = (kata: {start: number; end: number}[], t: number, dari: number, sampai: number): number => {
  if (t < dari || t > sampai) return 0;
  const w = kata.find((k) => t >= k.start && t <= k.end);
  if (!w) return 0;
  const p = (t - w.start) / Math.max(0.08, w.end - w.start);
  return 0.35 + 0.65 * Math.abs(Math.sin(p * Math.PI * Math.max(1, Math.round((w.end - w.start) / 0.12))));
};

export const Tokoh: React.FC<{
  x: number;
  y: number; // y = kaki
  ukuran?: number; // tinggi tokoh (px)
  kulit?: string;
  baju?: string;
  celana?: string;
  topi?: Topi;
  warnaTopi?: string;
  ekspresi?: Ekspresi;
  aksi?: Aksi;
  /** Rentang detik tokoh ini berbicara (mulut ikut kata narasi). */
  bicara?: [number, number][];
  arah?: 1 | -1;
  fase?: number;
  /** Pose duduk (kaki menekuk ke depan); `bungkuk` = derajat badan condong ke depan (postur buruk). */
  duduk?: boolean;
  bungkuk?: number;
  /** Tanda nyeri (zigzag merah berdenyut) di punggung bawah. */
  nyeri?: boolean;
}> = ({
  x,
  y,
  ukuran = 700,
  kulit = WARNA.kulit,
  baju = 'hijau',
  celana = '#2B4C7E',
  topi = 'rambut',
  warnaTopi = 'kuning',
  ekspresi = 'senang',
  aksi = 'diam',
  bicara = [],
  arah = 1,
  fase = 0,
  duduk = false,
  bungkuk = 0,
  nyeri = false,
}) => {
  const data = useData();
  const t = useDetik();
  const napas = goyang(t, 6, 0.4, fase);
  const kedip = (t + fase) % 3.3 < 0.12;
  const mulut = Math.max(0, ...bicara.map(([a, b]) => bukaMulut(data.kata, t, a, b)));
  const sedangBicara = mulut > 0;
  // lengan kanan (sisi depan) per aksi
  let sudutKanan = 20;
  let sudutKiri = -15;
  if (aksi === 'palu') sudutKanan = -60 + Math.abs(goyang(t, 75, 1.8, fase));
  if (aksi === 'lambai') sudutKanan = -140 + goyang(t, 25, 1.5, fase);
  if (aksi === 'tunjuk') sudutKanan = -80;
  if (aksi === 'jempol') sudutKanan = -110;
  if (aksi === 'gestur' || sedangBicara) {
    sudutKanan = -40 + goyang(t, 25, 0.9, fase);
    sudutKiri = 35 + goyang(t, 15, 0.7, fase + 0.3);
  }
  const k = warna(kulit);
  const lengan = (sudut: number, sx: number, alat?: React.ReactNode) => (
    <g transform={`rotate(${sudut} ${sx} 330)`}>
      <path d={`M${sx} 330 L${sx} 470`} stroke={TINTA} strokeWidth={46} strokeLinecap="round" />
      <path d={`M${sx} 330 L${sx} 470`} stroke={warna(baju)} strokeWidth={30} strokeLinecap="round" />
      <circle cx={sx} cy={482} r={22} fill={k} {...G} strokeWidth={7} />
      {alat}
    </g>
  );
  const palu =
    aksi === 'palu' ? (
      <g transform="translate(300 482) rotate(90)">
        <rect x={-8} y={-10} width={16} height={110} rx={7} fill="#B07A45" {...G} strokeWidth={6} />
        <rect x={-40} y={95} width={80} height={34} rx={8} fill={WARNA.abu} {...G} strokeWidth={6} />
      </g>
    ) : aksi === 'jempol' ? (
      <path d="M300 460 L300 430" stroke={TINTA} strokeWidth={20} strokeLinecap="round" />
    ) : null;
  const mata = (cx: number) =>
    kedip ? (
      <path d={`M${cx - 14} 168 L${cx + 14} 168`} {...G} strokeWidth={7} />
    ) : ekspresi === 'kaget' ? (
      <circle cx={cx} cy={166} r={15} fill={WARNA.putih} {...G} strokeWidth={6} />
    ) : (
      <ellipse cx={cx} cy={166} rx={10} ry={13} fill={TINTA} />
    );
  const alis =
    ekspresi === 'bingung' ? (
      <path d="M180 128 L215 120 M255 112 L290 128" {...G} strokeWidth={7} />
    ) : ekspresi === 'sedih' ? (
      <path d="M180 120 L212 130 M258 130 L290 120" {...G} strokeWidth={7} />
    ) : null;
  let mulutSvg: React.ReactNode;
  if (sedangBicara) {
    mulutSvg = <ellipse cx={240} cy={218} rx={22} ry={6 + 18 * mulut} fill="#7A2230" {...G} strokeWidth={6} />;
  } else if (ekspresi === 'senang') {
    mulutSvg = <path d="M208 205 C222 232 258 232 272 205 Z" fill="#7A2230" {...G} strokeWidth={6} />;
  } else if (ekspresi === 'kaget') {
    mulutSvg = <ellipse cx={240} cy={222} rx={16} ry={20} fill="#7A2230" {...G} strokeWidth={6} />;
  } else if (ekspresi === 'sedih' || ekspresi === 'bingung') {
    mulutSvg = <path d="M212 228 C228 210 252 210 268 228" fill="none" {...G} strokeWidth={7} />;
  } else {
    mulutSvg = <path d="M215 218 L265 218" {...G} strokeWidth={7} />;
  }
  const kepala = (
    <g>
      {topi === 'rambutPanjang' ? <path d="M140 170 C130 80 180 50 240 50 C300 50 350 80 340 170 L345 300 L135 300 Z" fill={warna(warnaTopi)} {...G} /> : null}
      <circle cx={240} cy={170} r={100} fill={k} {...G} />
      {mata(205)}
      {mata(275)}
      {alis}
      <ellipse cx={190} cy={200} rx={16} ry={9} fill="#F08A7E" opacity={0.6} />
      <ellipse cx={290} cy={200} rx={16} ry={9} fill="#F08A7E" opacity={0.6} />
      {mulutSvg}
      {topi === 'helmProyek' ? (
        <>
          <path d="M138 140 C138 60 185 40 240 40 C295 40 342 60 342 140 Z" fill={warna(warnaTopi)} {...G} />
          <path d="M120 140 L360 140 L360 156 L120 156 Z" fill={warna(warnaTopi)} {...G} />
          <path d="M228 44 L228 120 M252 44 L252 120" {...G} strokeWidth={7} />
        </>
      ) : topi === 'peci' ? (
        <path d="M160 105 L165 60 C200 48 280 48 315 60 L320 105 Z" fill={warna(warnaTopi)} {...G} />
      ) : topi === 'rambut' || topi === 'rambutPanjang' ? (
        <path d="M142 150 C130 70 190 55 240 62 C300 55 352 85 338 150 C320 110 290 98 250 104 C215 92 170 108 142 150 Z" fill={warna(warnaTopi)} {...G} />
      ) : null}
    </g>
  );
  const s = ukuran / 900;
  return (
    <svg
      width={480 * s}
      height={900 * s}
      viewBox="0 0 480 900"
      style={{position: 'absolute', left: x - 240 * s, top: y - 900 * s, overflow: 'visible', transform: `scaleX(${arah})`}}
    >
      <ellipse cx={240} cy={892} rx={150} ry={14} fill={TINTA} opacity={0.18} />
      {/* kaki */}
      {duduk ? (
        <>
          <path d="M220 650 L420 660 L430 870" fill="none" stroke={TINTA} strokeWidth={58} strokeLinecap="round" strokeLinejoin="round" />
          <path d="M220 650 L420 660 L430 870" fill="none" stroke={warna(celana)} strokeWidth={40} strokeLinecap="round" strokeLinejoin="round" />
          <path d="M420 878 L480 878" stroke={TINTA} strokeWidth={30} strokeLinecap="round" />
        </>
      ) : (
        <>
          <path d="M200 640 L195 870 M280 640 L285 870" stroke={TINTA} strokeWidth={58} strokeLinecap="round" />
          <path d="M200 640 L195 870 M280 640 L285 870" stroke={warna(celana)} strokeWidth={40} strokeLinecap="round" />
          <path d="M160 878 L220 878 M260 878 L320 878" stroke={TINTA} strokeWidth={30} strokeLinecap="round" />
        </>
      )}
      <g transform={`translate(0 ${napas * 0.6}) rotate(${bungkuk} 240 660)`}>
        {lengan(sudutKiri, 150)}
        {/* badan */}
        <path d="M150 330 C150 285 190 270 240 270 C290 270 330 285 330 330 L340 660 C340 680 320 690 300 690 L180 690 C160 690 140 680 140 660 Z" fill={warna(baju)} {...G} />
        <path d="M215 275 L240 320 L265 275" fill="none" {...G} strokeWidth={7} />
        <g transform={`translate(0 ${napas * 0.4}) rotate(${goyang(t, 2, 0.5, fase)} 240 260)`}>{kepala}</g>
        {lengan(sudutKanan, 330, palu)}
        {nyeri ? (
          <g opacity={0.55 + 0.45 * Math.abs(goyang(t, 1, 1.6))}>
            <path d="M118 560 L88 585 L118 605 L84 632 L116 652" fill="none" stroke={WARNA.merah} strokeWidth={14} strokeLinecap="round" strokeLinejoin="round" />
            <path d="M70 540 L40 520 M66 670 L36 690" stroke={WARNA.merah} strokeWidth={10} strokeLinecap="round" />
          </g>
        ) : null}
      </g>
    </svg>
  );
};
