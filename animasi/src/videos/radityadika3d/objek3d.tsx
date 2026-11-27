// Objek 3D khas video "radityadika3d" (tips bertahan jadi YouTuber gaming): kreator generik ber-headset, meja podcast,
// gamepad raksasa, tangga video ▶ (konsisten = satu anak tangga per video), menara piala, awan hujan / matahari (mood),
// konsol bercahaya di tengah sirkel, panah boost, konfeti. Warna hanya dari token kit (WARNA/TINTA) agar ikut gaya.
import React from 'react';
import * as THREE from 'three';
import {useDetik} from '../../kit/data';
import {goyang, lerp, pop} from '../../kit/gerak';
import {TINTA, WARNA} from '../../kit/tema';
import {Bentuk, V3} from '../../kit3d';

const lum = (hex: string) => {
  const c = new THREE.Color(hex);
  return 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;
};
/** Warna tergelap / terterang di antara tinta & "putih" gaya aktif (mata, ikon di atas permukaan berwarna). */
export const gelap = () => (lum(TINTA) < lum(WARNA.putih) ? TINTA : WARNA.putih);
export const terang = () => (lum(TINTA) < lum(WARNA.putih) ? WARNA.putih : TINTA);
/** Gaya berlatar gelap (grainy-gradient, neon-malam) → dunia malam bercahaya. */
export const gayaGelap = () => lum(WARNA.krem) < 0.3;

export const halus = (x: number) => {
  const c = Math.min(1, Math.max(0, x));
  return c * c * c * (c * (c * 6 - 15) + 10);
};
const acak = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

// ------------------------------------------------------------------ kreator (tokoh generik, bukan karikatur)
export type PoseKreator = {
  duduk?: boolean;
  /** fase langkah (rad); undefined = diam */
  langkah?: number;
  /** 0..1 lengan terangkat (sorak) */
  sorak?: number;
  /** tinggi lompatan (satuan) */
  lompat?: number;
  /** lengan di atas meja (podcast) */
  diMeja?: boolean;
};

