// Cuplikan podcast (video bicara): pembicara 9:16 + animasi (hook, stiker kata kunci) + caption pink karaoke.
// Footage asli dipakai apa adanya; hanya potong, crop, zoom pelan, dan overlay.
import React from 'react';
import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {AMAN, FONT_JUDUL, Klip, useData, useFootage, waktuKata} from '../../kit';
import type {JalurCrop} from '../../kit';

const PINK = '#FF2E93';
const PINK_TUA = '#C2185B';
const PINK_MUDA = '#FFD1E8';
const KUNING = '#FFC400';

// Kata yang disorot kuning di caption (angka & istilah inti dari ucapan)
const SOROT = ['100', 'juta', 'view', 'membership', 'membershipnya', '10', '10-11', '3', 'jam', 'hari', 'algoritmanya', '80'];

const bersih = (s: string) => s.replace(/[.,!?;:]+$/, '');
const tkDari = (data: ReturnType<typeof useData>) => (kata: string, setelah: number, cadangan: number): number => {
  try {
    return waktuKata(data, kata, setelah);
  } catch {
    return cadangan;
  }
};

// === ADEGAN 1: hook (cold open, 0–3,3 dtk) ===
const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  if (t > 2.6) return null;
  const p = spring({frame, fps, config: {damping: 11, stiffness: 170}});
  const keluar = interpolate(t, [2.35, 2.6], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: AMAN.atas + 30,
        display: 'flex',
        justifyContent: 'center',
        opacity: keluar,
        transform: `scale(${0.6 + 0.4 * p}) rotate(${(1 - p) * -6}deg)`,
      }}
    >
      <div
        style={{
          fontFamily: FONT_JUDUL,
          fontWeight: 900,
          fontSize: 96,
          lineHeight: 1.05,
          textAlign: 'center',
          textTransform: 'uppercase',
          color: '#fff',
          background: `linear-gradient(135deg, ${PINK}, ${PINK_TUA})`,
          border: '8px solid #fff',
          borderRadius: 36,
          padding: '22px 44px 28px',
          boxShadow: '0 14px 0 rgba(0,0,0,.45)',
          WebkitTextStroke: '3px rgba(0,0,0,.35)',
          paintOrder: 'stroke fill',
        }}
      >
        Siapa nomor 1
        <br />
        sekarang?
      </div>
    </div>
  );
};

