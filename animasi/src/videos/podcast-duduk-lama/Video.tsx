// UJI COBA (jangan diposting tanpa izin pemilik konten): cuplikan podcast_raditya_dika.mp4 tentang risiko kesehatan
// kerja duduk lama, disusun ulang (cold open). Tokoh generik — bukan karikatur orang sungguhan.
import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {
  Adegan,
  Cap,
  DiagramPanggul,
  IkonBebas,
  Judul,
  Kamera,
  Kursi,
  Label,
  Latar,
  MejaMonitor,
  Sapuan,
  Stiker,
  Ikon,
  Subtitle,
  Tokoh,
  FONT_JUDUL,
  useData,
  useDetik,
  waktuKata,
  waktuTiapKata,
} from '../../kit';

/** Gamer di meja kerja (lantai di y). */
const Setup: React.FC<{y?: number; bungkuk?: number; nyeri?: boolean; ekspresi?: 'senang' | 'biasa' | 'sedih' | 'bingung'}> = ({y = 1330, bungkuk = 0, nyeri = false, ekspresi = 'senang'}) => (
  <>
    <Kursi x={300} y={y} skala={0.8} warna="ungu" />
    <Tokoh x={330} y={y} ukuran={640} duduk bungkuk={bungkuk} nyeri={nyeri} ekspresi={ekspresi} baju="merah" topi="rambut" warnaTopi="#3A2A20" aksi="diam" />
    <MejaMonitor x={930} y={y} skala={0.75} />
  </>
);