export const Kreator3D: React.FC<{
  posisi: V3;
  yaw?: number;
  baju: string;
  rambut?: string;
  aksen?: string;
  skala?: number;
  pose?: PoseKreator;
  fase?: number;
}> = ({posisi, yaw = 0, baju, rambut, aksen, skala = 1, pose = {}, fase = 0}) => {
  const t = useDetik();
  const {duduk = false, langkah, sorak = 0, lompat = 0, diMeja = false} = pose;
  const ayun = langkah !== undefined ? Math.sin(langkah) * 0.65 : 0;
  const napas = goyang(t, 0.02, 0.5, fase);
  const turun = duduk ? -0.42 : 0;
  const celana = WARNA.abu;
  const warnaRambut = rambut ?? gelap();
  const warnaAksen = aksen ?? WARNA.kuning;
  return (
    <group position={[posisi[0], posisi[1] + lompat, posisi[2]]} rotation={[0, yaw, 0]} scale={skala}>
      <group position={[0, turun, 0]}>
        {/* kaki: paha (+ betis saat duduk) */}
        {[-1, 1].map((s) => (
          <group key={s} position={[0.16 * s, 0.78, 0]} rotation={[duduk ? -Math.PI / 2 : ayun * s, 0, 0]}>
            <Bentuk geo={() => <capsuleGeometry args={[0.13, 0.42, 4, 8]} />} warna={celana} posisi={[0, -0.36, 0]} garis={0.07} />
          </group>
        ))}
        {duduk
          ? [-1, 1].map((s) => (
              <Bentuk key={s} geo={() => <capsuleGeometry args={[0.12, 0.3, 4, 8]} />} warna={celana} posisi={[0.16 * s, 0.5, 0.62]} garis={0.07} />
            ))
          : null}
        {/* badan */}
        <Bentuk geo={() => <capsuleGeometry args={[0.31, 0.42, 6, 12]} />} warna={baju} posisi={[0, 1.13 + napas, 0]} garis={0.06} />
        {/* lengan */}
        {[-1, 1].map((s) => {
          const rx = diMeja ? -1.15 + goyang(t, 0.12, 0.7, fase + s) : -ayun * s;
          const rz = s * lerp(0.12, 2.7, sorak) + (sorak > 0 ? goyang(t, 0.25 * sorak, 1.6, fase + s * 0.3) : 0);
          return (
            <group key={s} position={[0.4 * s, 1.36 + napas, 0]} rotation={[rx, 0, rz]}>
              <Bentuk geo={() => <capsuleGeometry args={[0.09, 0.46, 4, 8]} />} warna={baju} posisi={[0, -0.3, 0]} garis={0.08} />
              <Bentuk geo={() => <sphereGeometry args={[0.11, 10, 8]} />} warna={WARNA.kulit} posisi={[0, -0.62, 0]} garis={0.08} />
            </group>
          );
        })}
        {/* kepala */}
        <group position={[0, 1.88 + napas, 0]} rotation={[goyang(t, 0.04, 0.6, fase), goyang(t, 0.12, 0.35, fase), 0]}>
          <Bentuk geo={() => <sphereGeometry args={[0.34, 18, 14]} />} warna={WARNA.kulit} garis={0.06} />
          <Bentuk geo={() => <sphereGeometry args={[0.36, 18, 12, 0, Math.PI * 2, 0, Math.PI * 0.5]} />} warna={warnaRambut} posisi={[0, 0.04, -0.03]} rotasi={[-0.35, 0, 0]} garis={0.04} />
          {[-1, 1].map((s) => (
            <mesh key={s} position={[0.12 * s, 0.02, 0.31]}>
              <sphereGeometry args={[0.05, 8, 6]} />
              <meshBasicMaterial color={gelap()} />
            </mesh>
          ))}
          <mesh position={[0, -0.12, 0.3]} rotation={[0, 0, Math.PI]}>
            <torusGeometry args={[0.08, 0.018, 4, 10, Math.PI]} />
            <meshBasicMaterial color={gelap()} />
          </mesh>
          {/* headset gaming */}
          <Bentuk geo={() => <torusGeometry args={[0.38, 0.045, 6, 18, Math.PI]} />} warna={warnaAksen} posisi={[0, 0.02, 0]} garis={0.12} />
          {[-1, 1].map((s) => (
            <Bentuk key={s} geo={() => <cylinderGeometry args={[0.13, 0.13, 0.12, 14]} />} warna={warnaAksen} posisi={[0.37 * s, 0, 0]} rotasi={[0, 0, Math.PI / 2]} garis={0.1} />
          ))}
          <Bentuk geo={() => <capsuleGeometry args={[0.025, 0.32, 3, 6]} />} warna={warnaAksen} posisi={[-0.32, -0.12, 0.18]} rotasi={[1.2, 0.5, 0]} garis={0.15} />
        </group>
      </group>
    </group>
  );
};

// ------------------------------------------------------------------ meja podcast
export const MejaPodcast: React.FC<{posisi: V3; kursi: number[]}> = ({posisi, kursi}) => (
  <group position={posisi}>
    <Bentuk geo={() => <cylinderGeometry args={[1.5, 1.5, 0.14, 32]} />} warna={WARNA.ungu} posisi={[0, 0.92, 0]} garis={0.04} />
    <Bentuk geo={() => <cylinderGeometry args={[0.18, 0.4, 0.86, 12]} />} warna={WARNA.abu} posisi={[0, 0.43, 0]} garis={0.05} />
    {kursi.map((a) => (
      <group key={a}>
        {/* bangku */}
        <Bentuk geo={() => <cylinderGeometry args={[0.38, 0.32, 0.42, 14]} />} warna={WARNA.merah} posisi={[Math.sin(a) * 2.3, 0.21, Math.cos(a) * 2.3]} garis={0.05} />
        {/* mikrofon menghadap kursi */}
        <group position={[Math.sin(a) * 1.05, 0.99, Math.cos(a) * 1.05]} rotation={[0, a, 0]}>
          <Bentuk geo={() => <cylinderGeometry args={[0.025, 0.025, 0.5, 6]} />} warna={WARNA.abu} posisi={[0, 0.25, 0]} rotasi={[0.5, 0, 0]} garis={0.2} />
          <Bentuk geo={() => <capsuleGeometry args={[0.09, 0.16, 4, 10]} />} warna={gelap()} posisi={[0, 0.48, 0.14]} rotasi={[1.1, 0, 0]} garis={0.1} />
        </group>
      </group>
    ))}
  </group>
);

