// Klip podcast vertikal 9:16 dari footage: potongan jump-cut yang mengikuti pembicara, subtitle kinetik per kata
// (gaya Stiker Flat dari kit: Montserrat ExtraBold, garis tinta, bayangan keras), hook di atas, dan satu momen puncak
// (kartu "1 VIDEO / HARI · 10 TAHUN"). Data: public/podcast-klip/klip.json (dibuat buat_data.py).
// Aturan caption mengikuti skill hyperframes captions-overlay: rail = subtitle verbatim, punch word = aksen di rail,
// embed (kartu puncak) hanya satu. Gerak: tiap potongan masuk dengan punch-in lalu push-in pelan (tanpa wobble).
import {loadFont} from '@remotion/fonts';
import React, {useEffect, useState} from 'react';
import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  cancelRender,
  continueRender,
  delayRender,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import {getar, keluar, masuk, pop} from '../../kit/gerak';

export type Kata = {t: string; s: number; e: number; punch: boolean; peak: boolean};
export type Potong = {dari: number; srcIn: number; srcOut: number; shot: {src: number; cx: number}[]};
export type KlipData = {fps: number; durasi: number; video: string; potong: Potong[]; grup: number[][]; kata: Kata[]};
export type KlipProps = {data: KlipData | null};

const W = 1080;
const H = 1920;
const SRC_W = 1920;
const SRC_H = 1080;
const FONT = 'KlipJudul';
const TINTA = '#0B0B0C';
const KUNING = '#FFC93C';
const HIJAU = '#00953F';
const PUTIH = '#FFFFFF';

const teksTinta = (uk: number, warna: string): React.CSSProperties => ({
  fontFamily: FONT,
  fontWeight: 800,
  fontSize: uk,
  lineHeight: 1.02,
  color: warna,
  textTransform: 'uppercase',
  letterSpacing: -1,
  WebkitTextStroke: `${Math.round(uk * 0.12)}px ${TINTA}`,
  paintOrder: 'stroke fill',
  filter: `drop-shadow(0 ${Math.round(uk * 0.09)}px 0 ${TINTA})`,
});

/** Satu potongan footage, dipotong 9:16 mengikuti titik tengah shot yang sedang tampil. */
const Potongan: React.FC<{p: Potong; fps: number; src: string; tPeak: number}> = ({p, fps, src, tPeak}) => {
  const f = useCurrentFrame();
  const lokal = f / fps;
  const tSrc = p.srcIn + lokal;
  const shot = [...p.shot].reverse().find((s) => tSrc >= s.src - 1e-3) ?? p.shot[0];
  const durasi = p.srcOut - p.srcIn;
  // punch-in di awal potongan (1.07 → 1) lalu push-in pelan sampai akhir; dorongan ekstra di momen puncak
  const tGlobal = p.dari + lokal;
  const zoom =
    1 + 0.07 * (1 - masuk(lokal, 0, 0.3)) + 0.045 * (lokal / durasi) + 0.06 * masuk(tGlobal, tPeak, 0.35);
  const skala = (H / SRC_H) * zoom;
  const lebar = SRC_W * skala;
  const kiri = Math.min(0, Math.max(W - lebar, W / 2 - shot.cx * lebar));
  const atas = (H - SRC_H * skala) / 2;
  // fade audio 3 frame di tiap sambungan agar jump cut tidak "klik"
  const vol = (fr: number) => Math.min(1, fr / 3, (durasi * fps - fr) / 3);
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: TINTA}}>
      <OffthreadVideo
        src={src}
        trimBefore={Math.round(p.srcIn * fps)}
        volume={vol}
        style={{position: 'absolute', left: kiri, top: atas, width: lebar, height: SRC_H * skala}}
      />
    </AbsoluteFill>
  );
};