export const PodcastDudukLama: React.FC = () => {
  const data = useData();
  const t = useDetik();
  const W = (teks: string, setelah = 0) => waktuKata(data, teks, setelah);
  const akhir = data.durasi;

  const s2 = W('gue') - 0.1;
  const s3 = W('terus') - 0.1;
  const s4 = W('nah') - 0.08;
  const s5 = W('pertanyaan') - 0.1;

  const sakit1 = W('back');
  const sembuh = W('hilang');
  const kambuh = W('masalah', sembuh);
  const nyeri = (t >= sakit1 && t < sembuh) || t >= kambuh;
  const bungkukS4 = interpolate(t, [s4, W('layar')], [2, 20], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill>
      {/* 1. HOOK — "profesi yang menyenangkan… duduk doang… tapi ada risiko" */}
      <Adegan dari={0} sampai={s2}>
        <Kamera dari={0} sampai={s2} zoom={[1, 1.07]} fokus={[0.4, 0.6]} hentak={[W('risiko')]}>
          <Latar warna={t < W('tapi') ? 'kuning' : 'merah'} pola="garis" warnaPola="putih" kuatPola={0.3} />
          <Setup ekspresi={t < W('tapi') ? 'senang' : 'bingung'} />
          <Judul baris={['Profesi', {teks: 'menyenangkan?', warna: 'kuning'}]} waktu={[-0.3, W('menyenangkan') - 0.4]} sampai={W('duduk') - 0.2} y={480} ukuran={92} />
          <Judul baris={[{teks: 'Duduk doang', ukuran: 130}]} waktu={waktuTiapKata(data, 'duduk doang')} sampai={W('tapi') - 0.1} y={480} />
          <Cap teks="Tapi ada risiko!" x={540} y={470} mulai={W('tapi')} warna="merah" ukuran={96} miring={-6} />
        </Kamera>
      </Adegan>

      {/* 2. Cerita — pilates 2x, back pain hilang lalu kambuh */}
      <Adegan dari={s2} sampai={s3}>
        <Kamera dari={s2} sampai={s3} hentak={[kambuh]}>
          <Latar warna="hijau" pola="titik" />
          <Tokoh x={330} y={1340} ukuran={820} baju="merah" topi="rambut" warnaTopi="#3A2A20" nyeri={nyeri} ekspresi={nyeri ? 'sedih' : 'senang'} aksi={t >= sembuh && t < kambuh ? 'jempol' : 'diam'} />
          <Stiker x={760} y={520} mulai={W('pilates')} lebar={440} padding={18} miring={3}>
            <Ikon nama="kalender" ukuran={110} warna="ungu" />
            <span style={{fontFamily: FONT_JUDUL, fontWeight: 800, fontSize: 52, textTransform: 'uppercase', lineHeight: 1}}>
              Pilates
              <br />
              <span style={{color: '#D9261C', fontSize: 64}}>{t >= W('dua') ? '2×' : ''}</span>
            </span>
          </Stiker>
          <Label teks="Back pain" x={770} y={800} mulai={sakit1} sampai={sembuh - 0.1} warna="merah" warnaTeks="putih" ukuran={84} miring={-4} />
          <Label teks="Hilang ✓" x={770} y={800} mulai={sembuh} sampai={kambuh - 0.1} warna="putih" warnaTeks="hijau" ukuran={84} miring={3} />
          <Cap teks="Kambuh lagi!" x={760} y={820} mulai={kambuh} ukuran={78} miring={-8} />
        </Kamera>
      </Adegan>

      {/* 3. Penjelasan — panggul memendek & miring ke depan (anterior pelvic tilt) */}
      <Adegan dari={s3} sampai={s4}>
        <Kamera dari={s3} sampai={s4} zoom={[1, 1.05]} fokus={[0.5, 0.55]}>
          <Latar warna="ungu" pola="kotak" kuatPola={0.1} />
          <Judul baris={['Yang dibenerin:', {teks: 'panggul', warna: 'kuning', ukuran: 120}]} waktu={[W('dibenerin') - 0.3, W('dibenerin'), W('panggul')]} sampai={W('karena', s3) - 0.2} y={400} ukuran={80} />
          <Judul baris={['Keseringan', {teks: 'duduk lama', warna: 'kuning'}]} waktu={waktuTiapKata(data, 'keseringan duduk lama')} y={400} ukuran={96} />
          <DiagramPanggul x={540} y={950} ukuran={560} mulai={s3 + 0.15} mulaiMiring={W('memendek')} durasi={2.2} sudut={24} label="Anterior pelvic tilt" mulaiLabel={W('anterior')} />
        </Kamera>
      </Adegan>

      {/* 4. Penyebab — kelamaan di depan layar, postur makin membungkuk */}
      <Adegan dari={s4} sampai={s5}>
        <Kamera dari={s4} sampai={s5} zoom={[1, 1.08]} fokus={[0.35, 0.6]} hentak={[W('duduk', s4)]}>
          <Latar warna="merah" pola="sinar" kuatPola={0.1} />
          <Setup bungkuk={bungkukS4} nyeri={t >= W('kesehatan', s4)} ekspresi="sedih" />
          <IkonBebas nama="jam" x={900} y={640} ukuran={170} mulai={W('kelamaan') - 0.2} warna="kuning" />
          <Judul baris={['Masalah', {teks: 'kesehatan', warna: 'kuning'}]} waktu={[W('masalah', s4), W('kesehatan', s4)]} sampai={W('kelamaan') - 0.2} y={450} ukuran={110} />
          <Judul baris={['Kelamaan', {teks: 'di depan layar', warna: 'kuning'}]} waktu={waktuTiapKata(data, 'kelamaan di depan layar')} sampai={W('duduk', s4) - 0.15} y={450} ukuran={104} />
          <Cap teks="Duduk lama!" x={560} y={460} mulai={W('duduk', s4)} warna="ungu" ukuran={110} miring={-5} />
        </Kamera>
      </Adegan>

      {/* 5. Pertanyaan ke tamu — ditutup dengan tanya */}
      <Adegan dari={s5} sampai={akhir + 1}>
        <Kamera dari={s5} sampai={akhir} zoom={[1, 1.05]}>
          <Latar warna="ungu" pola="sinar" kuatPola={0.14} />
          <Label teks="Pertanyaan" x={540} y={390} mulai={W('pertanyaan')} warna="kuning" ukuran={70} miring={-3} />
          <IkonBebas nama="mikrofon" x={540} y={680} ukuran={300} mulai={W('pertanyaan') + 0.2} warna="merah" />
          <Judul baris={['Main game', {teks: 'lama…', warna: 'kuning'}]} waktu={[W('main'), W('game'), W('lama', s5)]} sampai={W('apa', s5) - 0.2} y={1080} ukuran={120} />
          <Judul
            baris={['Masalah kesehatan', 'apa yang', {teks: 'kalian dapetin?', warna: 'kuning'}]}
            waktu={[W('masalah-masalah'), W('kesehatan', s5), W('apa', W('kesehatan', s5)), W('yang', W('kesehatan', s5)), W('kalian', W('kesehatan', s5)), W('dapetin')]}
            y={1080}
            ukuran={88}
          />
          <IkonBebas nama="tanya" x={200} y={600} ukuran={140} mulai={W('dapetin')} warna="kuning" miring={-14} />
          <IkonBebas nama="tanya" x={880} y={640} ukuran={120} mulai={W('dapetin') + 0.2} warna="kuning" miring={12} />
        </Kamera>
      </Adegan>

      {/* subtitle karaoke sepanjang video (konten bicara) */}
      <Subtitle y={1450} maksKata={4} ukuran={58} />

      {[s2, s3, s4, s5].map((p, i) => (
        <Sapuan key={p} pada={p} warna={i % 2 ? ['hijau', 'kuning', 'ungu'] : ['kuning', 'merah', 'ungu']} />
      ))}
    </AbsoluteFill>
  );
};
