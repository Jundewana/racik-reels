// Objek 3D dari bentuk dasar: motor matic + pengendara, garasi rental, bangunan, pin peta, helm, jas hujan.
import React from 'react';
import {useDetik} from '../kit/data';
import {getar, goyang, pop} from '../kit/gerak';
import {Bentuk, PapanTeks, V3} from './dasar';

const KULIT = '#F2C29B';

const Roda: React.FC<{posisi: V3; putar: number}> = ({posisi, putar}) => (
  <group position={posisi} rotation={[putar, 0, 0]}>
    <Bentuk geo={() => <torusGeometry args={[0.3, 0.12, 8, 16]} />} warna="#1E1E24" rotasi={[0, Math.PI / 2, 0]} />
    <Bentuk geo={() => <cylinderGeometry args={[0.18, 0.18, 0.16, 10]} />} warna="#D8D8DE" rotasi={[0, 0, Math.PI / 2]} garis={0.06} />
    <mesh rotation={[0, 0, Math.PI / 2]}>
      <boxGeometry args={[0.04, 0.4, 0.06]} />
      <meshBasicMaterial color="#1E1E24" />
    </mesh>
  </group>
);

/** Pengendara (duduk di motor, menghadap +z). */
export const Pengendara: React.FC<{baju?: string; helm?: string; t?: number}> = ({baju = '#00953F', helm = '#FFC93C', t = 0}) => (
  <group position={[0, 0.95, -0.15]} rotation={[0.12 + goyang(t, 0.03, 2.2), 0, 0]}>
    {/* badan */}
    <Bentuk geo={() => <capsuleGeometry args={[0.28, 0.5, 4, 10]} />} warna={baju} posisi={[0, 0.45, 0]} />
    {/* kaki */}
    <Bentuk geo={() => <capsuleGeometry args={[0.11, 0.55, 4, 8]} />} warna="#2B4C7E" posisi={[0.2, 0.05, 0.35]} rotasi={[Math.PI / 2.4, 0, 0]} />
    <Bentuk geo={() => <capsuleGeometry args={[0.11, 0.55, 4, 8]} />} warna="#2B4C7E" posisi={[-0.2, 0.05, 0.35]} rotasi={[Math.PI / 2.4, 0, 0]} />
    {/* lengan ke setang */}
    <Bentuk geo={() => <capsuleGeometry args={[0.08, 0.6, 4, 8]} />} warna={baju} posisi={[0.28, 0.55, 0.42]} rotasi={[Math.PI / 2.6, 0, 0.15]} />
    <Bentuk geo={() => <capsuleGeometry args={[0.08, 0.6, 4, 8]} />} warna={baju} posisi={[-0.28, 0.55, 0.42]} rotasi={[Math.PI / 2.6, 0, -0.15]} />
    {/* kepala + helm + kaca */}
    <Bentuk geo={() => <sphereGeometry args={[0.26, 16, 12]} />} warna={KULIT} posisi={[0, 1.05, 0.05]} />
    <Bentuk geo={() => <sphereGeometry args={[0.31, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.62]} />} warna={helm} posisi={[0, 1.07, 0.02]} />
    <Bentuk geo={() => <boxGeometry args={[0.42, 0.14, 0.06]} />} warna="#8ED8F8" posisi={[0, 1.08, 0.3]} garis={0.08} />
  </group>
);

/**
 * Motor matic 3D (±2 satuan panjang), menghadap +z. `laju` = putaran roda per detik, `miring` = condong belok (rad).
 */
