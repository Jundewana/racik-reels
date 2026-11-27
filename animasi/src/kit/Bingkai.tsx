// Pembungkus tiap video: memuat data.json (lewat calculateMetadata), font brand, narasi + musik (ducking).
import {loadFont} from '@remotion/fonts';
import {Audio} from '@remotion/media';
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, interpolate, staticFile} from 'remotion';
import {DataCtx, sedangBicara, VideoData} from './data';
import {Tekstur} from './Panggung';
import {FONT_ISI, FONT_JUDUL, GAYA, WARNA, pakaiGaya} from './tema';

/** Font gaya aktif (disalin `autoreels animasi prepare` ke public/_brand/fonts/). */
const muatFont = () =>
  Promise.all([
    loadFont({family: FONT_JUDUL, url: staticFile(`_brand/fonts/${GAYA.font.judul}`), weight: String(GAYA.huruf.berat)}),
    loadFont({family: FONT_ISI, url: staticFile(`_brand/fonts/${GAYA.font.isi}`), weight: '600'}),
  ]);

const dbKeLinear = (db: number) => Math.pow(10, db / 20);

/** Musik (+ trek efek suara tanpa ducking): −musik_db di bawah ucapan, naik 5 dB saat jeda & setelah narasi selesai, fade in/out. */
const Suara: React.FC<{data: VideoData}> = ({data}) => {
  const fps = data.fps;
  const dasar = dbKeLinear(data.audio.musik_db);
  const lepas = dbKeLinear(data.audio.musik_db + 5);
  return (
    <>
      {data.audio.narasi ? <Audio src={staticFile(data.audio.narasi)} /> : null}
      {data.audio.musik ? (
        <Audio
          src={staticFile(data.audio.musik)}
          loop
          volume={(f) => {
            const t = f / fps;
            const v = sedangBicara(data, t, 0.25) ? dasar : lepas;
            const fade = interpolate(t, [0, 0.4, data.durasi - 1.2, data.durasi], [0, 1, 1, 0], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return v * fade;
          }}
        />
      ) : null}
      {data.audio.sfx ? <Audio src={staticFile(data.audio.sfx)} volume={dbKeLinear(data.audio.sfx_db ?? -10)} /> : null}
    </>
  );
};

/** gaya: override gaya untuk render/pratinjau (null = pakai data.gaya). */
export type BingkaiProps = {id: string; data: VideoData | null; gaya?: string | null};

export const Bingkai: React.FC<BingkaiProps & {isi: React.FC}> = ({data, gaya, isi: Isi}) => {
  pakaiGaya(gaya || data?.gaya); // sebelum anak dirender: semua token kit membaca gaya ini
  const [handle] = useState(() => delayRender('Memuat font gaya'));
  const [fontSiap, setFontSiap] = useState(false);
  useEffect(() => {
    if (!data) return;
    muatFont()
      .then(() => {
        setFontSiap(true); // isi dirender setelah font siap (teks di kanvas/3D memakai font yang benar)
        continueRender(handle);
      })
      .catch((e) => cancelRender(e));
  }, [data, gaya, handle]);
  if (!data || !fontSiap) return null;
  return (
    <DataCtx.Provider value={data}>
      <AbsoluteFill style={{backgroundColor: WARNA.krem, fontFamily: FONT_ISI, overflow: 'hidden'}}>
        <Isi />
        {data.mode === 'footage' ? null : <Tekstur />}
        <Suara data={data} />
      </AbsoluteFill>
    </DataCtx.Provider>
  );
};