// ------------------------------------------------------------------ gamepad raksasa (gerbang "dunia gaming")
export const Gamepad3D: React.FC<{posisi: V3; yaw?: number; skala?: number; mulai: number}> = ({posisi, yaw = 0, skala = 1, mulai}) => {
  const t = useDetik();
  const p = pop(t, mulai, 160, 10);
  if (p <= 0) return null;
  const tombol: [string, number, number][] = [
    [WARNA.hijau, 1.55, 0.45],
    [WARNA.merah, 1.95, 0.05],
    [WARNA.kuning, 1.15, 0.05],
    [WARNA.langit, 1.55, -0.35],
  ];
  return (
    <group position={posisi} rotation={[0, yaw, 0]} scale={skala * p}>
      {/* tiang penyangga */}
      <Bentuk geo={() => <cylinderGeometry args={[0.35, 0.6, 2.2, 10]} />} warna={WARNA.abu} posisi={[0, 1.1, -0.3]} garis={0.04} />
      <group position={[0, 3.2 + goyang(t, 0.12, 0.4), 0]} rotation={[-0.25, goyang(t, 0.12, 0.25), goyang(t, 0.04, 0.3)]}>
        {/* badan & dua pegangan */}
        <Bentuk geo={() => <capsuleGeometry args={[1, 2.4, 8, 18]} />} warna={WARNA.ungu} rotasi={[0, 0, Math.PI / 2]} skala={[1, 1, 0.55]} garis={0.03} />
        {[-1, 1].map((s) => (
          <Bentuk key={s} geo={() => <capsuleGeometry args={[0.75, 1.2, 8, 14]} />} warna={WARNA.ungu} posisi={[1.75 * s, -0.75, 0]} rotasi={[0, 0, -0.45 * s]} skala={[1, 1, 0.6]} garis={0.03} />
        ))}
        {/* d-pad */}
        <Bentuk geo={() => <boxGeometry args={[0.95, 0.3, 0.2]} />} warna={gelap()} posisi={[-1.55, 0.05, 0.55]} garis={0.06} />
        <Bentuk geo={() => <boxGeometry args={[0.3, 0.95, 0.2]} />} warna={gelap()} posisi={[-1.55, 0.05, 0.55]} garis={0.06} />
        {/* tombol menyala bergiliran */}
        {tombol.map(([w, x, y], i) => {
          const nyala = Math.max(0, Math.sin(t * 3 - i * 1.4));
          return <Bentuk key={i} geo={() => <sphereGeometry args={[0.24, 14, 10]} />} warna={w} posisi={[x, y, 0.5]} skala={[1, 1, 0.6]} emisi={w} intensitas={0.2 + nyala * 0.8} garis={0.08} />;
        })}
        {/* dua stik analog */}
        {[-0.6, 0.6].map((x) => (
          <Bentuk key={x} geo={() => <cylinderGeometry args={[0.3, 0.32, 0.25, 16]} />} warna={gelap()} posisi={[x, -0.45, 0.48]} rotasi={[Math.PI / 2, 0, 0]} garis={0.06} />
        ))}
      </group>
    </group>
  );
};

