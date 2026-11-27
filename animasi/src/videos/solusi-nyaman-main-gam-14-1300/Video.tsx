// Cuplikan podcast (video bicara): pembicara 9:16 + subtitle karaoke + teks hook. Footage asli apa adanya.
import React from 'react';
import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {Klip, Subtitle, TeksFootage, useData, useFootage} from '../../kit';

type Potongan = {src: number; dur: number; cx: [number, number][]};

// === ADEGAN 1: hook (cold open 0–2,76 dtk) + isi bicara ===
export const SolusiNyamanMainGame: React.FC = () => {
  const data = useData();
  const {fps} = useVideoConfig();
  const {adegan, pembicara} = useFootage();
  if (!pembicara) return null;
  const sc = adegan.filter((a) => a.sumber === pembicara.nama);

  // 1) gabungkan frasa yang berurutan di video asli jadi satu potongan
  const run: {src: number; dur: number}[] = [];
  data.frasa.forEach((f, i) => {
    const dur = f.end - f.start;
    const src = (f as unknown as {src_start: number}).src_start;
    const last = run[run.length - 1];
    const lanjut = last && i > 0 && Math.abs(src - (last.src + last.dur)) < 0.15;
    if (lanjut) last.dur += dur;
    else run.push({src, dur});
  });
  // jarak ke frasa berikut ditutup oleh durasi frasa (audio narasi tanpa celah): potongan menempel berurutan
  const total = data.durasi_narasi;
  const sum = run.reduce((s, r) => s + r.dur, 0);
  const skala = sum > 0 ? total / sum : 1; // koreksi pembulatan kecil

  // 2) pecah di batas adegan (kamera berganti) supaya crop mengikuti orang yang tepat
  const pot: Potongan[] = [];
  for (const r of run) {
    let s = r.src;
    let sisa = r.dur * skala;
    while (sisa > 0.001) {
      const a = sc.find((x) => s >= x.mulai - 0.001 && s < x.selesai - 0.001);
      const batas = a ? Math.min(a.selesai, s + sisa) : s + sisa;
      const d = Math.max(0.05, batas - s);
      pot.push({src: s, dur: Math.min(d, sisa), cx: a?.crop ?? []});
      s += d;
      sisa -= d;
    }
  }

  let t = 0;
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {pot.map((p, i) => {
        const dari = Math.round(t * fps);
        t += p.dur;
        const sampai = Math.round(t * fps);
        return (
          <Sequence key={i} from={dari} durationInFrames={Math.max(1, sampai - dari)}>
            <Klip file={pembicara.file} mulai={p.src} cx={p.cx.length ? p.cx.map(([a, b]) => [a, Math.min(0.68, Math.max(0.32, b))] as [number, number]) : 0.5} mode="cover" zoom={[1, 1.04]} durasi={p.dur} />
          </Sequence>
        );
      })}
      {/* === ADEGAN 2: hook teks === */}
      <TeksFootage teks={'SOLUSI NYAMAN\nMAIN GAME SAMBIL SANTAI'} mulai={0} sampai={2.7} posisi="atas" ukuran={76} sorot={['NYAMAN']} />
      {/* === ADEGAN 3: subtitle karaoke === */}
      <Subtitle y={1380} maksKata={4} ukuran={62} />
      {/* === ADEGAN 4: penutup === */}
      <TeksFootage teks={'Ikuti @contohbrand\nuntuk konten lainnya'} mulai={Math.max(0, data.durasi - 2.6)} sampai={data.durasi - 0.1} posisi="atas" ukuran={64} sorot={['@contohbrand']} />
    </AbsoluteFill>
  );
};
