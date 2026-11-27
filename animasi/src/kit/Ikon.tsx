// Ikon flat bergaris tinta (SVG 200×200, digambar sendiri). Beberapa punya gerak kecil sendiri (jam, kilat, kilau).
import React from 'react';
import {useDetik} from './data';
import {goyang, pop} from './gerak';
import {TINTA, WARNA, garisSvg, warnaObjek} from './tema';

export type NamaIkon =
  | 'helm'
  | 'jasHujan'
  | 'jam'
  | 'tagHarga'
  | 'kilat'
  | 'kalender'
  | 'kereta'
  | 'rumah'
  | 'chat'
  | 'cek'
  | 'kunci'
  | 'kilau'
  | 'pusing'
  | 'pin'
  | 'tanya'
  | 'tangan'
  | 'palu'
  | 'kanopi'
  | 'molen'
  | 'helmProyek'
  | 'bata'
  | 'dokumen'
  | 'perisai'
  | 'penggaris'
  | 'mikrofon'
  | 'lampu';

const G = garisSvg(10);

const gambar = (nama: NamaIkon, w: string, t: number): React.ReactNode => {
  switch (nama) {
    case 'helm':
      return (
        <>
          <path d="M30 130 C30 60 80 30 115 30 C160 30 180 70 180 115 L180 140 L30 140 Z" fill={w} {...G} />
          <path d="M95 75 L175 75 L175 120 L110 120 C98 120 92 110 95 98 Z" fill={WARNA.langit} {...G} />
          <path d="M40 140 L190 140" {...G} />
          <circle cx="60" cy="100" r="9" fill={TINTA} />
        </>
      );
    case 'jasHujan':
      return (
        <>
          <path d="M70 40 L130 40 L160 70 L175 170 L25 170 L40 70 Z" fill={w} {...G} />
          <path d="M70 40 C75 70 125 70 130 40" fill={WARNA.kuning} {...G} />
          <path d="M100 75 L100 165" {...G} />
          {[0, 1, 2].map((i) => {
            const y = ((t * 160 + i * 55) % 120) - 20;
            return <path key={i} d={`M${20 + i * 80} ${y} l-6 18`} {...G} stroke={WARNA.langit} strokeWidth={9} />;
          })}
        </>
      );
    case 'jam': {
      const a = t * 720;
      return (
        <>
          <circle cx="100" cy="105" r="78" fill={WARNA.putih} {...G} />
          <circle cx="100" cy="105" r="78" fill="none" stroke={w} strokeWidth={14} />
          <circle cx="100" cy="105" r="62" fill="none" {...G} strokeWidth={0} />
          <line x1="100" y1="105" x2="100" y2="58" {...G} transform={`rotate(${a / 12} 100 105)`} />
          <line x1="100" y1="105" x2="100" y2="45" {...G} strokeWidth={7} stroke={WARNA.merah} transform={`rotate(${a} 100 105)`} />
          <circle cx="100" cy="105" r="9" fill={TINTA} />
          <path d="M60 22 L80 32 M140 22 L120 32" {...G} />
        </>
      );
    }
    case 'tagHarga':
      return (
        <>
          <path d="M20 95 L95 20 L180 20 L180 105 L105 180 Z" fill={w} {...G} />
          <circle cx="148" cy="52" r="13" fill={WARNA.krem} {...G} />
          <text x="98" y="128" fontSize="62" fontWeight={800} textAnchor="middle" fill={WARNA.putih} stroke={TINTA} strokeWidth={6} paintOrder="stroke" transform="rotate(-45 98 110)">
            Rp
          </text>
        </>
      );
    case 'kilat':
      return (
        <g transform={`scale(${1 + 0.06 * Math.max(0, goyang(t, 1, 3))}) `} style={{transformOrigin: '100px 100px'}}>
          <path d="M115 15 L45 115 L95 115 L80 185 L155 80 L105 80 Z" fill={w} {...G} />
        </g>
      );
    case 'kalender':
      return (
        <>
          <rect x="25" y="40" width="150" height="140" rx="18" fill={WARNA.putih} {...G} />
          <path d="M25 58 C25 48 33 40 43 40 L157 40 C167 40 175 48 175 58 L175 85 L25 85 Z" fill={w} {...G} />
          <path d="M65 22 L65 55 M135 22 L135 55" {...G} />
          {[0, 1, 2].map((r) =>
            [0, 1, 2, 3].map((c) => (
              <rect key={`${r}${c}`} x={45 + c * 30} y={100 + r * 25} width="18" height="14" rx="3" fill={(r * 4 + c) % 5 === 2 ? WARNA.merah : TINTA} opacity={0.85} />
            )),
          )}
        </>
      );
    case 'kereta':
      return (
        <>
          <rect x="40" y="25" width="120" height="135" rx="30" fill={w} {...G} />
          <rect x="58" y="48" width="84" height="50" rx="10" fill={WARNA.langit} {...G} />
          <circle cx="70" cy="125" r="10" fill={WARNA.kuning} {...G} strokeWidth={6} />
          <circle cx="130" cy="125" r="10" fill={WARNA.kuning} {...G} strokeWidth={6} />
          <path d="M60 160 L40 190 M140 160 L160 190 M30 190 L170 190" {...G} />
        </>
      );
    case 'rumah':
      return (
        <>
          <path d="M35 95 L35 180 L165 180 L165 95" fill={WARNA.krem} {...G} />
          <path d="M15 105 L100 25 L185 105 Z" fill={w} {...G} />
          <rect x="82" y="120" width="40" height="60" rx="6" fill={WARNA.kuning} {...G} />
          <rect x="130" y="115" width="24" height="24" rx="4" fill={WARNA.langit} {...G} strokeWidth={7} />
        </>
      );
    case 'chat':
      return (
        <>
          <path d="M100 18 C150 18 185 52 185 95 C185 138 150 172 100 172 C86 172 73 169 62 164 L22 182 L34 145 C22 131 15 114 15 95 C15 52 50 18 100 18 Z" fill={w} {...G} />
          <path
            d="M72 62 C66 62 62 70 64 80 C70 108 92 128 118 136 C128 139 136 134 136 128 L136 118 L116 110 L106 120 C94 114 84 104 78 92 L88 82 L80 62 Z"
            fill={WARNA.putih}
            {...G}
            strokeWidth={7}
          />
        </>
      );
    case 'cek':
      return (
        <>
          <circle cx="100" cy="100" r="82" fill={w} {...G} />
          <path d="M58 102 L88 132 L145 70" fill="none" {...G} stroke={WARNA.putih} strokeWidth={22} />
          <path d="M58 102 L88 132 L145 70" fill="none" {...G} strokeWidth={0} />
        </>
      );
    case 'kunci':
      return (
        <g transform={`rotate(${goyang(t, 14, 1.2)} 100 100)`}>
          <path d="M150 30 C122 22 98 46 106 74 L32 148 C24 156 24 168 32 176 C40 184 52 184 60 176 L134 102 C162 110 186 86 178 58 L156 80 L132 76 L128 52 Z" fill={w} {...G} />
        </g>
      );
    case 'kilau': {
      const s = 0.75 + 0.25 * Math.abs(goyang(t, 1, 1.5));
      return (
        <g transform={`translate(100 100) scale(${s}) translate(-100 -100)`}>
          <path d="M100 10 C108 70 130 92 190 100 C130 108 108 130 100 190 C92 130 70 108 10 100 C70 92 92 70 100 10 Z" fill={w} {...G} />
        </g>
      );
    }
    case 'pusing':
      return (
        <g transform={`rotate(${t * 360} 100 100)`}>
          <path d="M100 100 m0 -10 a10 10 0 1 1 -10 10 a22 22 0 1 1 22 22 a36 36 0 1 1 -36 -36 a52 52 0 1 1 52 52 a70 70 0 1 1 -70 -70" fill="none" {...G} stroke={w} strokeWidth={14} />
        </g>
      );
    case 'pin':
      return (
        <>
          <path d="M100 190 C70 140 35 110 35 72 C35 36 64 12 100 12 C136 12 165 36 165 72 C165 110 130 140 100 190 Z" fill={w} {...G} />
          <circle cx="100" cy="72" r="26" fill={WARNA.putih} {...G} />
        </>
      );
    case 'tanya':
      return (
        <text x="100" y="170" fontSize="190" fontWeight={800} textAnchor="middle" fill={w} stroke={TINTA} strokeWidth={10} paintOrder="stroke" fontFamily="RacikJudul">
          ?
        </text>
      );
    case 'palu':
      return (
        <g transform={`rotate(${-20 + goyang(t, 18, 1.6)} 60 170)`}>
          <rect x="88" y="60" width="24" height="125" rx="10" fill="#B07A45" {...G} />
          <path d="M40 30 L150 30 C162 30 168 40 168 52 L168 72 L40 72 C30 72 25 62 25 51 C25 40 30 30 40 30 Z" fill={w} {...G} />
          <path d="M168 40 L190 34 L190 70 L168 64" fill={w} {...G} />
        </g>
      );
    case 'kanopi':
      return (
        <>
          <path d="M15 75 L100 30 L185 75 L185 92 L15 92 Z" fill={w} {...G} />
          {[40, 75, 110, 145].map((x) => <path key={x} d={`M${x} 52 L${x} 92`} {...G} strokeWidth={6} opacity={0.6} />)}
          <path d="M35 92 L35 180 M165 92 L165 180" {...G} strokeWidth={14} />
          <path d="M20 182 L180 182" {...G} />
        </>
      );
    case 'molen': {
      const r = t * 200;
      return (
        <>
          <path d="M20 150 L20 105 L60 105 L70 80 L95 80 L95 150 Z" fill={WARNA.kuning} {...G} />
          <rect x="30" y="112" width="25" height="18" rx="4" fill={WARNA.langit} {...G} strokeWidth={6} />
          <g transform={`rotate(${r * 0.15} 140 100)`}>
            <ellipse cx="140" cy="100" rx="52" ry="40" fill={w} {...G} />
            <path d="M100 85 L180 115 M100 110 L175 82" {...G} strokeWidth={7} opacity={0.7} />
          </g>
          <rect x="15" y="148" width="175" height="18" rx="6" fill={WARNA.abu} {...G} strokeWidth={7} />
          {[50, 150].map((x) => (
            <g key={x}>
              <circle cx={x} cy="172" r="18" fill={TINTA} />
              <circle cx={x} cy="172" r="7" fill="#D8D8DE" transform={`rotate(${r} ${x} 172)`} />
            </g>
          ))}
        </>
      );
    }
    case 'helmProyek':
      return (
        <>
          <path d="M28 135 C28 70 65 40 100 40 C135 40 172 70 172 135 Z" fill={w} {...G} />
          <path d="M88 42 L88 100 M112 42 L112 100" {...G} strokeWidth={8} />
          <path d="M10 135 L190 135 L190 150 C190 158 184 162 176 162 L24 162 C16 162 10 158 10 150 Z" fill={w} {...G} />
        </>
      );
    case 'bata':
      return (
        <>
          {[[20, 120], [105, 120], [62, 75], [147, 75], [-23, 75], [20, 30], [105, 30]].map(([x, y], i) => (
            <rect key={i} x={x} y={y} width="78" height="40" rx="5" fill={i % 3 ? w : '#C24A2C'} {...G} strokeWidth={7} />
          ))}
        </>
      );
    case 'dokumen':
      return (
        <>
          <path d="M40 15 L130 15 L165 50 L165 185 L40 185 Z" fill={WARNA.putih} {...G} />
          <path d="M130 15 L130 50 L165 50" fill={WARNA.krem} {...G} />
          <text x="62" y="78" fontSize="40" fontWeight={800} fill={w} fontFamily="RacikJudul">RAB</text>
          {[0, 1, 2, 3].map((i) => {
            const p = Math.min(1, Math.max(0, t * 1.6 - i * 0.35 - Math.floor(t * 1.6 / 4) * 0));
            return <path key={i} d={`M60 ${105 + i * 20} L${60 + 85 * p} ${105 + i * 20}`} {...G} strokeWidth={7} opacity={0.75} />;
          })}
        </>
      );
    case 'perisai':
      return (
        <>
          <path d="M100 12 L175 40 C175 110 150 160 100 188 C50 160 25 110 25 40 Z" fill={w} {...G} />
          <path d="M65 100 L92 127 L140 75" fill="none" {...G} stroke={WARNA.putih} strokeWidth={20} />
        </>
      );
    case 'penggaris':
      return (
        <>
          <g transform="rotate(-35 100 100)">
            <rect x="10" y="75" width="180" height="50" rx="8" fill={w} {...G} />
            {Array.from({length: 9}, (_, i) => (
              <path key={i} d={`M${28 + i * 18} 75 L${28 + i * 18} ${i % 2 ? 95 : 105}`} {...G} strokeWidth={5} />
            ))}
          </g>
          <path d="M140 150 L170 20 L185 24 L155 154 L140 175 Z" fill={WARNA.kuning} {...G} strokeWidth={7} />
        </>
      );
    case 'mikrofon':
      return (
        <>
          <rect x="70" y="15" width="60" height="105" rx="30" fill={w} {...G} />
          {[45, 65, 85].map((y) => <path key={y} d={`M82 ${y} L118 ${y}`} {...G} strokeWidth={5} opacity={0.6} />)}
          <path d="M45 90 C45 135 70 150 100 150 C130 150 155 135 155 90" fill="none" {...G} />
          <path d="M100 150 L100 182 M65 185 L135 185" {...G} />
        </>
      );
    case 'lampu': {
      const nyala = 0.6 + 0.4 * Math.abs(goyang(t, 1, 1.2));
      return (
        <>
          {Array.from({length: 7}, (_, i) => (
            <rect key={i} x={-5} y={-95} width={10} height={22} rx={5} fill={WARNA.kuning} opacity={nyala} transform={`translate(100 85) rotate(${-90 + i * 30})`} />
          ))}
          <path d="M100 25 C138 25 160 52 160 82 C160 108 142 120 132 138 L68 138 C58 120 40 108 40 82 C40 52 62 25 100 25 Z" fill={w} {...G} />
          <rect x="70" y="140" width="60" height="38" rx="8" fill="#B8B8C2" {...G} />
        </>
      );
    }
    case 'tangan':
      return (
        <path d="M70 185 L70 95 C70 82 90 82 90 95 L90 30 C90 16 112 16 112 30 L112 90 L112 60 C112 48 132 48 132 60 L132 95 L132 72 C132 62 150 62 150 74 L150 140 C150 170 130 185 105 185 Z" fill={w} {...G} />
      );
  }
};

