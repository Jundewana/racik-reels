// Promo Rental Motor versi 3D — SATU dunia, SATU kamera yang terus bergerak (prinsip anti-PPT bang-motion):
// tidak ada potongan per kalimat; kamera meluncur dari momen ke momen, motor (hero) hadir sebagian besar durasi,
// teks huruf kalimat dengan posisi bergantian, sapuan hanya 2×, light leak hanya 1 momen (senja penutup).
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Adegan, Cap, CtaWA, GarisLaju, Judul, Label, Sapuan, useData, useDetik, waktuKata, waktuTiapKata} from '../../kit';
import {lerp, pop} from '../../kit/gerak';
import {KilauCahaya} from '../../kit/Sinematik';
import {
  Bangunan,
  Bentuk,
  diJalur,
  Diorama,
  Garasi,
  Helm3D,
  Hutan,
  JasHujan3D,
  Jalan,
  Kamera3D,
  Motor3D,
  PapanTeks,
  Panggung3D,
  Pegunungan,
  Pin3D,
  sampingJalur,
  Tanah,
  V3,
} from '../../kit3d';

const tambah = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
/** Titik di depan (arah hadap yaw) sejauh `jarak`, setinggi `tinggi`, digeser ke samping `samping`. */
const depan = (pos: V3, yaw: number, jarak: number, tinggi: number, samping = 0): V3 => [
  pos[0] + Math.sin(yaw) * jarak + Math.cos(yaw) * samping,
  pos[1] + tinggi,
  pos[2] + Math.cos(yaw) * jarak - Math.sin(yaw) * samping,
];
const campurV = (a: V3, b: V3, q: number): V3 => [lerp(a[0], b[0], q), lerp(a[1], b[1], q), lerp(a[2], b[2], q)];
const halus = (x: number) => {
  const c = Math.min(1, Math.max(0, x));
  return c * c * c * (c * (c * 6 - 15) + 10);
};

const GARASI = sampingJalur(0.2, 10);
const PODIUM = depan(GARASI.pos, GARASI.yaw, 5, 0);
// parkir hero di samping garasi (bukan di antara kamera & meja putar)
const PARKIR = {pos: depan(sampingJalur(0.2, 10).pos, sampingJalur(0.2, 10).yaw, 2.5, 0, 7), yaw: 0};
const DIORAMA: V3 = [220, 0, 0];
const SIMPANG = diJalur(0.105);
const BERSIH = [
  {p: SIMPANG.pos, r: 12},
  {p: GARASI.pos, r: 22},
  ...[10, 18, 26, 34].map((d) => ({p: [GARASI.pos[0] + Math.sin(GARASI.yaw) * d, 0, GARASI.pos[2] + Math.cos(GARASI.yaw) * d] as V3, r: 9})),
];

type Kam = {pos: V3; lihat: V3; fov: number};
type Hero = {pos: V3; yaw: number; laju: number; tampil: boolean};

/** Papan arah bertanda tanya (pusing transportasi). */
const PapanTanya: React.FC<{posisi: V3; yaw: number; mulai: number}> = ({posisi, yaw, mulai}) => {
  const t = useDetik();
  const p = pop(t, mulai, 200, 10);
  if (p <= 0) return null;
  return (
    <group position={posisi} rotation={[0, yaw + Math.sin(t * 3 + posisi[0]) * 0.25, 0]} scale={p}>
      <Bentuk geo={() => <cylinderGeometry args={[0.08, 0.08, 2.6, 6]} />} warna="#8A5A33" posisi={[0, 1.3, 0]} />
      <PapanTeks teks="?" lebar={1.4} tinggi={0.9} posisi={[0, 2.5, 0]} latar="#FFC93C" warna="#0B0B0C" ukuranHuruf={0.8} />
    </group>
  );
};

