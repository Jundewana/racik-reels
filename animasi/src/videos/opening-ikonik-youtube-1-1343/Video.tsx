import { AbsoluteFill, Sequence, useVideoConfig } from 'remotion';
import { useData, Klip, Subtitle, TeksFootage } from '../../kit';

export const Video: React.FC = () => {
  const { fps } = useVideoConfig();
  const data = useData();
  const { frasa, pembicara, adegan } = data as any;

  return (
    <AbsoluteFill style={{ backgroundColor: 'black' }}>
      {/* Pembicara Utama */}
      {frasa.map((f: any, i: number) => {
        const adeganPembicara = adegan.find((a: any) => a.sumber === pembicara.nama);
        if (!adeganPembicara) return null;

        return (
          <Sequence key={i} from={Math.round(f.start * fps)} durationInFrames={Math.round((f.end - f.start) * fps)}>
            <Klip
              file={pembicara.file}
              mulai={f.src_start}
              durasi={f.end - f.start}
              mode="cover"
              cx={adeganPembicara.crop}
            />
          </Sequence>
        );
      })}

      {/* Subtitle Karaoke */}
      <Subtitle />

      {/* Hook di 3 detik pertama */}
      <Sequence from={0} durationInFrames={Math.round(3 * fps)}>
        <TeksFootage
          teks="Youtuber Gaming Nomor 1?"
          mulai={0}
          sampai={3}
          posisi="atas"
          warna="#FFC400"
        />
      </Sequence>
    </AbsoluteFill>
  );
};
