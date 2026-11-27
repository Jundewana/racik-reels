// UJI COBA (jangan diposting tanpa izin pemilik konten): cuplikan podcast kreator gaming — tips bertahan jadi YouTuber
// (konsisten + masuk sirkel). Tokoh generik ber-headset, BUKAN karikatur orang sungguhan.
// Anti-PPT: SATU dunia 3D & SATU kamera yang terus bergerak: meja podcast → gamepad raksasa → tangga video yang
// tersusun di bawah kaki sang kreator (hero, hadir hampir sepanjang video) menuju piala → sirkel yang tumbuh bareng →
// pesta. Satu sapuan (pindah ke sirkel), satu light leak ("luar biasa"), kapital hanya "Just do it".
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Cap, Judul, Sapuan, Subtitle, WARNA, useData, useDetik, waktuKata, waktuTiapKata} from '../../kit';
import {lerp} from '../../kit/gerak';
import {KilauCahaya} from '../../kit/Sinematik';
import {Kamera3D, Panggung3D, Tanah, V3} from '../../kit3d';
import {KalenderStreak} from './KalenderStreak';
import {
  AwanHujan,
  atasTangga,
  Gamepad3D,
  gayaGelap,
  GumpalanLangit,
  halus,
  Konfeti,
  KonsolSirkel,
  Kreator3D,
  Matahari,
  MejaPodcast,
  PanahBoost,
  Piala3D,
  PoseKreator,
  TANGGA,
  TanggaVideo,
  zTangga,
} from './objek3d';

type Kam = {pos: V3; lihat: V3; fov: number};
type Hero = {pos: V3; yaw: number; pose: PoseKreator; skala: number};

const tambah = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const campurV = (a: V3, b: V3, q: number): V3 => [lerp(a[0], b[0], q), lerp(a[1], b[1], q), lerp(a[2], b[2], q)];
const antara = (x: number, a: number, b: number) => Math.min(1, Math.max(0, (x - a) / (b - a)));
const orbit = (pusat: V3, sudut: number, jarak: number, tinggi: number): V3 => [pusat[0] + Math.sin(sudut) * jarak, pusat[1] + tinggi, pusat[2] + Math.cos(sudut) * jarak];

// ---- tata letak dunia
const MEJA: V3 = [0, 0, 0];
const KURSI = {host: 0, hero: 2.2, tamu: -2.2};
const kursi = (a: number): V3 => [Math.sin(a) * 2.3, 0.42, Math.cos(a) * 2.3];
const GAMEPAD: V3 = [6, 0, -12];
const PUNCAK: V3 = [0, atasTangga(TANGGA.n), zTangga(TANGGA.n) - 1.8];
const SIRKEL: V3 = [42, 0, -22];
const ANGGOTA = [1, 2, 3, 4, 5].map((j) => (j * Math.PI) / 3);
const PEMULA = [Math.PI / 2, (7 * Math.PI) / 6, (11 * Math.PI) / 6];
const BAJU = () => [WARNA.merah, WARNA.ungu, WARNA.kuning, WARNA.langit, WARNA.merah];

