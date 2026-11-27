// Jasa bangun & renovasi rumah Contoh Brand (narasi: footage/_uji/voice_contoh2.m4a).
// Semua klaim (garansi, tanpa biaya tersembunyi, konsultasi/survei gratis) diambil dari ucapan narasi pemilik.
import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {
  Adegan,
  Cap,
  CtaWA,
  FONT_JUDUL,
  Ikon,
  IkonBebas,
  Judul,
  Kamera,
  KartuFitur,
  Label,
  Latar,
  NamaIkon,
  Pemandangan,
  Rumah,
  Sapuan,
  Stiker,
  Tokoh,
  useData,
  waktuKata,
  waktuTiapKata,
} from '../../kit';

const Layanan: React.FC<{ikon: NamaIkon; teks: string; x: number; y: number; mulai: number; warna: string; miring: number}> = ({ikon, teks, x, y, mulai, warna, miring}) => (
  <Stiker x={x} y={y} mulai={mulai} lebar={440} tinggi={390} warna="putih" miring={miring} dariArah="bawah">
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14}}>
      <Ikon nama={ikon} ukuran={210} warna={warna} />
      <span style={{fontFamily: FONT_JUDUL, fontWeight: 800, fontSize: 54, textTransform: 'uppercase', textAlign: 'center', lineHeight: 1}}>{teks}</span>
    </div>
  </Stiker>
);

