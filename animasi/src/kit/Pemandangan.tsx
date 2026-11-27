// Pemandangan flat bergaya pegunungan (langit, matahari, awan, gunung berlapis, pohon, jalan) dengan parallax.
// `laju` = kecepatan gulir (px/dtk pada lapisan depan); 0 = diam.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useDetik} from './data';
import {WARNA, garisSvg, GAYA} from './tema';

const G = garisSvg(8);

/** Lapisan yang diulang 2× selebar 1080 agar bisa digulir tanpa sambungan. */
const Gulir: React.FC<{geser: number; children: React.ReactNode; tinggi?: number}> = ({geser, children}) => {
  const x = -(((geser % 1078) + 1078) % 1078); // periode = jarak ubin (tumpang 2 px)
  return (
    <div style={{position: 'absolute', inset: 0, transform: `translateX(${x}px)`}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 1920}}>{children}</div>
      <div style={{position: 'absolute', left: 1078, top: 0, width: 1080, height: 1920}}>{children}</div>
    </div>
  );
};

/** Lapisan tanah: `atas` = path garis atas dari x=-20 sampai x=1100. Isi tanpa garis tepi, outline hanya di atas. */
const Lapis: React.FC<{atas: string; isi: string}> = ({atas, isi}) => (
  <>
    <path d={`${atas} L1100 1940 L-20 1940 Z`} fill={isi} />
    <path d={atas} fill="none" {...G} />
  </>
);

const Pohon: React.FC<{x: number; y: number; s?: number; w?: string}> = ({x, y, s = 1, w = WARNA.hijau}) => (
  <g transform={`translate(${x} ${y}) scale(${s})`}>
    <rect x={-9} y={-10} width={18} height={60} rx={6} fill="#7A4A2A" {...G} strokeWidth={6} />
    <circle cx={0} cy={-45} r={48} fill={w} {...G} strokeWidth={7} />
  </g>
);

export const Pemandangan: React.FC<{
  laju?: number;
  senja?: boolean;
  jalan?: boolean;
  yJalan?: number;
}> = ({laju = 0, senja = false, jalan = true, yJalan = 1330}) => {
  const t = useDetik();
  const g = t * laju;
  const malam = GAYA.id === 'neon-malam';
  const langitAtas = senja && !malam ? '#FF9E6B' : GAYA.langit[0];
  const langitBawah = senja && !malam ? '#FFD9A0' : GAYA.langit[1];
  return (
    <AbsoluteFill style={{background: `linear-gradient(${langitAtas}, ${langitBawah} 60%)`}}>
      {/* matahari */}
      <svg width={1080} height={1920} style={{position: 'absolute'}}>
        <g transform={`translate(800 470) rotate(${t * 20})`}>
          {Array.from({length: 12}, (_, i) => (
            <rect key={i} x={-10} y={-190} width={20} height={55} rx={10} fill={WARNA.kuning} transform={`rotate(${i * 30})`} />
          ))}
        </g>
        <circle cx={800} cy={470} r={110} fill={WARNA.kuning} {...G} />
      </svg>
      {/* awan */}
      <Gulir geser={g * 0.08 + t * 25}>
        <svg width={1080} height={1920}>
          {[
            [160, 380, 1],
            [620, 300, 0.8],
            [900, 640, 0.7],
          ].map(([x, y, s], i) => (
            <path
              key={i}
              transform={`translate(${x} ${y}) scale(${s})`}
              d="M-120 40 C-150 40 -150 -5 -110 -8 C-105 -55 -35 -60 -20 -25 C0 -70 85 -60 85 -10 C125 -12 130 40 95 40 Z"
              fill={WARNA.putih}
              {...G}
            />
          ))}
        </svg>
      </Gulir>
      {/* gunung jauh */}
      <Gulir geser={g * 0.15}>
        <svg width={1080} height={1920}>
          <Lapis atas="M-20 980 L160 760 L260 840 L420 600 L560 820 L700 700 L880 900 L1000 780 L1100 980" isi={WARNA.unguMuda} />
          <path d="M420 600 L380 655 L420 640 L455 668 L470 650 Z" fill={WARNA.putih} {...G} strokeWidth={6} />
        </svg>
      </Gulir>
      {/* bukit tengah */}
      <Gulir geser={g * 0.35}>
        <svg width={1080} height={1920}>
          <Lapis atas="M-20 1070 C150 960 300 980 420 1040 C560 1110 700 960 860 990 C960 1010 1030 1050 1100 1070" isi={WARNA.hijauMuda} />
          {[120, 340, 610, 820, 990].map((x, i) => (
            <Pohon key={i} x={x} y={1070 - ((i * 37) % 60)} s={0.7} w={WARNA.hijau} />
          ))}
        </svg>
      </Gulir>
      {/* bukit depan + jalan */}
      <Gulir geser={g}>
        <svg width={1080} height={1920}>
          <Lapis atas="M-20 1200 C200 1150 380 1190 540 1220 C700 1250 880 1170 1100 1200" isi={WARNA.hijau} />
          {[80, 470, 760].map((x, i) => (
            <Pohon key={i} x={x} y={1215 + (i % 2) * 20} s={1.05} w={WARNA.hijauMuda} />
          ))}
          {jalan ? (
            <>
              <Lapis atas={`M-20 ${yJalan - 70} L1100 ${yJalan - 70}`} isi={WARNA.abu} />
              {[0, 270, 540, 810].map((x) => (
                <rect key={x} x={x + 40} y={yJalan + 5} width={150} height={16} rx={8} fill={WARNA.kuning} />
              ))}
            </>
          ) : null}
          {/* tanah depan: rumput gelap + semak & bunga (mengisi area bawah) */}
          <Lapis atas={`M-20 ${yJalan + 100} L1100 ${yJalan + 100}`} isi="#007A33" />
          {[60, 330, 600, 880].map((x, i) => (
            <g key={x} transform={`translate(${x} ${yJalan + 210 + (i % 2) * 70})`}>
              <path d="M-70 30 C-80 -20 -30 -40 0 -15 C30 -45 85 -20 70 30 Z" fill={WARNA.hijauMuda} {...G} strokeWidth={6} />
              <circle cx={-20} cy={-8} r={11} fill={i % 2 ? WARNA.kuning : WARNA.merah} {...G} strokeWidth={5} />
              <circle cx={28} cy={2} r={9} fill={WARNA.putih} {...G} strokeWidth={5} />
            </g>
          ))}
        </svg>
      </Gulir>
    </AbsoluteFill>
  );
};