/** Ikon pada ukuran `ukuran` px. `mulai` (opsional) membuatnya muncul memantul. */
export const Ikon: React.FC<{nama: NamaIkon; ukuran?: number; warna?: string; mulai?: number; style?: React.CSSProperties}> = ({
  nama,
  ukuran = 160,
  warna: w = 'hijau',
  mulai,
  style,
}) => {
  const t = useDetik();
  const p = mulai === undefined ? 1 : pop(t, mulai + 0.08, 240, 10);
  return (
    <svg width={ukuran} height={ukuran} viewBox="-12 -12 224 224" style={{flexShrink: 0, overflow: 'visible', transform: `scale(${p}) rotate(${(1 - p) * 30}deg)`, ...style}}>
      {gambar(nama, warnaObjek(w), t)}
    </svg>
  );
};

/** Ikon berdiri bebas di posisi x,y (pusat), dengan pop + goyang. */
export const IkonBebas: React.FC<{nama: NamaIkon; x: number; y: number; mulai: number; sampai?: number; ukuran?: number; warna?: string; miring?: number}> = ({
  nama,
  x,
  y,
  mulai,
  sampai,
  ukuran = 220,
  warna: w,
  miring = 0,
}) => {
  const t = useDetik();
  if (t < mulai || (sampai !== undefined && t >= sampai)) return null;
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%, -50%) rotate(${miring + goyang(t, 4, 0.6, x * 0.003)}deg)`}}>
      <Ikon nama={nama} ukuran={ukuran} warna={w} mulai={mulai} />
    </div>
  );
};
