// Klip footage asli untuk mode "Claude + Remotion" di Buat video (data.mode === 'footage').
// File sudah dinormalisasi `autoreels animasi footage` ke public/<nama>/klip/*.mp4 (H.264, tanpa audio, tinggi ≤ 1920).
import {Video} from '@remotion/media';
import React from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useData} from './data';

export type JalurCrop = [number, number][]; // [[detik di klip sumber, pusat crop 0–1], …] (data.adegan[].crop)

export type KlipProps = {
  /** path relatif public, mis. data.klip[i].file */
  file: string;
  /** detik di klip sumber tempat bagian ini mulai (mis. data.adegan[i].mulai atau momen_terbaik − 0.5) */
  mulai: number;
  /** kecepatan putar: 1 = normal, 4–8 = speed-up/timelapse, 0.5 = slow-mo */
  speed?: number;
  /** reframe 9:16: 'cover' (isi layar, crop ikut subjek) | 'blur_pad' (footage lebar utuh di tengah, latar buram) */
  mode?: 'cover' | 'blur_pad';
  /** pusat crop 0–1 (angka tetap) atau jalur per detik sumber (adegan.crop) */
  cx?: number | JalurCrop;
  /** zoom awal → akhir selama klip (1 = tanpa zoom); push-in pelan: [1, 1.08] */
  zoom?: [number, number];
  /** durasi klip di layar, detik (untuk zoom). Wajib bila zoom dipakai. */
  durasi?: number;
  /** audio asli: 0 = diam (default; b-roll biasanya bising) */
  volume?: number;
};

const PENUH: React.CSSProperties = {width: '100%', height: '100%'};

const posisi = (cx: KlipProps['cx'], tSumber: number): number => {
  if (cx === undefined) return 0.5;
  if (typeof cx === 'number') return cx;
  if (!cx.length) return 0.5;
  return interpolate(tSumber, cx.map((p) => p[0]), cx.map((p) => p[1]), {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
};

/** Satu klip memenuhi layar. Taruh di dalam <Sequence> (frame lokal mulai dari 0 di awal sequence). */
export const Klip: React.FC<KlipProps> = ({file, mulai, speed = 1, mode = 'cover', cx, zoom, durasi, volume = 0}) => {
  const {fps} = useVideoConfig();
  const frame = useCurrentFrame();
  const tSumber = mulai + (frame / fps) * speed;
  const x = posisi(cx, tSumber) * 100;
  const skala = zoom && durasi ? interpolate(frame, [0, durasi * fps], zoom, {extrapolateRight: 'clamp'}) : 1;
  const src = staticFile(file);
  const sama = {trimBefore: Math.round(mulai * fps), playbackRate: speed, volume, src};
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#000'}}>
      {mode === 'blur_pad' && (
        <AbsoluteFill style={{transform: 'scale(1.35)', filter: 'blur(36px) brightness(0.7)'}}>
          <Video {...sama} muted objectFit="cover" style={PENUH} />
        </AbsoluteFill>
      )}
      <AbsoluteFill style={{transform: `scale(${skala})`}}>
        <Video {...sama} objectFit={mode === 'blur_pad' ? 'contain' : 'cover'} style={{...PENUH, objectPosition: `${x}% 50%`}} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Data footage dari data.json (tipe longgar; isi dibuat footage_remotion.py). */
export type AdeganFootage = {
  id: string;
  file: string;
  /** nama berkas sumber (sama dengan data.pembicara.nama bila adegan dari klip pembicara) */
  sumber?: string;
  mulai: number;
  selesai: number;
  durasi: number;
  layak: boolean;
  alasan: string[];
  tajam: number;
  terang: number;
  goyang: number;
  gerak: number;
  /** jalur crop per detik sumber → langsung ke <Klip cx=…> */
  crop: JalurCrop;
  /** detik di klip sumber dengan skor momen tertinggi (subjek utuh, tajam, stabil) */
  momen_terbaik: number | null;
  deskripsi?: string;
};

export const useFootage = () => {
  const d = useData() as unknown as {
    adegan?: AdeganFootage[];
    klip?: {file: string; nama: string; durasi: number; lebar: number; tinggi: number}[];
    beats?: number[];
    tempo?: number;
    preset?: Record<string, unknown>;
    hook_text?: string | null;
    cta_text?: string | null;
    pembicara?: {file: string; nama: string; durasi: number; lebar: number; tinggi: number};
  };
  return {adegan: d.adegan ?? [], klip: d.klip ?? [], beats: d.beats ?? [], tempo: d.tempo ?? 0, preset: d.preset ?? {},
    hook: d.hook_text ?? null, cta: d.cta_text ?? null, pembicara: d.pembicara ?? null};
};