export const RentalGarut3D: React.FC = () => {
  const data = useData();
  const t = useDetik();
  const W = (teks: string, setelah = 0) => waktuKata(data, teks, setelah);

  // batas momen (bukan potongan: kamera meluncur di sini)
  const s2 = W('tapi') - 0.08;
  const s3 = W('sewa') - 0.1;
  const s4 = W('motor', W('satu')) - 0.2;
  const s5 = W('harian') - 0.08;
  const s6 = W('mau ke Papandayan') - 0.2;
  const s7 = W('tinggal');
  const s8 = W('bebas') - 0.1;
  const s9 = W('harga') - 0.06;
  const s10 = W('helm') - 0.02;
  const s10b = W('bisa', s10) - 0.08;
  const s11 = W('booking') - 0.25;
  const s12 = W('Garut', W('layar')) - 0.05;
  const gas = W('gas');

  /** Motor hero per momen (posisi menyambung antar momen bila memungkinkan). */
  const hero = (x: number): Hero => {
    if (x < s2) {
      const m = diJalur(0.17 - 0.03 * x);
      return {pos: m.pos, yaw: m.yaw + Math.PI, laju: 2.2, tampil: true};
    }
    if (x < s3) return {pos: SIMPANG.pos, yaw: SIMPANG.yaw + Math.PI, laju: 0, tampil: true};
    if (x < s4) {
      // berbalik & melaju ke garasi, berhenti di parkiran depan garasi
      const q = halus((x - s3) / (s4 - s3 - 0.4));
      const m = diJalur(lerp(0.105, 0.19, q));
      return {pos: campurV(m.pos, PARKIR.pos, halus((q - 0.8) / 0.2)), yaw: m.yaw, laju: q < 1 ? 2.4 : 0, tampil: true};
    }
    if (x < s7) return {pos: PARKIR.pos, yaw: GARASI.yaw + 0.5, laju: 0, tampil: true};
    if (x < s9) {
      const u = x < s8 ? 0.28 + (x - s7) * 0.045 : 0.28 + (s8 - s7) * 0.045 + (x - s8) * 0.02;
      const m = diJalur(u);
      return {pos: m.pos, yaw: m.yaw, laju: x < s8 ? 5 : 3, tampil: true};
    }
    if (x < s10b) return {pos: PARKIR.pos, yaw: GARASI.yaw + 0.5, laju: 0, tampil: true};
    if (x < s11) {
      const m = diJalur(0.5 + (x - s10b) * 0.04);
      return {pos: m.pos, yaw: m.yaw, laju: 3, tampil: true};
    }
    if (x < s12) return {pos: PARKIR.pos, yaw: GARASI.yaw + 0.5, laju: 0, tampil: true};
    const m = diJalur(0.68 + (x - s12) * 0.025);
    return {pos: m.pos, yaw: m.yaw, laju: 3, tampil: true};
  };

  /** Kamera per momen (fungsi waktu). */
  const kamera = (x: number): Kam => {
    const h = hero(x);
    if (x < s2) return {pos: depan(h.pos, h.yaw, 7 - x * 0.6, 1.3 + x * 0.15, 1.2), lihat: tambah(h.pos, [0, 1.6, 0]), fov: 42};
    if (x < s3) {
      const a = 0.9 + (x - s2) * 0.45;
      return {pos: [SIMPANG.pos[0] + Math.sin(a) * 7.5, 2.4, SIMPANG.pos[2] + Math.cos(a) * 7.5], lihat: tambah(SIMPANG.pos, [0, 1.4, 0]), fov: 45};
    }
    if (x < s4) {
      const q = halus((x - s3) / (s4 - s3));
      return {
        pos: campurV(depan(h.pos, h.yaw, -7, 3, 2), depan(GARASI.pos, GARASI.yaw, 26, 3.4), q),
        lihat: campurV(tambah(h.pos, [0, 1.2, 0]), tambah(GARASI.pos, [0, 3.4, 0]), q),
        fov: 42,
      };
    }
    if (x < s5) {
      const q = (x - s4) / (s5 - s4);
      return {pos: depan(PODIUM, GARASI.yaw, lerp(12, 10, q), lerp(2.2, 2.6, q), q * 0.8), lihat: tambah(PODIUM, [0, -0.6, 0]), fov: 40};
    }
    if (x < s6) {
      const q = halus((x - s5) / (s6 - s5));
      return {pos: depan(GARASI.pos, GARASI.yaw, 10, 2.6, lerp(-4, 4, q)), lihat: depan(GARASI.pos, GARASI.yaw, 0, 1.2, lerp(-2, 2, q)), fov: 42};
    }
    if (x < s7) {
      const a = lerp(0.2, 0.75, (x - s6) / (s7 - s6));
      return {pos: tambah(DIORAMA, [Math.sin(a) * 32, 24, Math.cos(a) * 32]), lihat: tambah(DIORAMA, [0, 1, 0]), fov: 40};
    }
    if (x < s8) return {pos: depan(h.pos, h.yaw, -6.5, 2.4, 0.6), lihat: depan(h.pos, h.yaw, 6, 1.2), fov: 60};
    if (x < s9) return {pos: depan(h.pos, h.yaw, 5, 3.4, 2.4), lihat: tambah(h.pos, [0, 1.2, 0]), fov: 50};
    if (x < s10) {
      const q = (x - s9) / (s10 - s9);
      return {pos: depan(GARASI.pos, GARASI.yaw, lerp(28, 24, q), lerp(7, 5.5, q), lerp(-3, 2, q)), lihat: tambah(GARASI.pos, [0, 1, 0]), fov: 40};
    }
    if (x < s10b) {
      const q = (x - s10) / (s10b - s10);
      return {pos: depan(PODIUM, GARASI.yaw, lerp(12, 10.5, q), 3.2, q * 0.6), lihat: tambah(PODIUM, [0, 1.4, 0]), fov: 38};
    }
    if (x < s11) return {pos: depan(h.pos, h.yaw, -8, 5, -5), lihat: depan(h.pos, h.yaw, 4, 1), fov: 48};
    if (x < s12) return {pos: depan(GARASI.pos, GARASI.yaw + (x - s11) * 0.06, 20, 4.5), lihat: tambah(GARASI.pos, [0, 2.4, 0]), fov: 40};
    return {pos: depan(h.pos, h.yaw, -7 - (x - s12) * 0.8, 2 + (x - s12) * 0.9, 1.5), lihat: depan(h.pos, h.yaw, 10, 2), fov: 44};
  };

  // luncuran kamera di setiap batas momen (tanpa potongan): titik lihat dicampur, lalu kamera ditempatkan dengan
  // jarak & arah yang juga dicampur (melengkung mengitari subjek, tidak menembusnya); terbang jauh = naik melengkung
  const batas = [s2, s3, s4, s5, s6, s7, s8, s9, s10, s10b, s11, s12];
  let kam = kamera(t);
  for (const b of batas) {
    const jauh = b === s6 || b === s7; // terbang ke/dari diorama
    const lama = jauh ? 1.0 : 0.7;
    if (t >= b && t < b + lama) {
      const q = halus((t - b) / lama);
      const a = kamera(b - 0.001);
      const lihat = jauh ? kam.lihat : campurV(a.lihat, kam.lihat, q); // terbang jauh: langsung menatap tujuan
      const offA: V3 = [a.pos[0] - a.lihat[0], a.pos[1] - a.lihat[1], a.pos[2] - a.lihat[2]];
      const offB: V3 = [kam.pos[0] - kam.lihat[0], kam.pos[1] - kam.lihat[1], kam.pos[2] - kam.lihat[2]];
      const jarakA = Math.hypot(...offA);
      const jarakB = Math.hypot(...offB);
      let arah = campurV(offA, offB, q);
      const n = Math.hypot(...arah) || 1;
      arah = [arah[0] / n, arah[1] / n, arah[2] / n];
      const jarak = lerp(jarakA, jarakB, q) + Math.sin(Math.PI * q) * (jauh ? 40 : 2);
      const pos: V3 = [lihat[0] + arah[0] * jarak, lihat[1] + arah[1] * jarak + Math.sin(Math.PI * q) * (jauh ? 35 : 1.5), lihat[2] + arah[2] * jarak];
      kam = {pos, lihat, fov: lerp(a.fov, kam.fov, q)};
    }
  }
  const h = hero(t);

  // suasana: satu putaran hari saat "bebas atur waktu", senja di penutup
  const pHari = t >= s8 && t < s9 ? Math.sin(Math.PI * Math.min(1, (t - s8) / (s9 - s8))) : 0;
  const pSenja = t >= s12 ? halus((t - s12) / 2.2) : 0;
  const fokus: V3 = t >= s6 && t < s7 ? tambah(DIORAMA, [0, 1, 0]) : t >= s4 && t < s5 ? tambah(PODIUM, [0, 1, 0]) : tambah(h.pos, [0, 1.1, 0]);

  return (
    <AbsoluteFill>
      <Panggung3D suasana="siang" menuju="senja" p={Math.max(pHari, pSenja)} fokus={fokus} bokeh={t >= s6 && t < s7 ? 6 : 3}>
        <Kamera3D kunci={[{t: 0, pos: kam.pos, lihat: kam.lihat, fov: kam.fov}]} hentak={[W('jangan'), W('ribet'), W('satu'), gas, W('gratis')]} />
        <Tanah />
        <Jalan />
        <Hutan jumlah={70} dari={0} sampai={0.85} bersih={BERSIH} />
        <Pegunungan />
        <Garasi posisi={GARASI.pos} yaw={GARASI.yaw} />
        <Bangunan posisi={sampingJalur(0.56, -9).pos} yaw={sampingJalur(0.56, -9).yaw} nama="Stasiun" atap="#2B176E" lebar={6} />
        <Bangunan posisi={sampingJalur(0.63, 9).pos} yaw={sampingJalur(0.63, 9).yaw} nama="Penginapan" atap="#00953F" />
        {/* persimpangan: papan bertanda tanya */}
        {[4.1, 4.75, 5.4].map((a, i) => (
          <PapanTanya key={a} posisi={tambah(SIMPANG.pos, [Math.sin(a) * 4, 0, Math.cos(a) * 4])} yaw={a + Math.PI} mulai={i === 0 ? W('pusing') - 0.1 : W('transportasi') + (i - 1) * 0.25} />
        ))}
        {/* meja putar & meja bonus di depan garasi */}
        <Bentuk geo={() => <cylinderGeometry args={[2, 2.1, 0.3, 32]} />} warna="#FFC93C" posisi={tambah(PODIUM, [0, 0.15, 0])} />
        {(t >= s10 - 1 && t < s11) || (t >= s5 && t < s6) ? null : <Motor3D posisi={tambah(PODIUM, [0, 0.3, 0])} yaw={t * 0.9} />}
        {t >= s4 && t < s5
          ? [0, 1, 2, 3].map((i) =>
              t >= W('bersih') + i * 0.12 ? (
                <Bentuk
                  key={i}
                  geo={() => <octahedronGeometry args={[0.18, 0]} />}
                  warna="#FFE27A"
                  emisi="#FFD23F"
                  intensitas={0.8}
                  posisi={tambah(PODIUM, [Math.sin(i * 1.9 + t) * 1.4, 1.3 + Math.sin(i * 2.3) * 0.5, Math.cos(i * 1.9 + t) * 1.4])}
                  rotasi={[t * 2, t * 3, 0]}
                />
              ) : null,
            )
          : null}
        {t >= s10 - 1 && t < s11 ? (
          <>
            <Bentuk geo={() => <boxGeometry args={[5, 1, 2]} />} warna="#B07A45" posisi={tambah(PODIUM, [0, 0.5, 0])} />
            <Helm3D posisi={depan(tambah(PODIUM, [0, 1.4, 0]), GARASI.yaw, 0, 0, -1.2)} mulai={W('helm')} skala={0.6} />
            <JasHujan3D posisi={depan(tambah(PODIUM, [0, 1.8, 0]), GARASI.yaw, 0, 0, 1.2)} mulai={W('jas hujan')} skala={0.55} />
          </>
        ) : null}
        {/* hero */}
        {h.tampil ? <Motor3D posisi={h.pos} yaw={h.yaw} laju={h.laju} pengendara miring={h.laju > 4 ? -0.08 : Math.sin(t * 1.6) * 0.04} /> : null}
        {/* diorama peta (didatangi kamera dengan terbang) */}
        <Diorama posisi={DIORAMA} />
        <Pin3D posisi={tambah(DIORAMA, [5, 0, 1])} mulai={s6 + 0.6} nama="Garut" warna="#00953F" skala={1.3} />
        <Pin3D posisi={tambah(DIORAMA, [-4, 0, -3])} mulai={W('mau ke Papandayan')} nama="Papandayan" skala={1.3} />
        <Pin3D posisi={tambah(DIORAMA, [-6, 0, 6])} mulai={W('Darajat')} nama="Darajat" warna="#2B176E" skala={1.3} />
        <Pin3D posisi={tambah(DIORAMA, [7, 0, 9])} mulai={W('Sayang')} nama="Sayang Heulang" warna="#FFC93C" skala={1.3} />
      </Panggung3D>

      {/* ===== teks: huruf kalimat, posisi & arah bergantian; kapital hanya "Tinggal gas" ===== */}
      <Judul baris={['Liburan', {teks: 'ke Garut?', warna: 'kuning', ukuran: 170}]} waktu={[-0.3, W('ke') - 0.1, W('Garut')]} sampai={s2 - 0.1} y={470} ukuran={150} kapital={false} miring={-2} />
      <Judul baris={['Pusing', {teks: 'transportasi?', ukuran: 96}]} waktu={waktuTiapKata(data, 'pusing transportasi')} sampai={W('jangan') - 0.15} y={420} ukuran={140} kapital={false} rata="kiri" miring={0} />
      <Cap teks="Jangan ribet!" x={560} y={420} mulai={W('jangan')} sampai={s3 - 0.1} warna="ungu" ukuran={104} />
      <Judul baris={['Sewa motor', {teks: 'aja', warna: 'kuning', ukuran: 200}]} waktu={waktuTiapKata(data, 'sewa motor aja')} sampai={W('Rental') - 0.25} y={1250} ukuran={130} kapital={false} rata="kanan" miring={2} />
      <Cap teks="No. 1" x={540} y={1330} mulai={W('nomor')} sampai={s4 - 0.1} warna="merah" ukuran={150} miring={-8} />
      {/* satu kata berganti di tempat yang sama (bukan tumpukan 3 kartu) */}
      <Judul baris={[{teks: 'Selalu bersih', warna: 'kuning'}]} mulai={W('motor', s4)} sampai={W('mesin') - 0.12} y={1300} ukuran={120} kapital={false} rata="kiri" miring={0} />
      <Judul baris={[{teks: 'Mesin terawat', warna: 'kuning'}]} mulai={W('mesin')} sampai={W('siap') - 0.12} y={1300} ukuran={120} kapital={false} rata="kiri" miring={0} />
      <Judul baris={[{teks: 'Siap jalan', warna: 'kuning'}]} mulai={W('siap')} sampai={W('ada') - 0.12} y={1300} ukuran={120} kapital={false} rata="kiri" miring={0} />
      <Judul baris={['Matic', {teks: '& manual', warna: 'kuning'}]} waktu={[W('matic'), W('dan', W('matic')), W('manual')]} sampai={s5 - 0.1} y={1280} ukuran={130} kapital={false} rata="kiri" miring={0} />
      <Judul baris={['Harian']} mulai={W('harian')} sampai={W('mingguan') - 0.12} y={460} ukuran={170} kapital={false} rata="kanan" miring={0} />
      <Judul baris={[{teks: 'Mingguan', warna: 'kuning'}]} mulai={W('mingguan')} sampai={s6 - 0.15} y={460} ukuran={170} kapital={false} rata="kanan" miring={0} />
      <GarisLaju dari={s7} sampai={s8} />
      <Judul baris={['Tinggal', {teks: 'gas!', warna: 'kuning', ukuran: 230}]} waktu={[s7, gas]} sampai={s8 - 0.1} y={520} ukuran={150} kapital />
      <Judul baris={['Bebas atur', {teks: 'waktu sendiri', warna: 'kuning'}]} waktu={waktuTiapKata(data, 'bebas atur waktu sendiri')} sampai={s9 - 0.1} y={1300} ukuran={112} kapital={false} rata="kiri" miring={0} />
      <Judul baris={['Harga', {teks: 'bersahabat', warna: 'kuning'}]} waktu={waktuTiapKata(data, 'harga bersahabat')} sampai={W('proses') - 0.12} y={1240} ukuran={130} kapital={false} rata="kanan" miring={0} />
      <Judul baris={['Proses', {teks: 'cepat', warna: 'kuning'}]} waktu={waktuTiapKata(data, 'proses cepat')} sampai={s10 - 0.1} y={1240} ukuran={150} kapital={false} rata="kanan" miring={0} />
      <Cap teks="Gratis" x={540} y={1260} mulai={W('gratis')} sampai={s10b - 0.1} ukuran={140} />
      <Label teks="Bisa diantar" x={540} y={420} mulai={W('diantar')} sampai={s11 - 0.1} warna="putih" ukuran={80} />
      <Adegan dari={s11} sampai={s12}>
        <CtaWA mulai={W('booking') - 0.15} y={960} judul="Booking sekarang" />
      </Adegan>
      <Judul baris={['Garut lebih seru', {teks: 'pakai motor', warna: 'kuning'}]} waktu={waktuTiapKata(data, 'Garut lebih seru pakai motor', s12)} sampai={W('Rental', s12) - 0.25} y={470} ukuran={112} kapital={false} />
      <Judul baris={['Rental Motor', {teks: 'Garut No. 1', warna: 'kuning', ukuran: 140}]} waktu={[W('Rental', s12), W('Rental', s12) + 0.2, W('Rental', s12) + 0.4, W('nomor', s12), W('1', s12)]} y={470} ukuran={116} kapital={false} />
      {t >= s12 ? <Label teks={`WA ${data.brand.whatsapp}`} x={540} y={1470} mulai={s12 + 0.3} warna="hijau" warnaTeks="putih" ukuran={60} /> : null}

      {/* hanya dua sapuan (masuk peta & masuk CTA), satu light leak (senja penutup) */}
      <Sapuan pada={s6} warna={['kuning', 'merah', 'ungu']} />
      <Sapuan pada={s11} warna={['hijau', 'kuning', 'ungu']} />
      <KilauCahaya pada={s12 + 0.4} durasi={1.6} benih={3} kuat={0.7} />
    </AbsoluteFill>
  );
};
