// Dasar kit 3D: panggung (ThreeCanvas + cahaya + kabut), material toon, bentuk bergaris tinta (inverted hull),
// kamera ber-keyframe. Semua gerak dari useCurrentFrame (lewat useDetik) — useFrame dilarang (berkedip saat render).
import {colorCorrection} from '@remotion/effects/color-correction';
import {linearProgressiveBlur} from '@remotion/effects/linear-progressive-blur';
import {vignette} from '@remotion/effects/vignette';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import React, {useLayoutEffect, useMemo} from 'react';
import {AbsoluteFill, HtmlInCanvas, useVideoConfig} from 'remotion';
import * as THREE from 'three';
import {DataCtx, useData, useDetik} from '../kit/data';
import {getar, lerp} from '../kit/gerak';
import {TINTA} from '../kit/tema';

export type V3 = [number, number, number];

/** Gradien 3 tingkat untuk cel-shading (bayangan bertingkat tegas, khas kartun). */
let gradien: THREE.DataTexture | null = null;
const peta3Tingkat = () => {
  if (!gradien) {
    gradien = new THREE.DataTexture(new Uint8Array([90, 90, 90, 255, 170, 170, 170, 255, 255, 255, 255, 255]), 3, 1);
    gradien.minFilter = THREE.NearestFilter;
    gradien.magFilter = THREE.NearestFilter;
    gradien.needsUpdate = true;
  }
  return gradien;
};

/** Material toon (cel-shading). */
export const Toon: React.FC<{warna: string; emisi?: string; intensitas?: number; duaSisi?: boolean}> = ({warna, emisi, intensitas = 0, duaSisi}) => (
  <meshToonMaterial color={warna} gradientMap={peta3Tingkat()} emissive={emisi ?? '#000000'} emissiveIntensity={intensitas} side={duaSisi ? THREE.DoubleSide : THREE.FrontSide} />
);

/**
 * Bentuk bergaris tinta: mesh toon + salinan geometri sedikit lebih besar bermuka-belakang hitam (inverted hull).
 * `geo` = fungsi yang mengembalikan elemen geometri (dipanggil dua kali: isi & garis).
 */
export const Bentuk: React.FC<{
  geo: () => React.ReactElement;
  warna: string;
  posisi?: V3;
  rotasi?: V3;
  skala?: V3 | number;
  garis?: number;
  bayangan?: boolean;
  emisi?: string;
  intensitas?: number;
}> = ({geo, warna, posisi, rotasi, skala, garis = 0.08, bayangan = true, emisi, intensitas}) => (
  <group position={posisi} rotation={rotasi} scale={skala}>
    <mesh castShadow={bayangan} receiveShadow>
      {geo()}
      <Toon warna={warna} emisi={emisi} intensitas={intensitas} />
    </mesh>
    {garis > 0 ? (
      <mesh scale={1 + garis}>
        {geo()}
        <meshBasicMaterial color={TINTA} side={THREE.BackSide} fog={false} />
      </mesh>
    ) : null}
  </group>
);

export type Suasana = 'siang' | 'senja' | 'malam';
const SUASANA: Record<Suasana, {langit: string; kabut: string; matahari: string; kuat: number; tanah: string; arah: V3}> = {
  siang: {langit: '#8ED8F8', kabut: '#CBEFFF', matahari: '#FFF6E0', kuat: 2.4, tanah: '#5E8C3A', arah: [8, 14, 6]},
  senja: {langit: '#FF9E6B', kabut: '#FFD2A6', matahari: '#FFB070', kuat: 2.0, tanah: '#7A5A3A', arah: [-10, 5, -6]},
  malam: {langit: '#1B1747', kabut: '#2A2366', matahari: '#9AA8FF', kuat: 0.7, tanah: '#24243F', arah: [4, 10, 4]},
};

const campurWarna = (a: string, b: string, p: number) => new THREE.Color(a).lerp(new THREE.Color(b), p);

/**
 * Panggung 3D satu shot: kanvas, langit/kabut, cahaya matahari dengan bayangan, data video diteruskan ke dalam kanvas.
 * `suasana` + `menuju` (+ `p` 0..1) = transisi suasana (mis. siang → senja untuk "bebas atur waktu").
 */
