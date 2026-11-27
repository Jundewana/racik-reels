// Dunia 3D: tanah, jalan berkelok (jalur bersama untuk motor), gunung (Papandayan berasap), pohon, awan, pantai.
// Semua dari bentuk dasar (tanpa model unduhan), deterministik (tanpa Math.random) agar render stabil.
import React, {useMemo} from 'react';
import * as THREE from 'three';
import {useDetik} from '../kit/data';
import {TINTA} from '../kit/tema';
import {Bentuk, Toon, V3} from './dasar';

/** Jalur jalan utama (x, z) dari dekat kamera menuju pegunungan. */
export const JALUR = new THREE.CatmullRomCurve3(
  [
    [0, 0, 30],
    [3, 0, 15],
    [-2, 0, 0],
    [-6, 0, -18],
    [2, 0, -36],
    [8, 0, -55],
    [2, 0, -80],
    [-4, 0, -110],
  ].map(([x, y, z]) => new THREE.Vector3(x, y, z)),
);

/** Posisi & arah hadap (yaw) di jalur pada u (0..1). */
export const diJalur = (u: number): {pos: V3; yaw: number} => {
  const uu = Math.min(0.999, Math.max(0, u));
  const p = JALUR.getPointAt(uu);
  const d = JALUR.getTangentAt(uu);
  return {pos: [p.x, 0, p.z], yaw: Math.atan2(d.x, d.z)};
};

const acak = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

export const Tanah: React.FC<{warna?: string}> = ({warna = '#6FB24A'}) => (
  <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, -40]} receiveShadow>
    <planeGeometry args={[400, 400]} />
    <Toon warna={warna} />
  </mesh>
);

/** Pita jalan aspal mengikuti JALUR + marka putus-putus kuning. */
export const Jalan: React.FC<{lebar?: number}> = ({lebar = 4.2}) => {
  const {geo, marka} = useMemo(() => {
    const n = 220;
    const pos: number[] = [];
    const idx: number[] = [];
    const marka: {p: V3; yaw: number}[] = [];
    for (let i = 0; i <= n; i++) {
      const u = i / n;
      const p = JALUR.getPointAt(u);
      const d = JALUR.getTangentAt(u);
      const kiri = new THREE.Vector3(-d.z, 0, d.x).multiplyScalar(lebar / 2);
      pos.push(p.x + kiri.x, 0.02, p.z + kiri.z, p.x - kiri.x, 0.02, p.z - kiri.z);
      if (i < n) idx.push(i * 2, i * 2 + 1, i * 2 + 2, i * 2 + 1, i * 2 + 3, i * 2 + 2);
      if (i % 4 === 0) marka.push({p: [p.x, 0.04, p.z], yaw: Math.atan2(d.x, d.z)});
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    return {geo: g, marka};
  }, [lebar]);
  return (
    <group>
      <mesh geometry={geo} receiveShadow>
        <Toon warna="#4A4A55" duaSisi />
      </mesh>
      {marka.map((m, i) => (
        <mesh key={i} position={m.p} rotation={[0, m.yaw, 0]}>
          <boxGeometry args={[0.18, 0.02, 0.9]} />
          <meshBasicMaterial color="#FFD23F" />
        </mesh>
      ))}
    </group>
  );
};

export const Pohon: React.FC<{posisi: V3; s?: number; warna?: string}> = ({posisi, s = 1, warna = '#2F9E55'}) => (
  <group position={posisi} scale={s}>
    <Bentuk geo={() => <cylinderGeometry args={[0.12, 0.16, 1, 6]} />} warna="#8A5A33" posisi={[0, 0.5, 0]} />
    <Bentuk geo={() => <coneGeometry args={[0.8, 1.6, 7]} />} warna={warna} posisi={[0, 1.6, 0]} />
    <Bentuk geo={() => <coneGeometry args={[0.6, 1.2, 7]} />} warna={warna} posisi={[0, 2.3, 0]} />
  </group>
);

/** Pohon tersebar di kiri-kanan jalur (tidak di aspal). */
export const Hutan: React.FC<{jumlah?: number; dari?: number; sampai?: number; bersih?: {p: V3; r: number}[]}> = ({
  jumlah = 60,
  dari = 0,
  sampai = 1,
  bersih = [],
}) => {
  const titik = useMemo(() => {
    const out: {p: V3; s: number; w: string}[] = [];
    for (let i = 0; i < jumlah; i++) {
      const u = dari + (sampai - dari) * acak(i);
      const p = JALUR.getPointAt(u);
      const d = JALUR.getTangentAt(u);
      const sisi = acak(i + 99) > 0.5 ? 1 : -1;
      const jarak = 4.5 + acak(i + 7) * 14;
      const pos: V3 = [p.x - d.z * jarak * sisi, 0, p.z + d.x * jarak * sisi];
      if (bersih.some((b) => Math.hypot(pos[0] - b.p[0], pos[2] - b.p[2]) < b.r)) continue; // jangan halangi kamera
      out.push({p: pos, s: 0.8 + acak(i + 3) * 0.9, w: acak(i + 5) > 0.5 ? '#2F9E55' : '#3DB868'});
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jumlah, dari, sampai, JSON.stringify(bersih)]);
  return (
    <>
      {titik.map((t, i) => (
        <Pohon key={i} posisi={t.p} s={t.s} warna={t.w} />
      ))}
    </>
  );
};

/** Gunung low-poly; `kawah` = puncak terpotong berasap (Papandayan). */
export const Gunung: React.FC<{posisi: V3; tinggi?: number; jari?: number; warna?: string; kawah?: boolean; salju?: boolean}> = ({
  posisi,
  tinggi = 22,
  jari = 18,
  warna = '#6E5BC4',
  kawah = false,
  salju = false,
}) => {
  const t = useDetik();
  return (
    <group position={posisi}>
      <Bentuk
        geo={() => (kawah ? <cylinderGeometry args={[jari * 0.22, jari, tinggi, 9, 1]} /> : <coneGeometry args={[jari, tinggi, 9]} />)}
        warna={warna}
        posisi={[0, tinggi / 2, 0]}
        garis={0.012}
      />
      {salju ? <Bentuk geo={() => <coneGeometry args={[jari * 0.32, tinggi * 0.32, 9]} />} warna="#F5F2FF" posisi={[0, tinggi * 0.84, 0]} garis={0.02} /> : null}
      {kawah
        ? Array.from({length: 7}, (_, i) => {
            const fase = (t * 0.35 + i / 7) % 1;
            const r = 1.2 + fase * 3.5;
            return (
              <mesh key={i} position={[Math.sin(i * 2.1) * 1.2 + fase * 3, tinggi + 1 + fase * 10, Math.cos(i * 1.7) * 1.2]} scale={r}>
                <icosahedronGeometry args={[1, 1]} />
                <meshToonMaterial color="#F4F1F8" transparent opacity={0.85 * (1 - fase)} />
              </mesh>
            );
          })
        : null}
    </group>
  );
};

export const Awan: React.FC<{posisi: V3; s?: number}> = ({posisi, s = 1}) => {
  const t = useDetik();
  return (
    <group position={[posisi[0] + t * 0.6, posisi[1], posisi[2]]} scale={s}>
      {[
        [0, 0, 0, 1.6],
        [1.7, -0.2, 0.2, 1.2],
        [-1.6, -0.3, 0, 1.1],
        [0.6, 0.8, 0, 1.1],
      ].map(([x, y, z, r], i) => (
        <mesh key={i} position={[x, y, z]}>
          <icosahedronGeometry args={[r, 1]} />
          <meshToonMaterial color="#FFFFFF" />
        </mesh>
      ))}
    </group>
  );
};

/** Pegunungan latar khas Garut (Papandayan berasap di tengah). */
export const Pegunungan: React.FC = () => (
  <>
    <Gunung posisi={[-40, 0, -150]} tinggi={34} jari={30} warna="#7D6FC9" />
    <Gunung posisi={[10, 0, -170]} tinggi={44} jari={34} warna="#6E5BC4" kawah />
    <Gunung posisi={[60, 0, -150]} tinggi={30} jari={28} warna="#8A7ED0" salju />
    <Gunung posisi={[-80, 0, -120]} tinggi={22} jari={22} warna="#9A8FDA" />
    <Awan posisi={[-30, 30, -120]} s={2.2} />
    <Awan posisi={[25, 36, -130]} s={2.6} />
    <Awan posisi={[50, 26, -100]} s={1.8} />
  </>
);

/** Pantai (Sayang Heulang): pasir, laut, karang. */
export const Pantai: React.FC<{posisi: V3}> = ({posisi}) => {
  const t = useDetik();
  return (
    <group position={posisi}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]} receiveShadow>
        <circleGeometry args={[7, 24]} />
        <Toon warna="#F2D58A" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.06 + Math.sin(t * 2) * 0.03, 4]}>
        <circleGeometry args={[6, 24, Math.PI * 0.05, Math.PI * 0.9]} />
        <Toon warna="#3FA7D6" />
      </mesh>
      <Bentuk geo={() => <dodecahedronGeometry args={[1.1, 0]} />} warna="#7A7A86" posisi={[2.5, 0.5, 3]} />
      <Bentuk geo={() => <dodecahedronGeometry args={[0.7, 0]} />} warna="#8A8A96" posisi={[-2, 0.35, 4]} />
    </group>
  );
};

