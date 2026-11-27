// Adegan, kamera, latar, transisi — kerangka setiap shot.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useDetik} from './data';
import {KilauCahaya} from './Sinematik';
import {getar, keluar, lerp} from './gerak';
import {GAYA, TINTA, WARNA, campur, tepi, warna} from './tema';

/** Tampilkan isi hanya di rentang [dari, sampai) detik. Waktu di dalamnya tetap absolut. */
export const Adegan: React.FC<{dari: number; sampai: number; children: React.ReactNode}> = ({dari, sampai, children}) => {
  const t = useDetik();
  if (t < dari || t >= sampai) return null;
  return <AbsoluteFill>{children}</AbsoluteFill>;
};

/**
 * Kamera 2D: dorong pelan (push-in) sepanjang adegan + hentakan (zoom & getar) di detik `hentak`.
 * `fokus` = titik tujuan zoom (0..1 dari lebar/tinggi).
 */
export const Kamera: React.FC<{
  dari: number;
  sampai: number;
  zoom?: [number, number];
  geser?: [number, number];
  hentak?: number[];
  fokus?: [number, number];
  miring?: number;
  children: React.ReactNode;
}> = ({dari, sampai, zoom = [1, 1.06], geser = [0, 0], hentak = [], fokus = [0.5, 0.5], miring = 0, children}) => {
  const t = useDetik();
  const p = Math.min(1, Math.max(0, (t - dari) / Math.max(0.1, sampai - dari)));
  let s = lerp(zoom[0], zoom[1], p);
  let x = lerp(geser[0], geser[1], p);
  let y = 0;
  for (const h of hentak) {
    s += 0.07 * keluar(t, h, 0.35) * (t >= h ? 1 : 0);
    x += getar(t, h, 16, 0.3);
    y += getar(t, h + 0.03, 10, 0.3);
  }
  return (
    <AbsoluteFill
      style={{
        transform: `translate(${x}px, ${y}px) scale(${s}) rotate(${miring}deg)`,
        transformOrigin: `${fokus[0] * 100}% ${fokus[1] * 100}%`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

type Pola = 'polos' | 'titik' | 'garis' | 'sinar' | 'kotak';

/** Latar warna penuh + pola bergerak pelan (ciri kit: titik halftone / garis miring / sinar berputar). */
export const Latar: React.FC<{warna?: string; pola?: Pola; warnaPola?: string; kuatPola?: number}> = ({
  warna: w = 'hijau',
  pola: polaMinta = 'titik',
  warnaPola,
  kuatPola: kuatMinta = 0.16,
}) => {
  let pola = polaMinta;
  let kuatPola = kuatMinta;
  const t = useDetik();
  const dasar = warna(w);
  // perlakuan latar per gaya: pastel (garis-tipis), malam + pendar (neon), blok polos (tipografi), kertas redup
  const g = GAYA.id;
  const bg =
    g === 'garis-tipis'
      ? campur(dasar, '#FFFFFF', 0.8)
      : g === 'neon-malam' || g === 'grainy-gradient'
        ? WARNA.krem
        : g === 'kertas'
          ? campur(dasar, '#E6D6B8', 0.25)
          : g === 'pastel-ceria'
            ? campur(dasar, '#FFFFFF', 0.55)
            : dasar;
  if (g === 'pastel-ceria' || g === 'grainy-gradient') {
    // gumpalan besar bergerak pelan (bang-motion §7c "blob mengambang" / "gradien berpindah")
    const warnaBlob = g === 'pastel-ceria' ? [WARNA.kuning, WARNA.merah, WARNA.hijau] : [dasar, WARNA.ungu, WARNA.merah];
    return (
      <AbsoluteFill style={{backgroundColor: bg, overflow: 'hidden'}}>
        {warnaBlob.map((c, i) => {
          const x = 540 + Math.sin(t * 0.25 + i * 2.1) * 360;
          const y = 960 + Math.cos(t * 0.2 + i * 1.7) * 620;
          const r = g === 'pastel-ceria' ? 520 + i * 60 : 700 + i * 80;
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                left: x - r,
                top: y - r,
                width: r * 2,
                height: r * 2,
                borderRadius: '50%',
                background: g === 'pastel-ceria' ? c : `radial-gradient(circle, ${c} 0%, ${c}99 35%, transparent 70%)`,
                opacity: g === 'pastel-ceria' ? 0.55 : 0.75,
                filter: g === 'pastel-ceria' ? 'blur(6px)' : 'blur(40px)',
              }}
            />
          );
        })}
      </AbsoluteFill>
    );
  }
  const fg = g === 'garis-tipis' ? TINTA : g === 'neon-malam' ? dasar : warnaPola ? warna(warnaPola) : 'rgba(255,255,255,1)';
  if (g === 'tipografi-tebal') pola = 'polos';
  if (g === 'garis-tipis') kuatPola = Math.min(kuatPola, 0.07);
  if (g === 'neon-malam') kuatPola = Math.max(kuatPola, 0.18);
  const geser = (t * 40) % 80;
  let isi: React.ReactNode = null;
  if (pola === 'titik') {
    isi = (
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(${fg} 7px, transparent 8px)`,
          backgroundSize: '80px 80px',
          backgroundPosition: `${geser}px ${geser}px`,
          opacity: kuatPola,
        }}
      />
    );
  } else if (pola === 'garis') {
    isi = (
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(-35deg, ${fg} 0 26px, transparent 26px 80px)`,
          backgroundPosition: `${geser * 1.2}px 0`,
          opacity: kuatPola,
        }}
      />
    );
  } else if (pola === 'kotak') {
    isi = (
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${fg} 3px, transparent 3px), linear-gradient(90deg, ${fg} 3px, transparent 3px)`,
          backgroundSize: '90px 90px',
          backgroundPosition: `0 ${geser}px`,
          opacity: kuatPola,
        }}
      />
    );
  } else if (pola === 'sinar') {
    isi = (
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity: kuatPola}}>
        <div
          style={{
            width: 3200,
            height: 3200,
            flexShrink: 0,
            transform: `rotate(${t * 12}deg)`,
            background: `repeating-conic-gradient(${fg} 0deg 10deg, transparent 10deg 24deg)`,
            borderRadius: '50%',
          }}
        />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{backgroundColor: bg}}>
      {g === 'neon-malam' ? (
        <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 40%, ${dasar}66 0%, ${dasar}22 45%, transparent 75%)`}} />
      ) : null}
      {isi}
    </AbsoluteFill>
  );
};