// ------------------------------------------------------------------ tangga video (konsisten)
export const TANGGA = {z0: -18, panjang: 1.6, naik: 0.55, n: 20, lebar: 2.8};
/** Tinggi permukaan anak tangga i (i = -1 → tanah). */
export const atasTangga = (i: number) => TANGGA.naik * (i + 1);
/** Titik tengah (z) anak tangga i. */
export const zTangga = (i: number) => TANGGA.z0 - TANGGA.panjang * i;
const WARNA_ANAK = (i: number) => [WARNA.merah, WARNA.ungu, WARNA.kuning, WARNA.hijau][i % 4];

let segitiga: THREE.Shape | null = null;
const bentukPlay = () => {
  if (!segitiga) {
    segitiga = new THREE.Shape();
    segitiga.moveTo(-0.22, -0.26);
    segitiga.lineTo(0.3, 0);
    segitiga.lineTo(-0.22, 0.26);
    segitiga.closePath();
  }
  return segitiga;
};

/** Ikon play timbul (menghadap +x) — satu video di sisi anak tangga. */
const IkonPlay: React.FC<{posisi: V3; warna: string}> = ({posisi, warna}) => (
  <group position={posisi} rotation={[0, Math.PI / 2, 0]}>
    <mesh>
      <extrudeGeometry args={[bentukPlay(), {depth: 0.06, bevelEnabled: false}]} />
      <meshBasicMaterial color={warna} />
    </mesh>
  </group>
);

/** Anak tangga = video; muncul (tumbuh dari tanah) di detik muncul(i). Menara piala di puncak selalu ada. */
export const TanggaVideo: React.FC<{muncul: (i: number) => number; menaraMulai: number}> = ({muncul, menaraMulai}) => {
  const t = useDetik();
  const {n, lebar, panjang} = TANGGA;
  const tinggiMenara = atasTangga(n);
  const pm = pop(t, menaraMulai, 140, 12);
  return (
    <group>
      {Array.from({length: n}, (_, i) => {
        const p = pop(t, muncul(i), 220, 13);
        if (p <= 0) return null;
        const h = atasTangga(i);
        return (
          <group key={i} position={[0, 0, zTangga(i)]} scale={[1, Math.max(0.01, p), 1]}>
            <Bentuk geo={() => <boxGeometry args={[lebar, h, panjang]} />} warna={WARNA_ANAK(i)} posisi={[0, h / 2, 0]} garis={0.012} />
            <IkonPlay posisi={[lebar / 2 + 0.02, h - 0.28, 0]} warna={terang()} />
          </group>
        );
      })}
      {pm > 0 ? (
        <group position={[0, 0, zTangga(n) - 1.8]} scale={[1, Math.max(0.01, pm), 1]}>
          <Bentuk geo={() => <boxGeometry args={[6, tinggiMenara, 5.2]} />} warna={WARNA.ungu} posisi={[0, tinggiMenara / 2, 0]} garis={0.008} />
          <Bentuk geo={() => <boxGeometry args={[6.3, 0.3, 5.5]} />} warna={WARNA.kuning} posisi={[0, tinggiMenara - 0.1, 0]} garis={0.02} />
        </group>
      ) : null}
    </group>
  );
};