/** Hook di atas selama pertanyaan pembuka. */
const Hook: React.FC<{t: number; sampai: number}> = ({t, sampai}) => {
  const hilang = keluar(t, sampai, 0.25);
  if (hilang <= 0) return null;
  const baris: {teks: string; warna: string; uk: number}[] = [
    {teks: '1 tip buat', warna: PUTIH, uk: 62},
    {teks: 'calon youtuber', warna: KUNING, uk: 84},
    {teks: 'gaming', warna: KUNING, uk: 84},
  ];
  let n = 0;
  const pPelat = pop(t, 0.05, 220, 16);
  return (
    <div
      style={{
        position: 'absolute',
        top: 96,
        left: 0,
        width: W,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        transform: `rotate(-3deg) scale(${(0.85 + 0.15 * hilang) * (0.6 + 0.4 * pPelat)})`,
        opacity: hilang,
      }}
    >
      {baris.map((b, bi) => (
        <div key={bi} style={{display: 'flex', gap: b.uk * 0.25, marginTop: bi === 0 ? 0 : -4}}>
          {b.teks.split(' ').map((k) => {
            const p = pop(t, 0.12 + n++ * 0.11);
            return (
              <span
                key={k + n}
                style={{
                  ...teksTinta(b.uk, b.warna),
                  display: 'inline-block',
                  transform: `translateY(${(1 - p) * 60}px) scale(${0.3 + 0.7 * p}) rotate(${(1 - p) * -12}deg)`,
                  opacity: Math.min(1, p * 3),
                }}
              >
                {k}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

/** Pecah grup jadi deret kata berurutan dengan status punch yang sama (punch berurutan = satu pelat). */
const runs = (g: number[], kata: Kata[]): number[][] =>
  g.reduce<number[][]>((acc, ki) => {
    const last = acc[acc.length - 1];
    if (last && kata[last[0]].punch === kata[ki].punch && kata[ki].punch) last.push(ki);
    else acc.push([ki]);
    return acc;
  }, []);

/** Subtitle kinetik: satu grup (≤3 kata) tampil; tiap kata pop saat diucapkan, kata aktif kuning, punch word di pelat hijau. */
const Subtitle: React.FC<{t: number; data: KlipData; tPeak: number}> = ({t, data, tPeak}) => {
  const {grup, kata} = data;
  const gi = grup.findIndex((g, i) => {
    const mulai = kata[g[0]].s;
    const akhir = i + 1 < grup.length ? kata[grup[i + 1][0]].s : kata[g[g.length - 1]].e + 0.5;
    return t >= mulai && t < akhir;
  });
  if (gi < 0) return null;
  const g = grup[gi];
  if (g.some((ki) => kata[ki].peak)) return null;
  // saat kartu puncak tampil, subtitle turun sedikit agar tidak bertabrakan
  const turun = 90 * masuk(t, tPeak, 0.3);
  return (
    <div
      style={{
        position: 'absolute',
        top: 1170 + turun,
        left: 60,
        width: W - 120,
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        alignItems: 'center',
        columnGap: 26,
        rowGap: 10,
      }}
    >
      {runs(g, kata).map((run, ri) => {
        const kata0 = kata[run[0]];
        if (t < kata0.s - 0.03) return null;
        const kataRun = run.map((ki) => {
          const k = kata[ki];
          const p = pop(t, k.s - 0.03, 260, 14);
          const aktif = t >= k.s && t < k.e + 0.05;
          const uk = k.punch ? 112 : 96;
          const isi = k.t.replace(/[.,?!]+$/, '');
          return (
            <span
              key={ki}
              style={{
                display: 'inline-block',
                transform: `translateY(${(1 - p) * 40}px) scale(${(0.4 + 0.6 * p) * (aktif ? 1.08 : 1)}) rotate(${(1 - p) * -8}deg)`,
                opacity: t < k.s - 0.03 ? 0 : Math.min(1, p * 3),
                ...teksTinta(uk, aktif ? KUNING : PUTIH),
              }}
            >
              {isi}
            </span>
          );
        });
        if (!kata0.punch) return <React.Fragment key={ri}>{kataRun}</React.Fragment>;
        const pp = pop(t, kata0.s - 0.05, 240, 14);
        return (
          <span
            key={ri}
            style={{
              display: 'inline-flex',
              gap: 22,
              background: HIJAU,
              border: `7px solid ${TINTA}`,
              borderRadius: 18,
              boxShadow: `8px 14px 0 ${TINTA}`,
              padding: '2px 22px 8px',
              transform: `rotate(-2deg) scale(${0.5 + 0.5 * pp})`,
              opacity: Math.min(1, pp * 3),
            }}
          >
            {kataRun}
          </span>
        );
      })}
    </div>
  );
};

/** Satu-satunya "embed": kartu puncak saat "10 tahun". */
const KartuPuncak: React.FC<{t: number; tPeak: number}> = ({t, tPeak}) => {
  if (t < tPeak - 0.05) return null;
  const p = pop(t, tPeak - 0.05, 200, 12);
  const p2 = pop(t, tPeak + 0.22, 200, 12);
  const goyah = getar(t, tPeak + 0.22, 14, 0.3);
  return (
    <div
      style={{
        position: 'absolute',
        top: 250,
        left: 0,
        width: W,
        display: 'flex',
        justifyContent: 'center',
        transform: `translateX(${goyah}px) rotate(${-4 + (1 - p) * -10}deg) scale(${0.2 + 0.8 * p})`,
        opacity: Math.min(1, p * 3),
      }}
    >
      <div
        style={{
          background: KUNING,
          border: `9px solid ${TINTA}`,
          borderRadius: 34,
          boxShadow: `12px 20px 0 ${TINTA}`,
          padding: '26px 54px 34px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <span style={{...teksTinta(64, PUTIH), whiteSpace: 'nowrap'}}>1 video / hari</span>
        <span
          style={{
            ...teksTinta(150, PUTIH),
            display: 'inline-block',
            whiteSpace: 'nowrap',
            transform: `scale(${0.3 + 0.7 * p2})`,
            opacity: Math.min(1, p2 * 3),
            marginTop: 4,
          }}
        >
          10 tahun
        </span>
      </div>
    </div>
  );
};

export const PodcastKlip: React.FC<KlipProps> = ({data}) => {
  const [handle] = useState(() => delayRender('Memuat font klip'));
  useEffect(() => {
    loadFont({family: FONT, url: staticFile('_brand/Montserrat-ExtraBold.ttf'), weight: '800'})
      .then(() => continueRender(handle))
      .catch((e) => cancelRender(e));
  }, [handle]);
  const frame = useCurrentFrame();
  if (!data) return null;
  const {fps} = data;
  const t = frame / fps;
  const src = staticFile(data.video);
  const tPeak = data.kata.find((k) => k.peak)?.s ?? data.durasi + 10;
  const hookSampai = data.potong[1]?.dari ? data.potong[1].dari - 0.3 : 5;
  return (
    <AbsoluteFill style={{backgroundColor: TINTA, overflow: 'hidden'}}>
      {data.potong.map((p, i) => (
        <Sequence
          key={i}
          from={Math.round(p.dari * fps)}
          durationInFrames={Math.round((p.srcOut - p.srcIn) * fps)}
          premountFor={fps}
        >
          <Potongan p={p} fps={fps} src={src} tPeak={tPeak} />
        </Sequence>
      ))}
      {/* gelap tipis atas & bawah agar teks terbaca di atas footage terang (overlay, bukan pita kosong) */}
      <AbsoluteFill
        style={{
          background:
            'linear-gradient(180deg, rgba(11,11,12,0.55) 0%, rgba(11,11,12,0) 28%, rgba(11,11,12,0) 52%, rgba(11,11,12,0.6) 100%)',
        }}
      />
      <Hook t={t} sampai={hookSampai} />
      <KartuPuncak t={t} tPeak={tPeak} />
      <Subtitle t={t} data={data} tPeak={tPeak} />
      {/* bilah progres */}
      <div style={{position: 'absolute', top: 0, left: 0, height: 12, width: (W * t) / data.durasi, background: KUNING}} />
    </AbsoluteFill>
  );
};