/** Titik tepi bergerigi acak-tetap (deterministik per seed) untuk sobekan kertas: [x 0..100, goyang 0..1]. */
const gerigi = (n: number, seed: number): [number, number][] =>
  Array.from({length: n + 1}, (_, i) => [(i / n) * 100, (Math.sin(i * 7.13 + seed * 3.7) + 1) / 2]);

/**
 * Transisi khas gaya aktif, menutup layar penuh tepat di detik `pada` (letakkan pergantian adegan di sana):
 * pita (stiker flat), garis (garis-tipis: tirai tipis + garis), sobek (kertas), kilat (neon), blok (tipografi).
 */
export const Sapuan: React.FC<{pada: number; warna?: string[]; durasi?: number; kilau?: boolean}> = ({
  pada,
  warna: ws = ['kuning', 'merah', 'ungu'],
  durasi = 0.6,
  kilau = false,
}) => {
  const t = useDetik();
  const jenis = GAYA.transisi;
  // kilau (light leak) hanya untuk SATU momen istimewa per video, bukan di setiap potongan
  return (
    <>
      <SapuanInti t={t} pada={pada} ws={ws} durasi={durasi} />
      {kilau ? <KilauCahaya pada={pada} benih={Math.round(pada * 7) % 9} rona={jenis === 'garis' ? 200 : 0} kuat={jenis === 'garis' ? 0.45 : 0.6} /> : null}
    </>
  );
};