/** Titik di samping jalur (jarak + ke kanan arah jalan) yang menghadap ke jalan. */
export const sampingJalur = (u: number, jarak: number): {pos: V3; yaw: number} => {
  const p = JALUR.getPointAt(u);
  const d = JALUR.getTangentAt(u);
  const kanan = new THREE.Vector3(-d.z, 0, d.x);
  const pos: V3 = [p.x + kanan.x * jarak, 0, p.z + kanan.z * jarak];
  return {pos, yaw: Math.atan2(-kanan.x * Math.sign(jarak), -kanan.z * Math.sign(jarak))};
};

/** Diorama peta (meja pulau) untuk destinasi: kota, gunung berasap, kawah uap, pantai. Pusat di `posisi`. */
export const Diorama: React.FC<{posisi: V3}> = ({posisi}) => (
  <group position={posisi}>
    <Bentuk geo={() => <cylinderGeometry args={[16, 17, 2, 28]} />} warna="#6FB24A" posisi={[0, -1, 0]} garis={0.01} />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 9]}>
      <circleGeometry args={[9, 28, Math.PI * 0.08, Math.PI * 0.84]} />
      <Toon warna="#3FA7D6" />
    </mesh>
    <Gunung posisi={[-7, 0, -6]} tinggi={7} jari={5} warna="#7D6FC9" kawah />
    <Gunung posisi={[-9, 0, 4]} tinggi={5} jari={4} warna="#8A7ED0" />
    <Gunung posisi={[2, 0, -10]} tinggi={4} jari={4} warna="#9A8FDA" />
  </group>
);

/** Garis tepi hitam tipis untuk objek datar yang tidak memakai Bentuk. */
export const warnaTinta = () => TINTA;
