// Cuplikan opening YouTuber gaming (video bicara): pembicara 9:16 + sisipan shot lebar/dua orang + subtitle karaoke.
import React from 'react';
import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {Klip, Subtitle, TeksFootage, useData, useFootage} from '../../kit';

type Pot = {src: number; dur: number; cx: [number, number][]};

// Sisipan b-roll (detik di video jadi, durasi, adegan sumber, mulai di klip sumber)
const SISIP = [
  {at: 3.4, dur: 1.6, adegan: 'K1-2', src: 4.2}, // "Kalian ini berempat" → shot lebar meja
  {at: 8.3, dur: 1.7, adegan: 'K1-3', src: 9.75}, // "Kalian 4-4 bisa ngerjain barengan"
  {at: 40.9, dur: 1.9, adegan: 'K1-7', src: 20.2}, // "beberapa dari kita ngefans"
  {at: 71.0, dur: 1.8, adegan: 'K1-11', src: 32.3}, // reaksi dua orang
];

export const OpeningIkonikYoutube1306: React.FC = () => {
  const data = useData();
  const {fps} = useVideoConfig();
  const {adegan, pembicara} = useFootage();
  if (!pembicara) return null;
  const sc = adegan.filter((a) => a.sumber === pembicara.nama);

  // === ADEGAN 1: pembicara per frasa (gabung yang berurutan di video asli) ===
  const run: {src: number; dur: number}[] = [];
  data.frasa.forEach((f, i) => {
    const dur = f.end - f.start;
    const src = (f as unknown as {src_start: number}).src_start;
    const last = run[run.length - 1];
    if (last && i > 0 && Math.abs(src - (last.src + last.dur)) < 0.15) last.dur += dur;
    else run.push({src, dur});
  });
  const skala = data.durasi_narasi / Math.max(0.01, run.reduce((s, r) => s + r.dur, 0));
  const pot: Pot[] = [];
  for (const r of run) {
    let s = r.src;
    let sisa = r.dur * skala;
    while (sisa > 0.001) {
      const a = sc.find((x) => s >= x.mulai - 0.001 && s < x.selesai - 0.001);
      const d = Math.max(0.05, a ? Math.min(a.selesai, s + sisa) - s : sisa);
      pot.push({src: s, dur: Math.min(d, sisa), cx: a?.crop ?? []});
      s += d;
      sisa -= d;
    }
  }
  const cxOf = (c: [number, number][]) =>
    c.length ? (c.map(([a, b]) => [a, Math.min(0.68, Math.max(0.32, b))]) as [number, number][]) : 0.5;

  let t = 0;
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {pot.map((p, i) => {
        const dari = Math.round(t * fps);
        t += p.dur;
        const sampai = Math.round(t * fps);
        return (
          <Sequence key={i} from={dari} durationInFrames={Math.max(1, sampai - dari)}>
            <Klip file={pembicara.file} mulai={p.src} cx={cxOf(p.cx)} mode="cover" zoom={[1, 1.04]} durasi={p.dur} />
          </Sequence>
        );
      })}
      {/* === ADEGAN 2: sisipan b-roll (suara pembicara tetap jalan) === */}
      {SISIP.map((s) => {
        const a = adegan.find((x) => x.id === s.adegan);
        if (!a || !a.layak) return null;
        return (
          <Sequence key={s.adegan + s.at} from={Math.round(s.at * fps)} durationInFrames={Math.round(s.dur * fps)}>
            <Klip file={a.file} mulai={s.src} cx={cxOf(a.crop)} mode="cover" zoom={[1, 1.05]} durasi={s.dur} />
          </Sequence>
        );
      })}
      {/* === ADEGAN 3: teks hook === */}
      <TeksFootage teks={'SEKARANG NOMOR SATU\nNADIA OMAKASE'} mulai={0} sampai={2.8} posisi="atas" ukuran={56} sorot={['NOMOR SATU']} />
      {/* === ADEGAN 4: subtitle karaoke === */}
      <Subtitle y={1380} maksKata={4} ukuran={62} />
      {/* === ADEGAN 5: penutup === */}
      <TeksFootage teks={'Ikuti @contohbrand\nuntuk konten lainnya'} mulai={Math.max(0, data.durasi - 2.6)} sampai={data.durasi - 0.1} posisi="atas" ukuran={64} sorot={['@contohbrand']} />
    </AbsoluteFill>
  );
};
