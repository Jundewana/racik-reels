// Pilot: promo Rental Motor (narasi: footage/_uji/voice_contoh.m4a). Semua waktu dikunci ke kata narasi.
import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {
  Adegan,
  Cap,
  CtaWA,
  GarisLaju,
  IkonBebas,
  Judul,
  Kamera,
  KartuFitur,
  Label,
  Latar,
  Motor,
  Pemandangan,
  PetaRute,
  Sapuan,
  Stiker,
  Ikon,
  useData,
  useDetik,
  waktuKata,
  waktuTiapKata,
  FONT_JUDUL,
} from '../../kit';

export const RentalGarut: React.FC = () => {
  const data = useData();
  const t = useDetik();
  const W = (teks: string, setelah = 0) => waktuKata(data, teks, setelah);
  const akhir = data.durasi;

  // batas adegan (pergantian tersembunyi di balik Sapuan)
  const s2 = W('tapi') - 0.08;
  const s3 = W('sewa') - 0.1;
  const s4 = W('motor', W('satu')) - 0.2;
  const s5 = W('harian') - 0.08;
  const s6 = W('mau ke Papandayan') - 0.2;
  const s7 = W('tinggal');
  const s8 = W('bebas') - 0.1;
  const s9 = W('harga') - 0.06;
  const s10 = W('helm') - 0.02;
  const s11 = W('booking') - 0.25;
  const s12 = W('Garut', W('layar')) - 0.05;

  const gas = W('gas');
  const motorMasuk = interpolate(t, [0, 0.9], [-420, 540], {extrapolateRight: 'clamp'});
  const motorBerhenti = interpolate(t, [s3, s3 + 0.7], [1500, 540], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const motorAntar = interpolate(t, [W('diantar'), W('penginapan') + 0.6], [-200, 1280], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill>
      {/* 1. HOOK — pemandangan + motor melaju masuk, teks hook sejak detik 0 */}
      <Adegan dari={0} sampai={s2}>
        <Kamera dari={0} sampai={s2} zoom={[1.02, 1.1]} fokus={[0.5, 0.65]}>
          <Pemandangan laju={520} />
          <Motor x={motorMasuk} y={1345} ukuran={620} laju={t < 0.9 ? 3 : 1.6} pengendara warna="merah" />
        </Kamera>
        <Judul baris={['Liburan', {teks: 'ke Garut?', warna: 'kuning', ukuran: 170}]} waktu={[-0.3, W('ke') - 0.1, W('Garut')]} y={640} ukuran={160} />
      </Adegan>

      {/* 2. Masalah — pusing transportasi → jangan ribet */}
      <Adegan dari={s2} sampai={s3}>
        <Kamera dari={s2} sampai={s3} hentak={[W('jangan'), W('ribet')]}>
          <Latar warna="merah" pola="sinar" kuatPola={0.12} />
          <IkonBebas nama="pusing" x={540} y={600} ukuran={330} mulai={W('pusing') - 0.1} warna="putih" />
          <IkonBebas nama="tanya" x={230} y={470} ukuran={150} mulai={W('transportasi')} warna="kuning" miring={-15} />
          <IkonBebas nama="tanya" x={860} y={520} ukuran={120} mulai={W('transportasi') + 0.2} warna="kuning" miring={12} />
          <Judul baris={[{teks: 'Pusing', ukuran: 150}, 'transportasi?']} waktu={waktuTiapKata(data, 'pusing transportasi')} y={960} ukuran={104} />
          <Cap teks="Jangan ribet!" x={540} y={1290} mulai={W('jangan')} warna="ungu" ukuran={112} />
        </Kamera>
      </Adegan>

      {/* 3. Solusi — sewa motor aja, Rental Motor No.1 */}
      <Adegan dari={s3} sampai={s4}>
        <Kamera dari={s3} sampai={s4} zoom={[1, 1.05]} hentak={[W('satu')]}>
          <Latar warna="hijau" pola="titik" />
          <Motor x={motorBerhenti} y={1300} ukuran={760} laju={t < s3 + 0.7 ? 2.5 : 0} warna="merah" arah={-1} miring={t < s3 + 0.7 ? 0 : -2 * Math.max(0, Math.sin((t - s3 - 0.7) * 12)) * Math.exp(-(t - s3 - 0.7) * 4)} />
          <Judul baris={['Sewa motor', {teks: 'aja!', warna: 'kuning', ukuran: 190}]} waktu={waktuTiapKata(data, 'sewa motor aja')} sampai={W('Rental') - 0.25} y={560} ukuran={140} />
          <Judul
            baris={['Rental Motor', {teks: 'Garut No.1', warna: 'kuning', ukuran: 150}]}
            waktu={[W('Rental'), W('Rental') + 0.15, W('Garut', W('Rental')), W('nomor')]}
            y={560}
            ukuran={120}
          />
        </Kamera>
      </Adegan>

      {/* 4. Keunggulan unit — bersih, terawat, siap jalan; matic & manual */}
      <Adegan dari={s4} sampai={s5}>
        <Kamera dari={s4} sampai={s5} zoom={[1, 1.04]}>
          <Latar warna="ungu" pola="kotak" kuatPola={0.1} />
          <Motor x={540} y={830} ukuran={560} warna="merah" />
          <IkonBebas nama="kilau" x={300} y={500} ukuran={120} mulai={W('bersih')} warna="kuning" />
          <IkonBebas nama="kilau" x={820} y={560} ukuran={90} mulai={W('bersih') + 0.15} warna="kuning" />
          <KartuFitur ikon="kilau" warnaIkon="kuning" teks="Selalu bersih" y={1010} mulai={W('motor', s4)} sampai={W('ada') - 0.2} />
          <KartuFitur ikon="kunci" warnaIkon="hijau" teks="Mesin terawat" y={1185} mulai={W('mesin')} sampai={W('ada') - 0.2} miring={1.5} />
          <KartuFitur ikon="cek" warnaIkon="hijau" teks="Siap jalan" y={1360} mulai={W('siap')} sampai={W('ada') - 0.2} miring={-1.5} />
          <Label teks="Matic" x={400} y={1060} mulai={W('matic')} warna="kuning" ukuran={120} miring={-6} />
          <Label teks="&" x={560} y={1200} mulai={W('dan', W('matic'))} warna="putih" ukuran={80} />
          <Label teks="Manual" x={680} y={1340} mulai={W('manual')} warna="hijau" warnaTeks="putih" ukuran={120} miring={5} />
        </Kamera>
      </Adegan>

      {/* 5. Harian / mingguan */}
      <Adegan dari={s5} sampai={s6}>
        <Kamera dari={s5} sampai={s6} hentak={[W('mingguan')]}>
          <Latar warna="kuning" pola="garis" warnaPola="putih" kuatPola={0.35} />
          <IkonBebas nama="kalender" x={540} y={720} ukuran={420} mulai={s5} warna="merah" />
          <Label teks="Harian" x={330} y={1140} mulai={W('harian')} warna="hijau" warnaTeks="putih" ukuran={110} miring={-5} />
          <Label teks="Mingguan" x={720} y={1330} mulai={W('mingguan')} warna="ungu" warnaTeks="putih" ukuran={110} miring={4} />
        </Kamera>
      </Adegan>

      {/* 6. Destinasi — peta skematis (arah kira-kira) */}
      <Adegan dari={s6} sampai={s7}>
        <Kamera dari={s6} sampai={s7} zoom={[1, 1.05]}>
          <Latar warna="ungu" pola="titik" />
          <PetaRute
            mulai={s6}
            asal={{nama: 'Garut', x: 560, y: 860, mulai: s6 + 0.1}}
            tujuan={[
              {nama: 'Papandayan', x: 330, y: 1120, mulai: W('mau ke Papandayan'), warna: 'merah'},
              {nama: 'Darajat', x: 290, y: 620, mulai: W('Darajat'), warna: 'ungu'},
              {nama: 'Sayang Heulang', x: 680, y: 1400, mulai: W('Sayang'), warna: 'hijau'},
            ]}
          />
        </Kamera>
      </Adegan>

      {/* 7. Tinggal gas! */}
      <Adegan dari={s7} sampai={s8}>
        <Kamera dari={s7} sampai={s8} zoom={[1.08, 1.0]} hentak={[gas]}>
          <Pemandangan laju={1500} />
          <GarisLaju dari={s7} sampai={s8} />
          <Motor x={540} y={1345} ukuran={680} laju={4} pengendara warna="merah" miring={-4} />
          <Judul baris={['Tinggal', {teks: 'gas!', warna: 'kuning', ukuran: 230}]} waktu={[s7, gas]} y={640} ukuran={150} />
        </Kamera>
      </Adegan>

      {/* 8. Bebas atur waktu */}
      <Adegan dari={s8} sampai={s9}>
        <Kamera dari={s8} sampai={s9}>
          <Latar warna="hijau" pola="sinar" kuatPola={0.12} />
          <IkonBebas nama="jam" x={540} y={680} ukuran={420} mulai={s8} warna="kuning" />
          <Judul baris={['Bebas atur', {teks: 'waktu sendiri', warna: 'kuning'}]} waktu={waktuTiapKata(data, 'bebas atur waktu sendiri')} y={1170} ukuran={120} />
        </Kamera>
      </Adegan>

      {/* 9. Harga bersahabat, proses cepat (tanpa angka harga — tidak dikarang) */}
      <Adegan dari={s9} sampai={s10}>
        <Kamera dari={s9} sampai={s10} hentak={[W('cepat')]}>
          <Latar warna="krem" pola="titik" warnaPola="kuning" kuatPola={0.5} />
          <KartuFitur ikon="tagHarga" warnaIkon="merah" teks="Harga bersahabat" y={760} mulai={W('harga')} dariArah="kiri" miring={-2} ukuranTeks={70} lebar={900} />
          <KartuFitur ikon="kilat" warnaIkon="kuning" teks="Proses cepat" y={1080} mulai={W('proses')} dariArah="kanan" miring={2} warna="ungu" warnaTeks="putih" ukuranTeks={70} lebar={900} />
        </Kamera>
      </Adegan>

      {/* 10. Bonus helm + jas hujan, diantar ke stasiun / penginapan */}
      <Adegan dari={s10} sampai={s11}>
        <Kamera dari={s10} sampai={s11} hentak={[W('gratis')]}>
          <Latar warna="hijau" pola="garis" kuatPola={0.1} />
          <Stiker x={300} y={620} mulai={W('helm')} lebar={330} tinggi={330} miring={-4}>
            <Ikon nama="helm" ukuran={250} warna="merah" />
          </Stiker>
          <Stiker x={780} y={620} mulai={W('jas hujan')} lebar={330} tinggi={330} miring={4}>
            <Ikon nama="jasHujan" ukuran={250} warna="kuning" />
          </Stiker>
          <Cap teks="Gratis!" x={540} y={870} mulai={W('gratis')} ukuran={130} />
          <Label teks="Bisa diantar ke" x={540} y={1060} mulai={W('diantar')} warna="putih" ukuran={64} />
          <Stiker x={300} y={1270} mulai={W('stasiun')} lebar={420} padding={18} warna="krem" miring={-2}>
            <Ikon nama="kereta" ukuran={120} warna="ungu" />
            <span style={{fontFamily: FONT_JUDUL, fontWeight: 800, fontSize: 52, textTransform: 'uppercase'}}>Stasiun</span>
          </Stiker>
          <Stiker x={780} y={1270} mulai={W('penginapan')} lebar={460} padding={18} warna="krem" miring={2}>
            <Ikon nama="rumah" ukuran={120} warna="merah" />
            <span style={{fontFamily: FONT_JUDUL, fontWeight: 800, fontSize: 48, textTransform: 'uppercase'}}>Penginapan</span>
          </Stiker>
          <Motor x={motorAntar} y={1490} ukuran={300} laju={3} pengendara warna="merah" />
        </Kamera>
      </Adegan>

      {/* 11. CTA WhatsApp (nomor dari brand.yaml) */}
      <Adegan dari={s11} sampai={s12}>
        <Kamera dari={s11} sampai={s12} zoom={[1, 1.03]}>
          <Latar warna="ungu" pola="sinar" kuatPola={0.14} />
          <CtaWA mulai={W('booking') - 0.15} y={900} judul="Booking sekarang!" />
          <IkonBebas nama="tangan" x={880} y={1390} ukuran={200} mulai={W('layar') - 0.4} warna="kuning" miring={-25} />
        </Kamera>
      </Adegan>

      {/* 12. Penutup — Garut lebih seru pakai motor + nomor tetap tampil */}
      <Adegan dari={s12} sampai={akhir + 1}>
        <Kamera dari={s12} sampai={akhir} zoom={[1.0, 1.08]} fokus={[0.5, 0.7]} hentak={[W('1', W('nomor', W('Rental', s12)))]}>
          <Pemandangan laju={380} senja />
          <Motor x={540} y={1345} ukuran={600} laju={2} pengendara warna="merah" />
          <Judul
            baris={['Garut lebih seru', {teks: 'pakai motor!', warna: 'kuning'}]}
            waktu={waktuTiapKata(data, 'Garut lebih seru pakai motor', s12)}
            sampai={W('Rental', s12) - 0.25}
            y={600}
            ukuran={118}
          />
          <Judul
            baris={['Rental Motor', {teks: 'Garut No.1', warna: 'kuning', ukuran: 150}]}
            waktu={[W('Rental', s12), W('Rental', s12) + 0.2, W('nomor', s12), W('1', s12)]}
            y={600}
            ukuran={120}
          />
        </Kamera>
        <Label teks={`WA ${data.brand.whatsapp}`} x={540} y={1470} mulai={s12 + 0.3} warna="hijau" warnaTeks="putih" ukuran={60} />
      </Adegan>

      {/* transisi khas di tiap pergantian adegan */}
      {[s2, s3, s4, s5, s6, s8, s9, s10, s11, s12].map((p, i) => (
        <Sapuan key={p} pada={p} warna={i % 2 ? ['hijau', 'kuning', 'ungu'] : ['kuning', 'merah', 'ungu']} />
      ))}
    </AbsoluteFill>
  );
};