export const KonstruksiRumah: React.FC = () => {
  const data = useData();
  const W = (teks: string, setelah = 0) => waktuKata(data, teks, setelah);
  const akhir = data.durasi;

  const s2 = W('tapi') - 0.08;
  const s3 = W('serahkan') - 0.1;
  const s4 = W('kami') - 0.1;
  const s5 = W('dikerjakan') - 0.1;
  const s6 = W('RAB') - 0.08;
  const s7 = W('pengerjaan') - 0.06;
  const s8 = W('hubungi') - 0.2;
  const s9 = W('rumah', s8) - 0.1;

  return (
    <AbsoluteFill>
      {/* 1. HOOK — rumah dibangun di atas kertas cetak biru */}
      <Adegan dari={0} sampai={s2}>
        <Kamera dari={0} sampai={s2} zoom={[1.0, 1.08]} fokus={[0.5, 0.7]} hentak={[0.9 + 2.2 * 0.8]}>
          <Latar warna="ungu" pola="kotak" kuatPola={0.14} />
          <Rumah x={540} y={1360} ukuran={640} mulai={0.6} durasi={2.2} />
          <Judul
            baris={['Mau bangun', 'atau renovasi', {teks: 'rumah?', warna: 'kuning', ukuran: 160}]}
            waktu={[-0.3, -0.2, W('atau'), W('renovasi'), W('rumah')]}
            y={540}
            ukuran={112}
          />
        </Kamera>
      </Adegan>

      {/* 2. Masalah — takut hasilnya tidak sesuai */}
      <Adegan dari={s2} sampai={s3}>
        <Kamera dari={s2} sampai={s3} hentak={[W('gak')]}>
          <Latar warna="merah" pola="sinar" kuatPola={0.12} />
          <Rumah x={540} y={1340} ukuran={560} mulai={s2} durasi={0.8} rusak warnaAtap="ungu" />
          <IkonBebas nama="tanya" x={200} y={820} ukuran={150} mulai={W('takut')} warna="kuning" miring={-12} />
          <IkonBebas nama="tanya" x={880} y={760} ukuran={120} mulai={W('hasilnya')} warna="kuning" miring={12} />
          <Judul baris={['Takut hasilnya', {teks: 'gak sesuai', warna: 'kuning'}, 'harapan?']} waktu={waktuTiapKata(data, 'takut hasilnya gak sesuai harapan')} y={540} ukuran={104} />
        </Kamera>
      </Adegan>

      {/* 3. Solusi — serahkan ke Contoh Brand */}
      <Adegan dari={s3} sampai={s4}>
        <Kamera dari={s3} sampai={s4} zoom={[1, 1.05]} hentak={[W('Brand')]}>
          <Latar warna="hijau" pola="sinar" kuatPola={0.12} />
          <Judul baris={['Serahkan ke']} waktu={waktuTiapKata(data, 'serahkan ke')} y={470} ukuran={120} />
          {data.brand.logo ? (
            <Stiker x={540} y={860} mulai={W('PT')} lebar={460} tinggi={460} padding={30} miring={-3}>
              <Img src={staticFile(data.brand.logo)} style={{width: '100%', height: '100%', objectFit: 'contain', borderRadius: 18}} />
            </Stiker>
          ) : null}
          <Judul baris={['PT Brand', {teks: 'Energi Indonesia', warna: 'kuning', ukuran: 84}]} waktu={[W('PT'), W('Brand'), W('Energi'), W('Indonesia')]} y={1310} ukuran={110} miring={-2} />
        </Kamera>
      </Adegan>

      {/* 4. Layanan — 4 kartu */}
      <Adegan dari={s4} sampai={s5}>
        <Kamera dari={s4} sampai={s5} zoom={[1, 1.04]}>
          <Latar warna="krem" pola="kotak" warnaPola="ungu" kuatPola={0.08} />
          <Label teks="Kami melayani" x={540} y={400} mulai={W('kami')} warna="ungu" warnaTeks="putih" ukuran={76} miring={-2} />
          <Layanan ikon="rumah" teks="Rumah baru" x={295} y={770} mulai={W('bangunan')} warna="merah" miring={-3} />
          <Layanan ikon="palu" teks="Renovasi" x={785} y={770} mulai={W('renovasi', s4)} warna="kuning" miring={2} />
          <Layanan ikon="kanopi" teks="Kanopi" x={295} y={1215} mulai={W('kanopi')} warna="hijau" miring={2} />
          <Layanan ikon="molen" teks="Pengecoran" x={785} y={1215} mulai={W('pengecoran')} warna="ungu" miring={-2} />
        </Kamera>
      </Adegan>

      {/* 5. Keunggulan kerja — tukang memalu + daftar */}
      <Adegan dari={s5} sampai={s6}>
        <Kamera dari={s5} sampai={s6}>
          <Latar warna="ungu" pola="titik" />
          <Tokoh x={235} y={1490} ukuran={760} topi="helmProyek" warnaTopi="kuning" baju="merah" aksi="palu" ekspresi="senang" />
          <KartuFitur ikon="helmProyek" warnaIkon="kuning" teks="Tukang berpengalaman" x={700} y={560} lebar={620} ukuranTeks={42} mulai={W('tukang')} />
          <KartuFitur ikon="bata" warnaIkon="merah" teks="Material berkualitas" x={700} y={820} lebar={620} ukuranTeks={42} mulai={W('material')} miring={1.5} />
          <KartuFitur ikon="penggaris" warnaIkon="hijau" teks="Desain sesuai kebutuhan" x={700} y={1080} lebar={620} ukuranTeks={42} mulai={W('desain')} miring={-1.5} />
        </Kamera>
      </Adegan>

      {/* 6. RAB jelas, tanpa biaya tersembunyi */}
      <Adegan dari={s6} sampai={s7}>
        <Kamera dari={s6} sampai={s7} hentak={[W('tanpa')]}>
          <Latar warna="kuning" pola="garis" warnaPola="putih" kuatPola={0.35} />
          <IkonBebas nama="dokumen" x={540} y={700} ukuran={430} mulai={s6} warna="ungu" />
          <Judul baris={['RAB jelas', {teks: 'dari awal', warna: 'putih'}]} waktu={waktuTiapKata(data, 'RAB jelas dari awal')} y={1120} ukuran={130} />
          <Cap teks="Tanpa biaya tersembunyi" x={540} y={1380} mulai={W('tanpa')} warna="merah" ukuran={68} miring={-5} />
        </Kamera>
      </Adegan>

      {/* 7. Tepat waktu, bergaransi, konsultasi gratis */}
      <Adegan dari={s7} sampai={s8}>
        <Kamera dari={s7} sampai={s8} hentak={[W('gratis', s7)]}>
          <Latar warna="hijau" pola="garis" kuatPola={0.1} />
          <KartuFitur ikon="jam" warnaIkon="kuning" teks="Tepat waktu" y={620} mulai={s7 + 0.2} dariArah="kiri" />
          <KartuFitur ikon="perisai" warnaIkon="ungu" teks="Bergaransi" y={900} mulai={W('bergaransi')} dariArah="kanan" miring={1.5} />
          <KartuFitur ikon="chat" warnaIkon="hijau" teks="Konsultasi" y={1180} mulai={W('konsultasi', s7)} dariArah="kiri" miring={-1.5} />
          <Cap teks="Gratis!" x={800} y={1300} mulai={W('gratis', s7)} ukuran={90} miring={-10} />
        </Kamera>
      </Adegan>

      {/* 8. CTA — survei & konsultasi gratis via WhatsApp */}
      <Adegan dari={s8} sampai={s9}>
        <Kamera dari={s8} sampai={s9} zoom={[1, 1.03]}>
          <Latar warna="ungu" pola="sinar" kuatPola={0.14} />
          <CtaWA mulai={W('hubungi') - 0.15} y={880} judul="Survei & konsultasi gratis!" />
          <IkonBebas nama="tangan" x={890} y={1370} ukuran={190} mulai={W('nomor') - 0.2} warna="kuning" miring={-25} />
        </Kamera>
      </Adegan>

      {/* 9. Penutup — rumah impian mulai dari sini */}
      <Adegan dari={s9} sampai={akhir + 1}>
        <Kamera dari={s9} sampai={akhir} zoom={[1, 1.06]} fokus={[0.5, 0.65]} hentak={[s9 + 0.05 + 1.2 * 0.8]}>
          <Pemandangan senja jalan={false} />
          <Rumah x={520} y={1300} ukuran={660} mulai={s9 + 0.05} durasi={1.2} warnaAtap="merah" />
          <Tokoh x={900} y={1430} ukuran={470} topi="helmProyek" warnaTopi="kuning" baju="hijau" aksi="jempol" fase={0.7} />
          <Judul baris={['Rumah impian', {teks: 'mulai dari sini', warna: 'kuning'}]} waktu={waktuTiapKata(data, 'rumah impian mulai dari sini', s8)} y={500} ukuran={112} />
        </Kamera>
        <Label teks={`WA ${data.brand.whatsapp}`} x={540} y={1470} mulai={s9 + 0.3} warna="hijau" warnaTeks="putih" ukuran={60} />
      </Adegan>

      {[s2, s3, s4, s5, s6, s7, s8, s9].map((p, i) => (
        <Sapuan key={p} pada={p} warna={i % 2 ? ['hijau', 'kuning', 'ungu'] : ['kuning', 'merah', 'ungu']} />
      ))}
    </AbsoluteFill>
  );
};