export const Panggung3D: React.FC<{
  suasana?: Suasana;
  menuju?: Suasana;
  p?: number;
  kabut?: [number, number];
  /** Ada subjek utama → tepi atas & bawah dikaburkan (tilt-shift ala lensa, kesan miniatur). */
  fokus?: V3;
  /** Kekuatan blur tepi (px). */
  bokeh?: number;
  children: React.ReactNode;
}> = ({suasana = 'siang', menuju, p = 0, kabut = [70, 280], fokus, bokeh = 3.2, children}) => {
  const data = useData();
  const {width, height} = useVideoConfig();
  const a = SUASANA[suasana];
  const b = SUASANA[menuju ?? suasana];
  const langit = campurWarna(a.langit, b.langit, p);
  const warnaKabut = campurWarna(a.kabut, b.kabut, p);
  const arah: V3 = [lerp(a.arah[0], b.arah[0], p), lerp(a.arah[1], b.arah[1], p), lerp(a.arah[2], b.arah[2], p)];
  return (
    <AbsoluteFill style={{background: `#${langit.getHexString()}`}}>
      <HtmlInCanvas
        width={width}
        height={height}
        effects={[
          colorCorrection({contrast: 1.08, saturation: 1.12, vibrance: 0.15, temperature: menuju === 'senja' || suasana === 'senja' ? 0.12 : 0.04}),
          ...(fokus
            ? [
                linearProgressiveBlur({start: [0.5, 0], end: [0.5, 0.32], startBlur: bokeh * 3, endBlur: 0}),
                linearProgressiveBlur({start: [0.5, 1], end: [0.5, 0.7], startBlur: bokeh * 3, endBlur: 0}),
              ]
            : []),
          vignette({amount: 0.18}),
        ]}
      >
      <ThreeCanvas width={width} height={height} shadows camera={{fov: 40, near: 0.1, far: 400, position: [0, 4, 12]}}>
        <DataCtx.Provider value={data}>
          <color attach="background" args={[langit]} />
          <fog attach="fog" args={[warnaKabut, kabut[0], kabut[1]]} />
          <hemisphereLight args={[langit, a.tanah, 1.1]} />
          <directionalLight
            position={arah}
            intensity={lerp(a.kuat, b.kuat, p)}
            color={campurWarna(a.matahari, b.matahari, p)}
            castShadow
            shadow-mapSize={[2048, 2048]}
            shadow-camera-left={-30}
            shadow-camera-right={30}
            shadow-camera-top={30}
            shadow-camera-bottom={-30}
            shadow-bias={-0.0005}
          />
          {children}
        </DataCtx.Provider>
      </ThreeCanvas>
      </HtmlInCanvas>
    </AbsoluteFill>
  );
};

export type KunciKamera = {t: number; pos: V3; lihat: V3; fov?: number};

const halus = (x: number) => x * x * x * (x * (x * 6 - 15) + 10); // smootherstep

/** Kamera: interpolasi halus antar-kunci (detik absolut) + hentakan (getar) di detik `hentak`. */
export const Kamera3D: React.FC<{kunci: KunciKamera[]; hentak?: number[]}> = ({kunci, hentak = []}) => {
  const t = useDetik();
  const {camera} = useThree();
  let i = 0;
  while (i < kunci.length - 1 && t >= kunci[i + 1].t) i++;
  const a = kunci[i];
  const b = kunci[Math.min(i + 1, kunci.length - 1)];
  const q = b.t > a.t ? halus(Math.min(1, Math.max(0, (t - a.t) / (b.t - a.t)))) : 0;
  const mix = (u: V3, v: V3): V3 => [lerp(u[0], v[0], q), lerp(u[1], v[1], q), lerp(u[2], v[2], q)];
  const pos = mix(a.pos, b.pos);
  const lihat = mix(a.lihat, b.lihat);
  const g = hentak.reduce((s, h) => s + getar(t, h, 0.12, 0.3), 0);
  useLayoutEffect(() => {
    const cam = camera as THREE.PerspectiveCamera;
    cam.position.set(pos[0] + g, pos[1] + g * 0.6, pos[2]);
    cam.fov = lerp(a.fov ?? 40, b.fov ?? 40, q);
    cam.updateProjectionMatrix();
    cam.lookAt(lihat[0], lihat[1], lihat[2]);
  });
  return null;
};

/** Teks di permukaan 3D (papan nama) lewat CanvasTexture. */
export const PapanTeks: React.FC<{teks: string; lebar?: number; tinggi?: number; warna?: string; latar?: string; posisi?: V3; rotasi?: V3; ukuranHuruf?: number}> = ({
  teks,
  lebar = 4,
  tinggi = 1,
  warna = '#FFFFFF',
  latar = '#2B176E',
  posisi,
  rotasi,
  ukuranHuruf = 0.62,
}) => {
  const tekstur = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = 1024;
    c.height = Math.round((1024 * tinggi) / lebar);
    const g = c.getContext('2d')!;
    g.fillStyle = latar;
    g.fillRect(0, 0, c.width, c.height);
    g.fillStyle = warna;
    g.font = `800 ${Math.round(c.height * ukuranHuruf)}px RacikJudul, sans-serif`;
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.fillText(teks.toUpperCase(), c.width / 2, c.height / 2 + c.height * 0.04, c.width * 0.92);
    const tx = new THREE.CanvasTexture(c);
    tx.colorSpace = THREE.SRGBColorSpace;
    tx.anisotropy = 8;
    return tx;
  }, [teks, lebar, tinggi, warna, latar, ukuranHuruf]);
  return (
    <group position={posisi} rotation={rotasi}>
      <mesh>
        <boxGeometry args={[lebar + 0.12, tinggi + 0.12, 0.1]} />
        <meshBasicMaterial color={TINTA} />
      </mesh>
      <mesh position={[0, 0, 0.06]}>
        <planeGeometry args={[lebar, tinggi]} />
        <meshBasicMaterial map={tekstur} toneMapped={false} />
      </mesh>
    </group>
  );
};