const SapuanInti: React.FC<{t: number; pada: number; ws: string[]; durasi: number}> = ({t, pada, ws, durasi}) => {
  const jenis = GAYA.transisi;
  const d = jenis === 'kilat' ? 0.36 : jenis === 'blok' ? 0.5 : durasi;
  const mulai = pada - d / 2;
  if (t < mulai || t > mulai + d) return null;
  const p = (t - mulai) / d;
  // ease: cepat masuk, melambat saat menutup layar, cepat keluar
  const pe = p < 0.5 ? 0.5 * Math.pow(p * 2, 0.55) : 1 - 0.5 * Math.pow((1 - p) * 2, 0.55);

  if (jenis === 'kilat') {
    const kuat = 1 - Math.abs(p - 0.5) * 2;
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <AbsoluteFill style={{background: warna(ws[0]), opacity: kuat * 0.85, mixBlendMode: 'screen'}} />
        <AbsoluteFill style={{background: '#FFFFFF', opacity: Math.max(0, kuat - 0.55) * 2.2}} />
        <AbsoluteFill style={{background: `repeating-linear-gradient(0deg, ${warna(ws[1])} 0 6px, transparent 6px 22px)`, opacity: kuat * 0.5, transform: `translateX(${(p - 0.5) * 120}px)`}} />
      </AbsoluteFill>
    );
  }
  if (jenis === 'blok') {
    // dua blok warna tegas bergantian dari bawah ke atas
    const a = Math.min(1, pe * 2);
    const b = Math.max(0, pe * 2 - 1);
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <AbsoluteFill style={{background: warna(ws[0]), clipPath: `inset(${(1 - a) * 100}% 0 ${b * 100}% 0)`}} />
      </AbsoluteFill>
    );
  }
  if (jenis === 'garis') {
    // tirai warna lembut dari kiri + satu garis tinta tipis di tepinya
    const x = lerp(-10, 110, pe);
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <AbsoluteFill style={{background: WARNA.krem, clipPath: `polygon(${x - 60}% 0, ${x}% 0, ${x - 12}% 100%, ${x - 72}% 100%)`}} />
        <svg width={1080} height={1920} style={{position: 'absolute'}}>
          <line x1={(x / 100) * 1080} y1={0} x2={((x - 12) / 100) * 1080} y2={1920} stroke={TINTA} strokeWidth={5} />
        </svg>
      </AbsoluteFill>
    );
  }
  if (jenis === 'sobek') {
    // selembar kertas bertepi sobek turun menutup lalu terus jatuh
    const y = lerp(-110, 110, pe);
    const atas = gerigi(18, pada).map(([x, g]) => `${x}% ${g * 3}%`);
    const bawah = gerigi(18, pada + 3)
      .reverse()
      .map(([x, g]) => `${x}% ${97 + g * 3}%`);
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <div
          style={{
            position: 'absolute',
            left: -40,
            width: 1160,
            height: 2400,
            top: `${y}%`,
            transform: 'translateY(-50%) rotate(-3deg)',
            background: warna(ws[0]),
            clipPath: `polygon(${[...atas, ...bawah].join(',')})`,
            filter: 'drop-shadow(0 12px 18px rgba(40,25,10,0.35))',
          }}
        />
      </AbsoluteFill>
    );
  }
  const x = lerp(-3400, 3400, pe);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          left: 540 - 1500 + x,
          top: -700,
          width: 3000,
          height: 3300,
          transform: 'rotate(-18deg)',
          display: 'flex',
        }}
      >
        {ws.map((w, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              backgroundColor: warna(w),
              borderLeft: tepi(10),
              borderRight: i === ws.length - 1 ? tepi(10) : undefined,
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};

/** Tekstur seluruh layar sesuai gaya: serat & vinyet kertas, atau scanline neon. Dipasang otomatis oleh Bingkai. */
export const Tekstur: React.FC = () => {
  const t = useDetik();
  if (GAYA.tekstur === 'kertas') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <svg width={1080} height={1920} style={{position: 'absolute', opacity: 0.22, mixBlendMode: 'multiply'}}>
          <filter id="serat">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={3} seed={Math.floor(t * 12) % 4} />
            <feColorMatrix values="0 0 0 0 0.35  0 0 0 0 0.25  0 0 0 0 0.15  0 0 0 0.9 0" />
          </filter>
          <rect width="100%" height="100%" filter="url(#serat)" />
        </svg>
        <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, transparent 55%, rgba(60,40,20,0.28) 100%)'}} />
      </AbsoluteFill>
    );
  }
  if (GAYA.tekstur === 'grain') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <svg width={1080} height={1920} style={{position: 'absolute', opacity: 0.16, mixBlendMode: 'overlay'}}>
          <filter id="butir">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={Math.floor(t * 24) % 8} />
          </filter>
          <rect width="100%" height="100%" filter="url(#butir)" />
        </svg>
      </AbsoluteFill>
    );
  }
  if (GAYA.tekstur === 'scanline') {
    return (
      <AbsoluteFill style={{pointerEvents: 'none'}}>
        <AbsoluteFill style={{background: 'repeating-linear-gradient(0deg, rgba(255,255,255,0.05) 0 2px, transparent 2px 5px)', mixBlendMode: 'screen'}} />
        <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%)'}} />
      </AbsoluteFill>
    );
  }
  return null;
};

/** Garis kecepatan (speed lines) untuk kesan melaju. */
export const GarisLaju: React.FC<{dari: number; sampai: number; warnaGaris?: string; arah?: 1 | -1}> = ({
  dari,
  sampai,
  warnaGaris = WARNA.putih,
  arah = 1,
}) => {
  const t = useDetik();
  if (t < dari || t >= sampai) return null;
  const garis = Array.from({length: 14}, (_, i) => {
    const y = 220 + ((i * 397) % 1500);
    const pj = 180 + ((i * 131) % 260);
    const kec = 2600 + ((i * 211) % 900);
    const x = ((((t - dari) * kec + i * 517) % 1700) - 300) * arah;
    return (
      <div
        key={i}
        style={{
          position: 'absolute',
          top: y,
          left: arah === 1 ? 1080 - x : x - pj,
          width: pj,
          height: 12,
          borderRadius: 6,
          backgroundColor: warnaGaris,
          opacity: 0.85,
        }}
      />
    );
  });
  return <AbsoluteFill style={{pointerEvents: 'none'}}>{garis}</AbsoluteFill>;
};
