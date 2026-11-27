// Kurva gerak khas kit. Semua waktu dalam detik absolut.
import {Easing, interpolate, spring} from 'remotion';
import {GAYA} from './tema';

const FPS = 30;

/** 0→1 memantul (overshoot) mulai detik `mulai`. */
export const pop = (t: number, mulai: number, kaku = 180, redam = 11): number =>
  t < mulai
    ? 0
    : spring({
        frame: (t - mulai) * FPS,
        fps: FPS,
        // diskalakan relatif ke gaya bawaan (180/11): garis-tipis lebih teredam (tanpa pantulan), tipografi tegas
        config: {stiffness: kaku * (GAYA.gerak.kaku / 180), damping: redam * (GAYA.gerak.redam / 11), mass: 0.7},
      });

/** 0→1 halus (ease-out) selama `durasi`. */
export const masuk = (t: number, mulai: number, durasi = 0.35): number =>
  interpolate(t, [mulai, mulai + durasi], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

/** 1→0 halus (ease-in) mulai `mulai`. */
export const keluar = (t: number, mulai: number, durasi = 0.25): number =>
  interpolate(t, [mulai, mulai + durasi], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.7, 0, 0.84, 0),
  });

/** Goyang idle (sinus) — membuat elemen diam tetap "hidup". */
export const goyang = (t: number, amp = 1, cepat = 1, fase = 0): number => Math.sin((t * cepat + fase) * Math.PI * 2) * amp;

/** Getar pudar setelah `mulai` (hentakan/impact) selama `durasi`. */
export const getar = (t: number, mulai: number, kuat = 18, durasi = 0.3): number => {
  if (t < mulai || t > mulai + durasi) return 0;
  const p = (t - mulai) / durasi;
  return Math.sin(p * Math.PI * 9) * kuat * (1 - p);
};

/** Nilai di antara a dan b mengikuti p (0..1). */
export const lerp = (a: number, b: number, p: number): number => a + (b - a) * p;