// ------------------------------------------------------------------ piala
export const Piala3D: React.FC<{posisi: V3; skala?: number; nyala?: number}> = ({posisi, skala = 1, nyala = 0.2}) => {
  const t = useDetik();
  return (
    <group position={posisi} scale={skala} rotation={[0, t * 0.6, 0]}>
      <Bentuk geo={() => <boxGeometry args={[1.1, 0.3, 1.1]} />} warna={WARNA.abu} posisi={[0, 0.15, 0]} garis={0.05} />
      <Bentuk geo={() => <cylinderGeometry args={[0.14, 0.22, 0.6, 10]} />} warna={WARNA.kuning} posisi={[0, 0.6, 0]} emisi={WARNA.kuning} intensitas={nyala} garis={0.06} />
      <Bentuk geo={() => <cylinderGeometry args={[0.75, 0.3, 1.1, 20]} />} warna={WARNA.kuning} posisi={[0, 1.45, 0]} emisi={WARNA.kuning} intensitas={nyala} garis={0.04} />
      {[-1, 1].map((s) => (
        <Bentuk key={s} geo={() => <torusGeometry args={[0.3, 0.07, 6, 14, Math.PI]} />} warna={WARNA.kuning} posisi={[0.72 * s, 1.5, 0]} rotasi={[0, 0, -s * Math.PI / 2]} garis={0.12} />
      ))}
      <Bentuk geo={() => <octahedronGeometry args={[0.3, 0]} />} warna={WARNA.kuning} posisi={[0, 2.35 + goyang(t, 0.1, 0.8), 0]} rotasi={[0, t * 2, 0]} emisi={WARNA.kuning} intensitas={0.4 + nyala} garis={0.1} />
    </group>
  );
};

// ------------------------------------------------------------------ mood: awan hujan & matahari
export const AwanHujan: React.FC<{posisi: V3; kuat: number}> = ({posisi, kuat}) => {
  const t = useDetik();
  if (kuat <= 0.01) return null;
  return (
    <group position={posisi} scale={kuat}>
      {[
        [0, 0, 0, 1.1],
        [1.1, -0.15, 0.2, 0.85],
        [-1.1, -0.2, 0, 0.8],
        [0.4, 0.55, -0.1, 0.8],
      ].map(([x, y, z, r], i) => (
        <Bentuk key={i} geo={() => <icosahedronGeometry args={[r, 1]} />} warna={WARNA.abu} posisi={[x + goyang(t, 0.06, 0.5, i), y, z]} garis={0.04} />
      ))}
      {Array.from({length: 16}, (_, i) => {
        const f = (t * 1.8 + acak(i)) % 1;
        return (
          <mesh key={i} position={[(acak(i + 20) - 0.5) * 2.6, -0.6 - f * 3.2, (acak(i + 40) - 0.5) * 1.6]}>
            <capsuleGeometry args={[0.035, 0.28, 2, 4]} />
            <meshBasicMaterial color={WARNA.langit} transparent opacity={1 - f * 0.6} />
          </mesh>
        );
      })}
    </group>
  );
};

export const Matahari: React.FC<{posisi: V3; kuat: number}> = ({posisi, kuat}) => {
  const t = useDetik();
  if (kuat <= 0.01) return null;
  return (
    <group position={posisi} scale={kuat} rotation={[0, 0, t * 0.8]}>
      <Bentuk geo={() => <sphereGeometry args={[0.75, 18, 14]} />} warna={WARNA.kuning} emisi={WARNA.kuning} intensitas={0.7} garis={0.06} />
      {Array.from({length: 8}, (_, i) => {
        const a = (i / 8) * Math.PI * 2;
        return <Bentuk key={i} geo={() => <boxGeometry args={[0.16, 0.5, 0.16]} />} warna={WARNA.kuning} posisi={[Math.sin(a) * 1.15, Math.cos(a) * 1.15, 0]} rotasi={[0, 0, -a]} emisi={WARNA.kuning} intensitas={0.6} garis={0.1} />;
      })}
    </group>
  );
};