export const Motor3D: React.FC<{posisi?: V3; yaw?: number; warna?: string; laju?: number; pengendara?: boolean; miring?: number; baju?: string; helm?: string}> = ({
  posisi = [0, 0, 0],
  yaw = 0,
  warna = '#D9261C',
  laju = 0,
  pengendara = false,
  miring = 0,
  baju,
  helm,
}) => {
  const t = useDetik();
  const putar = t * laju * Math.PI * 2;
  const getaran = laju ? Math.abs(goyang(t, 0.02, laju * 0.8)) : 0;
  return (
    <group position={[posisi[0], posisi[1] + getaran, posisi[2]]} rotation={[0, yaw, miring]}>
      <Roda posisi={[0, 0.42, -0.75]} putar={putar} />
      <Roda posisi={[0, 0.42, 0.8]} putar={putar} />
      {/* badan belakang */}
      <Bentuk geo={() => <capsuleGeometry args={[0.36, 0.7, 6, 14]} />} warna={warna} posisi={[0, 0.82, -0.45]} rotasi={[Math.PI / 2, 0, 0]} />
      {/* jok */}
      <Bentuk geo={() => <capsuleGeometry args={[0.22, 0.55, 4, 10]} />} warna="#2A2A30" posisi={[0, 1.13, -0.4]} rotasi={[Math.PI / 2, 0, 0]} />
      {/* dek kaki */}
      <Bentuk geo={() => <boxGeometry args={[0.5, 0.1, 0.65]} />} warna="#3A3A40" posisi={[0, 0.55, 0.22]} />
      {/* pelindung kaki depan */}
      <Bentuk geo={() => <boxGeometry args={[0.55, 0.95, 0.18]} />} warna={warna} posisi={[0, 0.95, 0.62]} rotasi={[-0.28, 0, 0]} />
      {/* garpu & setang */}
      <Bentuk geo={() => <cylinderGeometry args={[0.05, 0.05, 0.9, 6]} />} warna="#9A9AA4" posisi={[0, 0.85, 0.78]} rotasi={[0.3, 0, 0]} />
      <Bentuk geo={() => <cylinderGeometry args={[0.045, 0.045, 0.85, 6]} />} warna="#2A2A30" posisi={[0, 1.45, 0.62]} rotasi={[0, 0, Math.PI / 2]} />
      {/* spakbor + lampu */}
      <Bentuk geo={() => <sphereGeometry args={[0.38, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2]} />} warna={warna} posisi={[0, 0.62, 0.8]} skala={[0.6, 0.55, 1]} />
      <Bentuk geo={() => <sphereGeometry args={[0.13, 12, 10]} />} warna="#FFE27A" posisi={[0, 1.25, 0.76]} emisi="#FFD23F" intensitas={0.6} garis={0.1} />
      <Bentuk geo={() => <boxGeometry args={[0.22, 0.12, 0.06]} />} warna="#D9261C" posisi={[0, 0.85, -1.1]} emisi="#FF3B2F" intensitas={0.5} garis={0.1} />
      {pengendara ? <Pengendara baju={baju} helm={helm} t={t} /> : null}
    </group>
  );
};

/** Garasi rental: bangunan terbuka + kanopi + papan nama + deretan motor. */
export const Garasi: React.FC<{posisi?: V3; yaw?: number; nama?: string; warnaMotor?: string[]}> = ({
  posisi = [0, 0, 0],
  yaw = 0,
  nama = 'Rental Motor',
  warnaMotor = ['#D9261C', '#00953F', '#2B176E'],
}) => (
  <group position={posisi} rotation={[0, yaw, 0]}>
    <Bentuk geo={() => <boxGeometry args={[9, 0.2, 5]} />} warna="#C9C2B6" posisi={[0, 0.1, 0]} garis={0.01} />
    <Bentuk geo={() => <boxGeometry args={[9, 3.6, 0.3]} />} warna="#FFF3DC" posisi={[0, 1.9, -2.4]} garis={0.01} />
    <Bentuk geo={() => <boxGeometry args={[0.3, 3.6, 5]} />} warna="#FFF3DC" posisi={[-4.4, 1.9, 0]} garis={0.015} />
    <Bentuk geo={() => <boxGeometry args={[0.3, 3.6, 5]} />} warna="#FFF3DC" posisi={[4.4, 1.9, 0]} garis={0.015} />
    <Bentuk geo={() => <boxGeometry args={[9.6, 0.3, 6]} />} warna="#2B176E" posisi={[0, 3.85, 0.3]} garis={0.01} />
    {/* kanopi garis-garis */}
    {Array.from({length: 8}, (_, i) => (
      <Bentuk key={i} geo={() => <boxGeometry args={[1.2, 0.08, 1.4]} />} warna={i % 2 ? '#FFFFFF' : '#00953F'} posisi={[-4.2 + i * 1.2, 3.45, 3.0]} rotasi={[0.35, 0, 0]} garis={0.02} />
    ))}
    <PapanTeks teks={nama} lebar={7} tinggi={1.1} posisi={[0, 4.75, 2.7]} latar="#00953F" />
    {warnaMotor.map((w, i) => (
      <Motor3D key={i} posisi={[-2.8 + i * 2.8, 0.2, -0.3]} yaw={0.35} warna={w} />
    ))}
  </group>
);

/** Bangunan sederhana bertuliskan nama (stasiun, penginapan). */
export const Bangunan: React.FC<{posisi: V3; yaw?: number; nama: string; dinding?: string; atap?: string; lebar?: number}> = ({
  posisi,
  yaw = 0,
  nama,
  dinding = '#FFF3DC',
  atap = '#D9261C',
  lebar = 5,
}) => (
  <group position={posisi} rotation={[0, yaw, 0]}>
    <Bentuk geo={() => <boxGeometry args={[lebar, 2.6, 3.4]} />} warna={dinding} posisi={[0, 1.3, 0]} garis={0.015} />
    <Bentuk geo={() => <coneGeometry args={[lebar * 0.78, 1.6, 4]} />} warna={atap} posisi={[0, 3.4, 0]} rotasi={[0, Math.PI / 4, 0]} skala={[1, 1, 0.75]} garis={0.015} />
    <Bentuk geo={() => <boxGeometry args={[0.9, 1.5, 0.1]} />} warna="#FFC93C" posisi={[0, 0.75, 1.72]} garis={0.05} />
    <Bentuk geo={() => <boxGeometry args={[0.8, 0.7, 0.1]} />} warna="#8ED8F8" posisi={[-lebar * 0.3, 1.6, 1.72]} garis={0.05} />
    <Bentuk geo={() => <boxGeometry args={[0.8, 0.7, 0.1]} />} warna="#8ED8F8" posisi={[lebar * 0.3, 1.6, 1.72]} garis={0.05} />
    <PapanTeks teks={nama} lebar={lebar * 0.8} tinggi={0.7} posisi={[0, 2.45, 1.8]} latar="#2B176E" />
  </group>
);