export const Radityadika3D: React.FC = () => {
  const data = useData();
  const t = useDetik();
  const W = (teks: string, setelah = 0) => waktuKata(data, teks, setelah);
  const gelapGaya = gayaGelap();

  // ---- ketukan cerita (dari ucapan)
  const tanya = W('terakhir') - 0.15;
  const dunia = W('dunia') - 0.3;
  const kunci = W('kuncinya');
  const konsisten = W('konsisten', kunci);
  const tiba = kunci + 4;
  const mood = W('mood', 34) - 0.15;
  const buruk = W('buruk');
  const bagus = W('bagus');
  const just = W('just');
  const buah = W('buah') - 0.2;
  const satuVideo = W('satu', 54);
  const sepuluh = W('10', 54);
  const luar = W('luar');
  const sapuan = W('tips', 62) + 0.12;
  const masuk = W('masuk', 67);
  const tumbuh = W('tumbuhnya');
  const collab = W('collab');
  const bawa = W('bawa');
  const boost = W('keboosting');
  const pesta = W('baru', 95);
  const party = W('party');
  const akhirCirkel = W('cirkel', 105);

  // ---- hero (kreator ber-headset hijau)
  const N = TANGGA.n;
  const kursiHero = kursi(KURSI.hero);
  const kakiTangga: V3 = [0, 0, zTangga(-1)];
  const langkahPerDtk = (N + 1) / (luar - tiba);
  const radius = (x: number) => 4.5 + 2 * halus(antara(x, collab, collab + 1.8));
  const tumbuhS = (x: number) => 1 + 0.3 * halus(antara(x, tumbuh, tumbuh + 1.5));
  const pestaP = (x: number) => halus(antara(x, pesta, pesta + 0.6));
  const lompatPesta = (x: number, j: number) => Math.abs(Math.sin((x * 1.7 + j * 0.29) * Math.PI)) * 0.7 * pestaP(x);

  const hero = (x: number): Hero => {
    if (x < kunci) return {pos: [kursiHero[0], 0, kursiHero[2]], yaw: KURSI.hero + Math.PI, pose: {duduk: true, diMeja: true}, skala: 1};
    if (x < kunci + 0.5) {
      // berdiri sambil berbalik ke arah tangga
      const q = halus(antara(x, kunci, kunci + 0.5));
      return {pos: [kursiHero[0], 0, kursiHero[2]], yaw: lerp(KURSI.hero + Math.PI, Math.PI + 0.12, q), pose: {lompat: Math.sin(Math.PI * q) * 0.25}, skala: 1};
    }
    if (x < tiba) {
      const q = antara(x, kunci + 0.5, tiba);
      const pos = campurV([kursiHero[0], 0, kursiHero[2]], kakiTangga, q);
      return {pos, yaw: Math.atan2(kakiTangga[0] - kursiHero[0], kakiTangga[2] - kursiHero[2]), pose: {langkah: x * 11}, skala: 1};
    }
    if (x < luar) {
      // naik satu anak tangga demi satu (k = -1 → tanah, N → puncak)
      const k = -1 + (x - tiba) * langkahPerDtk;
      const i = Math.floor(k);
      const f = k - i;
      const q = f < 0.6 ? 0 : (f - 0.6) / 0.4;
      const y = lerp(atasTangga(i), atasTangga(i + 1), halus(q)) + Math.sin(Math.PI * q) * 0.3;
      return {pos: [0, y, zTangga(-1) - TANGGA.panjang * (k + 1)], yaw: Math.PI, pose: {langkah: k * Math.PI}, skala: 1};
    }
    if (x < sapuan) {
      const q = halus(antara(x, luar, luar + 0.9));
      const pos: V3 = [lerp(0, -1.2, q), PUNCAK[1], lerp(zTangga(N), PUNCAK[2] + 0.6, q)];
      const sorak = x > luar + 0.8 ? 1 : 0;
      const lompat = sorak ? Math.abs(Math.sin((x - luar) * Math.PI * 1.6)) * 0.6 : 0;
      return {pos, yaw: lerp(Math.PI, Math.PI * 0.35, q), pose: q < 1 ? {langkah: x * 10, sorak, lompat} : {sorak, lompat}, skala: 1};
    }
    // sirkel: berjalan masuk ke slot sudut 0, lalu tumbuh & berpesta bersama
    const tujuan = (xx: number): V3 => [SIRKEL[0], 0, SIRKEL[2] + radius(xx)];
    const tibaSirkel = masuk + 0.4;
    if (x < tibaSirkel) {
      const q = antara(x, sapuan, tibaSirkel);
      return {pos: campurV([SIRKEL[0], 0, SIRKEL[2] + 13], tujuan(x), q), yaw: Math.PI, pose: {langkah: x * 9}, skala: 1};
    }
    const pp = pestaP(x);
    return {pos: tujuan(x), yaw: Math.PI, pose: {lompat: lompatPesta(x, 0), sorak: pp * (0.6 + 0.4 * Math.sin(x * 5))}, skala: tumbuhS(x)};
  };

  // ---- kamera: satu fungsi per momen, dicampur halus di tiap batas (tanpa potongan, kecuali di balik sapuan)
  const shots: {dari: number; f: (x: number) => Kam}[] = [
    {dari: 0, f: (x) => {
      const q = halus(antara(x, 0, 3));
      return {pos: orbit(MEJA, lerp(0.35, 1.0, q), lerp(17, 13.5, q), lerp(10, 4.6, q)), lihat: [0, 1.2, 0], fov: 40};
    }},
    {dari: 3, f: (x) => {
      const q = antara(x, 3, tanya);
      return {pos: orbit(MEJA, lerp(1.0, 1.75, q), lerp(13.5, 12.5, q), lerp(4.6, 4.0, q)), lihat: [0, 1.2, 0], fov: 40};
    }},
    {dari: tanya, f: (x) => {
      const q = antara(x, tanya, dunia);
      return {pos: [lerp(0.8, 0.2, q), 3.6, lerp(-6.6, -5.8, q)], lihat: [0, 1.7, 2.3], fov: 38};
    }},
    {dari: dunia, f: (x) => {
      const q = halus(antara(x, dunia, kunci));
      return {pos: campurV([4, 3.2, 7.5], [11, 9, 6], q), lihat: campurV([0, 1.4, 0], [2, 5, -30], q), fov: 42};
    }},
    {dari: kunci, f: (x) => {
      const h = hero(x).pos;
      return {pos: tambah(h, [5, 2.6, 5.5]), lihat: tambah(h, [0, 1.1, -1.5]), fov: 42};
    }},
    {dari: tiba, f: (x) => {
      const h = hero(x).pos;
      return {pos: tambah(h, [9.5, 2.6, 3.5]), lihat: tambah(h, [0, 1.3, -2.5]), fov: 42};
    }},
    {dari: mood, f: (x) => {
      const h = hero(x).pos;
      return {pos: tambah(h, [6.5, -0.4, 4.5]), lihat: tambah(h, [0, 2.6, -1]), fov: 46};
    }},
    {dari: buruk - 0.3, f: (x) => {
      const h = hero(x).pos;
      return {pos: tambah(h, [3.8, 2.2, -3.4]), lihat: tambah(h, [0, 2.1, 0]), fov: 46};
    }},
    {dari: buah, f: (x) => {
      const h = hero(x).pos;
      const q = antara(x, buah, satuVideo);
      return {pos: tambah(h, [16, lerp(1.5, 5, q), 10]), lihat: tambah(h, [0, 0.5, -5]), fov: 42};
    }},
    {dari: satuVideo - 0.3, f: (x) => {
      const q = antara(x, satuVideo, sapuan);
      return {pos: orbit(PUNCAK, lerp(0.55, 1.45, q), 12, 3.2), lihat: tambah(PUNCAK, [0, 3.6, 0]), fov: 40};
    }},
    {dari: sapuan, f: (x) => {
      const h = hero(x).pos;
      return {pos: tambah(h, [1.4, 3.0, 7.2]), lihat: tambah(SIRKEL, [0, 1.3, 0]), fov: 42};
    }},
    {dari: masuk + 0.5, f: (x) => {
      const q = antara(x, masuk + 0.5, tumbuh);
      return {pos: orbit(SIRKEL, lerp(0.35, 1.3, q), 15, 6), lihat: tambah(SIRKEL, [0, 1.4, 0]), fov: 40};
    }},
    {dari: tumbuh, f: (x) => {
      const q = antara(x, tumbuh, collab);
      return {pos: orbit(SIRKEL, lerp(1.3, 1.7, q), lerp(15, 18, q), lerp(6, 8, q)), lihat: tambah(SIRKEL, [0, 1.6, 0]), fov: 40};
    }},
    {dari: collab, f: (x) => {
      const q = antara(x, collab, boost);
      return {pos: orbit(SIRKEL, lerp(1.7, 2.5, q), 21, 13), lihat: tambah(SIRKEL, [0, 0.8, 0]), fov: 40};
    }},
    {dari: boost - 0.35, f: (x) => {
      const a = PEMULA[0];
      const r = radius(x);
      const q = antara(x, boost, pesta);
      return {pos: orbit(SIRKEL, a, lerp(r - 5.6, r - 6.2, q), 2.1), lihat: orbit(SIRKEL, a, r, 1.9), fov: 44};
    }},
    {dari: pesta, f: (x) => {
      const q = halus(antara(x, pesta, data.durasi));
      return {pos: orbit(SIRKEL, lerp(0.15, -0.35, q), lerp(15, 22, q), lerp(5, 12, q)), lihat: tambah(SIRKEL, [0, lerp(1.6, 0.6, q), 0]), fov: 42};
    }},
  ];
  const kamera = (x: number): Kam => {
    let i = 0;
    while (i < shots.length - 1 && x >= shots[i + 1].dari) i++;
    const k = shots[i].f(x);
    const lama = 0.9;
    if (i === 0 || shots[i].dari === sapuan || x >= shots[i].dari + lama) return k;
    const a = shots[i - 1].f(x);
    const q = halus((x - shots[i].dari) / lama);
    return {pos: campurV(a.pos, k.pos, q), lihat: campurV(a.lihat, k.lihat, q), fov: lerp(a.fov, k.fov, q)};
  };
  const kam = kamera(t);
  const h = hero(t);

  // ---- mood: awan hujan saat "buruk", matahari saat "bagus"
  const hujan = halus(antara(t, buruk - 0.7, buruk - 0.2)) * (1 - halus(antara(t, bagus - 0.05, bagus + 0.3)));
  const cerah = halus(antara(t, bagus - 0.1, bagus + 0.25)) * (1 - halus(antara(t, buah + 0.5, buah + 1.2)));
  const fokus: V3 = t < kunci ? [0, 1.2, 0] : t >= satuVideo && t < sapuan ? tambah(PUNCAK, [0, 1, 0]) : t >= collab && t < boost - 0.35 ? SIRKEL : tambah(h.pos, [0, 1.2, 0]);

  // tangga: 4 anak tangga pertama muncul saat "dunia gaming", sisanya muncul 3 langkah di depan hero
  const muncul = (i: number) => (i < 4 ? W('gaming', 17) + i * 0.12 : tiba + (i - 3) / langkahPerDtk);
  const anggotaS = tumbuhS(t);

  return (
    <AbsoluteFill>
      <Panggung3D suasana={gelapGaya ? 'malam' : 'siang'} menuju="malam" p={gelapGaya ? 0 : hujan * 0.55} fokus={fokus} bokeh={2.6} kabut={[60, 300]}>
        <Kamera3D kunci={[{t: 0, pos: kam.pos, lihat: kam.lihat, fov: kam.fov}]} hentak={[konsisten, just, luar, W('sirkel', masuk), boost, party]} />
        <ambientLight intensity={gelapGaya ? 0.9 : 0.25} />
        <Tanah warna={gelapGaya ? WARNA.unguMuda : WARNA.hijauMuda} />
        <GumpalanLangit />

        {/* studio podcast */}
        <MejaPodcast posisi={MEJA} kursi={[KURSI.host, KURSI.hero, KURSI.tamu]} />
        <Kreator3D posisi={[kursi(KURSI.host)[0], 0, kursi(KURSI.host)[2]]} yaw={KURSI.host + Math.PI} baju={WARNA.merah} aksen={WARNA.langit} pose={{duduk: true, diMeja: true}} fase={1.3} />
        <Kreator3D posisi={[kursi(KURSI.tamu)[0], 0, kursi(KURSI.tamu)[2]]} yaw={KURSI.tamu + Math.PI} baju={WARNA.ungu} aksen={WARNA.merah} pose={{duduk: true, diMeja: true}} fase={2.1} />

        {/* dunia gaming: gamepad raksasa, tangga video, menara piala */}
        <Gamepad3D posisi={GAMEPAD} yaw={-0.5} skala={1.5} mulai={W('dunia') - 0.1} />
        <TanggaVideo muncul={muncul} menaraMulai={W('gaming', 17) + 0.5} />
        <Piala3D posisi={tambah(PUNCAK, [1.6, 0.15, -1])} skala={1.4} nyala={t >= luar ? 0.6 : 0.15} />
        <AwanHujan posisi={tambah(h.pos, [0.4, 3.4, -0.8])} kuat={hujan * 0.65} />
        <Matahari posisi={tambah(h.pos, [1.6, 5, -1])} kuat={cerah} />

        {/* sirkel kreator */}
        <KonsolSirkel posisi={SIRKEL} kuat={halus(antara(t, masuk, masuk + 1)) + 0.6 * halus(antara(t, collab, collab + 1))} />
        {ANGGOTA.map((a, j) => (
          <Kreator3D
            key={j}
            posisi={tambah(SIRKEL, [Math.sin(a) * radius(t), 0, Math.cos(a) * radius(t)])}
            yaw={a + Math.PI}
            baju={BAJU()[j]}
            aksen={j % 2 ? WARNA.hijau : WARNA.kuning}
            skala={anggotaS}
            fase={j * 1.7}
            pose={{lompat: lompatPesta(t, j + 1), sorak: pestaP(t) * (0.6 + 0.4 * Math.sin(t * 5 + j)), diMeja: t < pesta && t >= masuk && j % 2 === 0}}
          />
        ))}
        {PEMULA.map((a, j) => {
          const mulai = bawa + j * 0.35;
          if (t < mulai) return null;
          const q = antara(t, mulai, mulai + 2.6);
          const r = radius(t);
          const pos = tambah(SIRKEL, [Math.sin(a) * lerp(r + 10, r, q), 0, Math.cos(a) * lerp(r + 10, r, q)]);
          const s = 0.6 + 0.7 * Math.min(1.08, halus(antara(t, boost + j * 0.15, boost + j * 0.15 + 0.6)));
          return (
            <React.Fragment key={j}>
              <Kreator3D
                posisi={pos}
                yaw={a + Math.PI}
                baju={WARNA.hijauMuda}
                aksen={WARNA.ungu}
                skala={s}
                fase={j * 2.3}
                pose={q < 1 ? {langkah: t * 10 + j} : {lompat: lompatPesta(t, j + 6), sorak: Math.max(pestaP(t), t >= boost ? 0.7 : 0)}}
              />
              <PanahBoost posisi={pos} mulai={boost + j * 0.15} />
            </React.Fragment>
          );
        })}
        <Konfeti pusat={SIRKEL} mulai={pesta} jumlah={40} />
        <Konfeti pusat={SIRKEL} mulai={akhirCirkel - 0.2} jumlah={60} luas={22} />

        {/* hero */}
        <Kreator3D posisi={h.pos} yaw={h.yaw} baju={WARNA.hijau} aksen={WARNA.kuning} pose={h.pose} skala={h.skala} />
      </Panggung3D>

      {/* ===== teks: maks 1 judul + subtitle; huruf kalimat, posisi bergantian; kapital hanya "Just do it" ===== */}
      <Judul baris={['Kunci YouTuber', {teks: 'bertahan lama', warna: 'kuning'}]} mulai={-0.3} jeda={0.08} sampai={W('5') - 0.2} y={430} ukuran={118} kapital={false} miring={-2} />
      <Judul baris={['5 tahun', {teks: 'lebih!', warna: 'kuning', ukuran: 170}]} waktu={[W('5'), W('tahun'), W('lebih')]} sampai={tanya - 0.15} y={450} ukuran={130} kapital={false} rata="kiri" miring={0} />
      <Judul baris={['Satu tip', {teks: 'buat pemula?', warna: 'kuning'}]} waktu={[W('satu', 12), W('tip', 12), W('buat', 13), W('temen', 13)]} sampai={dunia - 0.1} y={440} ukuran={120} kapital={false} rata="kanan" miring={0} />
      <Judul baris={['Masuk dunia', {teks: 'gaming', warna: 'kuning', ukuran: 180}]} waktu={[W('masuk', 14), W('dunia'), W('gaming', 17)]} sampai={kunci - 0.15} y={440} ukuran={110} kapital={false} miring={-2} />
      <Judul baris={['Kuncinya:', {teks: 'konsisten', warna: 'kuning', ukuran: 170}]} waktu={[kunci, konsisten]} sampai={W('basi') - 0.12} y={450} ukuran={110} kapital={false} rata="kiri" miring={0} />
      <Cap teks="Basi?" x={540} y={440} mulai={W('basi')} sampai={W('tapi', 28) - 0.1} warna="merah" ukuran={120} miring={-8} />
      <Judul baris={['Tapi itu', {teks: 'yang berhasil', warna: 'kuning'}]} waktu={[W('tapi', 28), W('itu', 28.4), W('exactly'), W('lakukan', 29)]} sampai={W('konsisten', 31) - 0.12} y={450} ukuran={120} kapital={false} rata="kanan" miring={0} />
      <Judul baris={['Kerja jangan', {teks: 'ikut mood', warna: 'kuning'}]} waktu={[mood + 0.15, W('gak', 36), W('bekerja', 36), W('mood', W('bekerja', 36))]} sampai={buruk - 0.5} y={440} ukuran={120} kapital={false} miring={-2} />
      <Judul baris={['Mood buruk', {teks: 'atau bagus', warna: 'kuning'}]} waktu={[buruk - 0.4, buruk, W('atau', 42.5), bagus]} sampai={just - 0.06} y={450} ukuran={120} kapital={false} rata="kiri" miring={0} />
      <Judul baris={['Just', {teks: 'do it!', warna: 'kuning', ukuran: 210}]} waktu={[just, W('do', just), W('it', just)]} sampai={buah - 0.1} y={470} ukuran={170} kapital miring={-4} />
      <Judul baris={['Buah dari', {teks: 'konsisten', warna: 'kuning'}]} waktu={[W('buah'), W('buah') + 0.12, W('konsisten', 47)]} sampai={W('grinding') - 0.12} y={440} ukuran={125} kapital={false} rata="kanan" miring={0} />
      <Judul baris={['Terus', {teks: 'grinding', warna: 'kuning', ukuran: 170}]} waktu={[W('terus', 52), W('grinding')]} sampai={satuVideo - 0.4} y={450} ukuran={120} kapital={false} rata="kiri" miring={-2} />
      <KalenderStreak mulai={satuVideo - 0.3} isi={satuVideo} hitungDari={W('dilakukan', 55)} hitungSampai={sepuluh + 0.6} sampai={luar - 0.15} y={640} />
      <Cap teks="Luar biasa!" x={540} y={450} mulai={luar} sampai={W('kalau', 61) - 0.1} warna="hijau" ukuran={110} miring={-6} />
      <Judul baris={['Ada tips', {teks: 'lain?', warna: 'kuning', ukuran: 170}]} waktu={[W('kalau', 61.5), W('apa', 62), W('tips', 62)]} sampai={sapuan - 0.05} y={450} ukuran={120} kapital={false} rata="kanan" miring={0} />
      <Judul baris={['Ikuti', {teks: 'meta sekarang', warna: 'kuning'}]} waktu={[W('ikutin'), W('meta'), W('sekarang', 65)]} sampai={masuk - 0.15} y={440} ukuran={120} kapital={false} rata="kanan" miring={0} />
      <Judul baris={['Masuk', {teks: 'sirkel', warna: 'kuning', ukuran: 190}]} waktu={[masuk, W('sirkel', masuk)]} sampai={masuk + 3} y={450} ukuran={120} kapital={false} miring={-3} />
      <Judul baris={['Tumbuh', {teks: 'bareng', warna: 'kuning', ukuran: 180}]} waktu={[tumbuh, W('bareng', tumbuh)]} sampai={collab - 0.15} y={440} ukuran={120} kapital={false} rata="kiri" miring={0} />
      <Judul baris={['Collab =', {teks: 'makin besar', warna: 'kuning'}]} waktu={[collab, collab + 0.15, W('lebih', 86.5), W('besar', 86.5)]} sampai={bawa - 0.15} y={440} ukuran={125} kapital={false} rata="kanan" miring={0} />
      <Judul baris={['Ajak yang', {teks: 'baru merintis', warna: 'kuning'}]} waktu={[bawa, bawa + 0.12, W('masih', 91), W('merindis')]} sampai={boost - 0.1} y={450} ukuran={115} kapital={false} rata="kiri" miring={0} />
      <Cap teks="Ke-boost!" x={540} y={450} mulai={boost} sampai={pesta - 0.1} warna="ungu" ukuran={120} miring={-7} />
      <Judul baris={['Pemula?', {teks: 'Jalan bareng', warna: 'kuning'}]} waktu={[pesta, W('lain', 97), W('lain', 97) + 0.15]} sampai={W('buat', 99) - 0.12} y={450} ukuran={120} kapital={false} rata="kanan" miring={0} />
      <Judul baris={['Bikin', {teks: 'sirkelmu', warna: 'kuning', ukuran: 180}]} waktu={[W('buat', 99), W('cirkel', 100)]} sampai={akhirCirkel - 0.25} y={440} ukuran={120} kapital={false} rata="kiri" miring={-2} />
      <Judul baris={['Sirkel +', {teks: 'game party', warna: 'kuning', ukuran: 160}]} waktu={[akhirCirkel, akhirCirkel + 0.15, ...waktuTiapKata(data, 'game party', akhirCirkel)]} y={450} ukuran={130} kapital={false} miring={-3} />

      <Subtitle y={1410} maksKata={4} ukuran={58} />

      {/* satu sapuan (lompat ke dunia sirkel), satu light leak (puncak "luar biasa") */}
      <Sapuan pada={sapuan} warna={['ungu', 'kuning', 'merah']} />
      <KilauCahaya pada={luar + 0.2} durasi={1.6} benih={5} kuat={0.75} />
    </AbsoluteFill>
  );
};