// ------------------------------------------------------------------ sirkel: konsol bercahaya, panah boost, konfeti
export const KonsolSirkel: React.FC<{posisi: V3; kuat: number}> = ({posisi, kuat}) => {
  const t = useDetik();
  return (
    <group position={posisi}>
      <Bentuk geo={() => <cylinderGeometry args={[0.9, 1.1, 0.6, 16]} />} warna={WARNA.abu} posisi={[0, 0.3, 0]} garis={0.04} />
      <Bentuk
        geo={() => <octahedronGeometry args={[0.7, 0]} />}
        warna={WARNA.hijau}
        posisi={[0, 1.6 + goyang(t, 0.15, 0.5), 0]}
        rotasi={[0, t * 1.2, 0]}
        skala={0.8 + kuat * 0.4}
        emisi={WARNA.hijau}
        intensitas={0.3 + kuat * 0.7}
        garis={0.06}
      />
      <Bentuk geo={() => <torusGeometry args={[1.1, 0.06, 6, 28]} />} warna={WARNA.kuning} posisi={[0, 1.6, 0]} rotasi={[Math.PI / 2 + goyang(t, 0.3, 0.3), t * 0.7, 0]} emisi={WARNA.kuning} intensitas={0.5} garis={0.12} />
      <pointLight position={[0, 2.2, 0]} color={WARNA.hijau} intensity={8 + kuat * 30} distance={18} decay={1.6} />
    </group>
  );
};

/** Panah naik berulang di sekitar `posisi` mulai `mulai` (kena boost). */
export const PanahBoost: React.FC<{posisi: V3; mulai: number; lama?: number}> = ({posisi, mulai, lama = 2.2}) => {
  const t = useDetik();
  const d = t - mulai;
  if (d < 0 || d > lama) return null;
  return (
    <group position={posisi}>
      {Array.from({length: 5}, (_, i) => {
        const f = (d * 1.4 + i / 5) % 1;
        const a = (i / 5) * Math.PI * 2 + 0.4;
        const s = Math.sin(Math.PI * f) * 0.9;
        return (
          <Bentuk key={i} geo={() => <coneGeometry args={[0.22, 0.5, 8]} />} warna={WARNA.hijau} posisi={[Math.sin(a) * 1.1, 0.3 + f * 3.4, Math.cos(a) * 1.1]} skala={Math.max(0.01, s)} emisi={WARNA.hijau} intensitas={0.6} garis={0.1} />
        );
      })}
    </group>
  );
};

export const Konfeti: React.FC<{pusat: V3; mulai: number; luas?: number; jumlah?: number}> = ({pusat, mulai, luas = 18, jumlah = 70}) => {
  const t = useDetik();
  const d = t - mulai;
  if (d < 0) return null;
  const warnaK = [WARNA.merah, WARNA.kuning, WARNA.hijau, WARNA.ungu, WARNA.langit];
  return (
    <group position={pusat}>
      {Array.from({length: jumlah}, (_, i) => {
        const jatuh = (d * (1.6 + acak(i) * 1.4) + acak(i + 7) * 10) % 10;
        return (
          <mesh
            key={i}
            position={[(acak(i + 3) - 0.5) * luas + goyang(t, 0.3, 0.7, i), 11 - jatuh, (acak(i + 11) - 0.5) * luas]}
            rotation={[t * (2 + acak(i) * 3), t * 2.4 + i, 0]}
            scale={Math.min(1, d * 3)}
          >
            <boxGeometry args={[0.28, 0.16, 0.03]} />
            <meshBasicMaterial color={warnaK[i % warnaK.length]} side={THREE.DoubleSide} />
          </mesh>
        );
      })}
    </group>
  );
};

/** Gumpalan cahaya jauh di langit (nuansa gradien) — warna dari palet gaya. */
export const GumpalanLangit: React.FC = () => {
  const t = useDetik();
  const g: [V3, number, string][] = [
    [[-70, 40, -170], 22, WARNA.ungu],
    [[60, 55, -190], 26, WARNA.merah],
    [[140, 35, -120], 20, WARNA.hijau],
    [[10, 70, -230], 18, WARNA.kuning],
  ];
  return (
    <>
      {g.map(([p, r, w], i) => (
        <mesh key={i} position={[p[0] + goyang(t, 3, 0.03, i), p[1] + goyang(t, 2, 0.04, i + 1), p[2]]}>
          <sphereGeometry args={[r, 24, 16]} />
          <meshBasicMaterial color={w} transparent opacity={0.55} fog={false} />
        </mesh>
      ))}
    </>
  );
};