/** Pin peta yang jatuh & memantul di detik `mulai`, dengan papan nama melayang. */
export const Pin3D: React.FC<{posisi: V3; mulai: number; nama: string; warna?: string; skala?: number}> = ({posisi, mulai, nama, warna = '#D9261C', skala = 1}) => {
  const t = useDetik();
  const p = pop(t, mulai, 200, 10);
  if (p <= 0) return null;
  const naik = (1 - Math.min(1, p)) * 6;
  return (
    <group position={[posisi[0], posisi[1] + naik, posisi[2]]} scale={skala * Math.max(0.01, p)}>
      <Bentuk geo={() => <coneGeometry args={[0.55, 1.6, 12]} />} warna={warna} posisi={[0, 0.8, 0]} rotasi={[Math.PI, 0, 0]} />
      <Bentuk geo={() => <sphereGeometry args={[0.75, 16, 12]} />} warna={warna} posisi={[0, 1.9, 0]} />
      <Bentuk geo={() => <sphereGeometry args={[0.3, 12, 10]} />} warna="#FFFFFF" posisi={[0, 1.95, 0.55]} garis={0.08} />
      <PapanTeks teks={nama} lebar={nama.length * 0.42 + 0.8} tinggi={0.9} posisi={[0, 3.5, 0]} latar="#FFFFFF" warna="#0B0B0C" />
    </group>
  );
};

/** Helm 3D (bonus) — berputar pelan, muncul memantul. */
export const Helm3D: React.FC<{posisi: V3; mulai: number; warna?: string; skala?: number}> = ({posisi, mulai, warna = '#D9261C', skala = 1}) => {
  const t = useDetik();
  const p = pop(t, mulai, 220, 11);
  if (p <= 0) return null;
  return (
    <group position={posisi} scale={p * skala} rotation={[0, t * 0.8, 0]}>
      <Bentuk geo={() => <sphereGeometry args={[1, 20, 14, 0, Math.PI * 2, 0, Math.PI * 0.6]} />} warna={warna} />
      <Bentuk geo={() => <boxGeometry args={[1.3, 0.45, 0.2]} />} warna="#8ED8F8" posisi={[0, 0.2, 0.92]} garis={0.06} />
      <Bentuk geo={() => <torusGeometry args={[1, 0.08, 6, 24]} />} warna="#1E1E24" rotasi={[Math.PI / 2, 0, 0]} posisi={[0, 0.02, 0]} />
    </group>
  );
};

/** Jas hujan 3D: badan + tudung, muncul memantul, bergoyang. */
export const JasHujan3D: React.FC<{posisi: V3; mulai: number; warna?: string; skala?: number}> = ({posisi, mulai, warna = '#FFC93C', skala = 1}) => {
  const t = useDetik();
  const p = pop(t, mulai, 220, 11);
  if (p <= 0) return null;
  return (
    <group position={posisi} scale={p * skala} rotation={[0, goyang(t, 0.3, 0.6), goyang(t, 0.05, 1.1)]}>
      <Bentuk geo={() => <coneGeometry args={[1.1, 2.4, 10, 1, true]} />} warna={warna} posisi={[0, 0, 0]} />
      <Bentuk geo={() => <sphereGeometry args={[0.55, 14, 10, 0, Math.PI * 2, 0, Math.PI * 0.6]} />} warna={warna} posisi={[0, 1.25, 0]} />
      <Bentuk geo={() => <capsuleGeometry args={[0.18, 1, 4, 8]} />} warna={warna} posisi={[0.85, 0.2, 0]} rotasi={[0, 0, 0.5]} />
      <Bentuk geo={() => <capsuleGeometry args={[0.18, 1, 4, 8]} />} warna={warna} posisi={[-0.85, 0.2, 0]} rotasi={[0, 0, -0.5]} />
    </group>
  );
};

/** Hentakan kecil untuk objek (getar) — dipakai saat kata penting. */
export const hentakan = (t: number, mulai: number) => getar(t, mulai, 0.15, 0.3);
