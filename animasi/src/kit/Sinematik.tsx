// Sentuhan sinematik dari @remotion/effects (skill remotion-best-practices → markup/light-leaks, effects).
import {lightLeak} from '@remotion/effects/light-leak';
import React from 'react';
import {AbsoluteFill, interpolate, Solid, useVideoConfig} from 'remotion';
import {useDetik} from './data';

/**
 * Kilau cahaya (light leak) di sekitar detik `pada`: muncul di paruh pertama, surut di paruh kedua.
 * `rona` = geser hue (0 kuning-oranye, 120 hijau, 240 biru). Dipasang otomatis oleh Sapuan di gaya yang cocok.
 */
export const KilauCahaya: React.FC<{pada: number; durasi?: number; benih?: number; rona?: number; kuat?: number}> = ({
  pada,
  durasi = 1.1,
  benih = 0,
  rona = 0,
  kuat = 0.85,
}) => {
  const t = useDetik();
  const {width, height} = useVideoConfig();
  const mulai = pada - durasi * 0.35;
  if (t < mulai || t > mulai + durasi) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen', opacity: kuat}}>
      <Solid
        width={width}
        height={height}
        effects={[
          lightLeak({
            seed: benih,
            hueShift: rona,
            progress: interpolate(t, [mulai, mulai + durasi], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
          }),
        ]}
      />
    </AbsoluteFill>
  );
};
