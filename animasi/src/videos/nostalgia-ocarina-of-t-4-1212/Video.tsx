// Cuplikan podcast "Nostalgia Ocarina of Time Remake" (video bicara, multikamera): pembicara 9:16 + teks hook/poin + subtitle karaoke.
// Footage asli dipakai apa adanya: tiap frasa narasi dimulai dari src_start, dipotong di pergantian kamera, crop 9:16 ikut subjek.
import React from 'react';
import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {Klip, Subtitle, TeksFootage, useData, useFootage} from '../../kit';

type Potong = {dari: number; sampai: number; src: number; adegan?: string};

// === ADEGAN 1: rencana potongan (dari frasa → potongan per pergantian kamera) ===
const rencana = (
  frasa: {start: number; end: number; src_start?: number | null}[],
  batas: {id: string; mulai: number; selesai: number}[],
): Potong[] => {
  // gabung frasa yang berurutan di rekaman asli (selisih offset < 0,15 dtk) agar tak ada lompatan
  const gab: Potong[] = [];
  for (const f of frasa) {
    const src = f.src_start ?? f.start;
    const akhir = gab[gab.length - 1];
    if (akhir && Math.abs(src - f.start - (akhir.src - akhir.dari)) < 0.15) akhir.sampai = f.end;
    else gab.push({dari: f.start, sampai: f.end, src});
  }
  // pecah di batas adegan (pergantian kamera) agar crop tiap kamera tepat
  const hasil: Potong[] = [];
  for (const g of gab) {
    let t = g.dari;
    while (t < g.sampai - 0.01) {
      const s = g.src + (t - g.dari);
      const a = batas.find((b) => s >= b.mulai - 0.001 && s < b.selesai - 0.001);
      const sisa = a ? (a.selesai - s) : g.sampai - t;
      // sisa < 0,25 dtk: biarkan menyatu dengan potongan berikutnya (hindari kedipan)
      const dur = Math.min(g.sampai - t, sisa < 0.25 ? g.sampai - t : sisa);
      hasil.push({dari: t, sampai: t + dur, src: s, adegan: a?.id});
      t += dur;
    }
  }
  return hasil;
};

// === ADEGAN 2: teks hook & poin (waktu detik video; dari ucapan di narasi) ===
const POIN: {teks: string; mulai: number; sampai: number}[] = [
  {teks: 'OCARINA OF TIME\nREMAKE', mulai: 0, sampai: 2.4}, // hook di cold open
  {teks: 'DULU MAIN DI N64\nLEWAT EMULATOR', mulai: 32.9, sampai: 36.2},
  {teks: 'GAME 3D PERTAMA\nYANG LEGEND', mulai: 41.6, sampai: 44.0},
  {teks: 'KONTROL OCARINA\nDIGITAL', mulai: 57.0, sampai: 59.6},
  {teks: 'LAGU = SPELL\nDI DALAM GAME', mulai: 76.0, sampai: 79.0},
  {teks: 'FAST TRAVEL\nDIHAPUS', mulai: 92.3, sampai: 95.0},
  {teks: 'NPC IKUT\nWAKTU REAL TIME', mulai: 108.8, sampai: 111.6},
];

export const NostalgiaOcarina: React.FC = () => {
  const data = useData();
  const {fps} = useVideoConfig();
  const {adegan, pembicara} = useFootage();
  if (!pembicara) throw new Error('data.pembicara kosong');
  const batas = adegan.filter((a) => a.sumber === pembicara.nama && a.layak);
  const adeganOleh = (id?: string) => adegan.find((a) => a.id === id);
  const potong = rencana(data.frasa, batas);
  const bingkai = (d: number) => Math.round(d * fps);

  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      {potong.map((p, i) => {
        const a = adeganOleh(p.adegan);
        const dur = p.sampai - p.dari;
        const dari = bingkai(p.dari);
        const panjang = (i + 1 < potong.length ? bingkai(potong[i + 1].dari) : bingkai(p.sampai)) - dari;
        return (
          <Sequence key={i} from={dari} durationInFrames={Math.max(1, panjang)}>
            <Klip
              file={pembicara.file}
              mulai={p.src}
              cx={a?.crop ?? 0.5}
              zoom={i % 2 === 0 ? [1, 1.05] : [1.05, 1]}
              durasi={dur}
            />
          </Sequence>
        );
      })}
      {/* === ADEGAN 3: teks === */}
      {POIN.map((p, i) => (
        <TeksFootage key={i} teks={p.teks} mulai={p.mulai} sampai={p.sampai} posisi={1010} ukuran={i === 0 ? 84 : 66} sorot={['OCARINA', 'LEGEND', 'SPELL']} />
      ))}
      <Subtitle y={1330} maksKata={4} />
    </AbsoluteFill>
  );
};