// === ADEGAN 2: stiker kata kunci (animasi pop) ===
const Stiker: React.FC<{teks: string; mulai: number; durasi?: number; kiri?: boolean; y?: number}> = ({teks, mulai, durasi = 2.2, kiri = false, y = AMAN.atas + 40}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  if (t < mulai || t > mulai + durasi) return null;
  const p = spring({frame: frame - mulai * fps, fps, config: {damping: 9, stiffness: 190}});
  const keluar = interpolate(t, [mulai + durasi - 0.2, mulai + durasi], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const goyang = Math.sin((t - mulai) * 7) * 2.2;
  return (
    <div
      style={{
        position: 'absolute',
        top: y,
        [kiri ? 'left' : 'right']: 70,
        opacity: keluar,
        transform: `scale(${p}) rotate(${(kiri ? -6 : 6) + goyang}deg)`,
        transformOrigin: kiri ? 'left center' : 'right center',
      }}
    >
      <div
        style={{
          fontFamily: FONT_JUDUL,
          fontWeight: 900,
          fontSize: 78,
          textTransform: 'uppercase',
          color: PINK_TUA,
          background: '#fff',
          border: `8px solid ${PINK}`,
          borderRadius: 28,
          padding: '10px 32px 14px',
          boxShadow: `0 10px 0 ${PINK}`,
        }}
      >
        ✦ {teks}
      </div>
    </div>
  );
};

// === ADEGAN 3: caption pink karaoke ===
const CaptionPink: React.FC<{y?: number; maksKata?: number}> = ({y = 1390, maksKata = 3}) => {
  const data = useData();
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const grup = React.useMemo(() => {
    const out: {start: number; end: number; kata: typeof data.kata}[] = [];
    for (const f of data.frasa) {
      const ks = data.kata.filter((k) => (k.start + k.end) / 2 >= f.start && (k.start + k.end) / 2 < f.end);
      for (let i = 0; i < ks.length; i += maksKata) {
        const g = ks.slice(i, i + maksKata);
        out.push({start: g[0].start, end: g[g.length - 1].end, kata: g});
      }
    }
    return out;
  }, [data, maksKata]);
  const idx = grup.findIndex((g, i) => t >= g.start - 0.05 && t < (grup[i + 1]?.start ?? g.end + 0.4) - 0.05);
  const aktif = idx >= 0 ? grup[idx] : null;
  if (!aktif || t > aktif.end + 0.5) return null;
  const p = spring({frame: frame - (aktif.start - 0.05) * fps, fps, config: {damping: 14, stiffness: 260}});
  return (
    <AbsoluteFill style={{alignItems: 'center'}}>
      <div
        style={{
          position: 'absolute',
          top: y,
          transform: `translateY(-50%) scale(${0.88 + 0.12 * p})`,
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: 12,
          maxWidth: 940,
          padding: '14px 26px 18px',
          borderRadius: 40,
          background: 'linear-gradient(135deg, rgba(255,46,147,.9), rgba(194,24,91,.9))',
          border: '6px solid #fff',
          boxShadow: '0 12px 0 rgba(0,0,0,.4), 0 0 40px rgba(255,46,147,.6)',
        }}
      >
        {aktif.kata.map((k, i) => {
          const on = t >= k.start - 0.03 && t < k.end + 0.08;
          const lewat = t >= k.start - 0.03;
          const kata = bersih(k.text);
          const sorot = SOROT.includes(kata.toLowerCase());
          return (
            <span
              key={i}
              style={{
                fontFamily: FONT_JUDUL,
                fontWeight: 900,
                fontSize: 70,
                textTransform: 'uppercase',
                padding: '0 12px 2px',
                borderRadius: 18,
                color: on ? PINK_TUA : sorot ? KUNING : '#fff',
                background: on ? '#fff' : 'transparent',
                opacity: lewat ? 1 : 0.6,
                transform: on ? 'scale(1.12) rotate(-2deg)' : undefined,
                textShadow: on ? 'none' : '0 4px 0 rgba(0,0,0,.35)',
              }}
            >
              {kata}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// === ADEGAN 4: bar progres + penutup ===
const Progres: React.FC<{total: number}> = ({total}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const w = Math.min(1, frame / fps / total);
  return (
    <div style={{position: 'absolute', left: 60, right: 60, top: AMAN.atas - 40, height: 12, borderRadius: 8, background: 'rgba(255,255,255,.35)'}}>
      <div style={{width: `${w * 100}%`, height: '100%', borderRadius: 8, background: `linear-gradient(90deg, ${PINK_MUDA}, ${PINK})`, boxShadow: `0 0 16px ${PINK}`}} />
    </div>
  );
};

const Penutup: React.FC<{mulai: number}> = ({mulai}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {brand} = useData();
  const t = frame / fps;
  if (t < mulai) return null;
  const p = spring({frame: frame - mulai * fps, fps, config: {damping: 12, stiffness: 160}});
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: 1000, display: 'flex', justifyContent: 'center', transform: `scale(${p})`}}>
      <div
        style={{
          fontFamily: FONT_JUDUL,
          fontWeight: 900,
          fontSize: 56,
          color: '#fff',
          background: `linear-gradient(135deg, ${PINK}, ${PINK_TUA})`,
          border: '6px solid #fff',
          borderRadius: 999,
          padding: '14px 44px 18px',
          boxShadow: '0 10px 0 rgba(0,0,0,.4)',
        }}
      >
        Ikuti {brand.instagram}
      </div>
    </div>
  );
};

export const OpeningIkonikYoutube: React.FC = () => {
  const data = useData();
  const {adegan, pembicara} = useFootage();
  const {fps} = useVideoConfig();
  const tk = tkDari(data);
  if (!pembicara) throw new Error('data.pembicara kosong');

  // Jalur crop pembicara: gabungan adegan, dengan lompatan tegas di batas adegan (tanpa geser di tengah)
  const jalur: JalurCrop = [];
  for (const a of adegan.filter((x) => x.sumber === pembicara.nama).sort((x, y) => x.mulai - y.mulai)) {
    const c = a.crop.length ? a.crop : [[a.mulai, 0.5] as [number, number]];
    if (jalur.length) jalur.push([a.mulai - 0.001, jalur[jalur.length - 1][1]]);
    jalur.push([a.mulai, c[0][1]], ...c.slice(1));
  }

  // Segmen per frasa; frasa yang berurutan di sumber digabung agar tanpa lompatan
  type Seg = {dari: number; dur: number; mulai: number};
  const segs: Seg[] = [];
  data.frasa.forEach((f, i) => {
    const sumber = f.src_start ?? 0;
    const dur = f.end - f.start;
    const sebelum = segs[segs.length - 1];
    if (sebelum && Math.abs(sebelum.mulai + sebelum.dur - sumber) < 0.15 && i > 0) {
      sebelum.dur += dur;
    } else {
      segs.push({dari: f.start, dur, mulai: sumber});
    }
  });
  const akhirNarasi = data.durasi_narasi ?? data.frasa[data.frasa.length - 1].end;
  // segmen terakhir menutup sampai akhir narasi; ekor 1 dtk pelan (slow-mo) agar tidak melewati akhir sumber
  segs[segs.length - 1].dur = akhirNarasi - segs[segs.length - 1].dari;
  const ekorMulai = segs[segs.length - 1].mulai + segs[segs.length - 1].dur;
  const durTotal = data.durasi;

  const tCta = durTotal - 2.2;
  const kataKunci = [
    {teks: 'Membership', t: tk('membershipnya', 0, 17.6), kiri: true},
    {teks: '100 juta view', t: tk('100', 0, 50.2), kiri: false},
    {teks: '3 jam!', t: tk('3', 64, 64.8), kiri: true},
    {teks: 'Algoritma', t: tk('algoritmanya', 0, 66.9), kiri: false},
  ];

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {/* === ADEGAN 0: pembicara (potongan per frasa) === */}
      {segs.map((s, i) => (
        <Sequence key={i} from={Math.round(s.dari * fps)} durationInFrames={Math.max(1, Math.round(s.dur * fps))}>
          <Klip
            file={pembicara.file}
            mulai={s.mulai}
            cx={jalur}
            zoom={i % 2 ? [1.07, 1] : [1, 1.07]}
            durasi={s.dur}
          />
        </Sequence>
      ))}
      <Sequence from={Math.round(akhirNarasi * fps)} durationInFrames={Math.max(1, Math.round((durTotal - akhirNarasi) * fps))}>
        <Klip file={pembicara.file} mulai={ekorMulai - 0.05} speed={0.3} cx={jalur} zoom={[1.07, 1.1]} durasi={durTotal - akhirNarasi} />
      </Sequence>

      {/* === ADEGAN 1: hook === */}
      <Hook />
      {/* === ADEGAN 2: stiker kata kunci === */}
      {kataKunci.map((k) => (
        <Stiker key={k.teks} teks={k.teks} mulai={k.t} kiri={k.kiri} />
      ))}
      {/* === ADEGAN 3: caption pink === */}
      <CaptionPink />
      <Progres total={durTotal} />
      {/* === ADEGAN 4: penutup === */}
      <Penutup mulai={tCta} />
    </AbsoluteFill>
  );
};
