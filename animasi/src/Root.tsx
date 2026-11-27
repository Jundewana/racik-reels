// Mendaftarkan semua video di src/videos/index.ts sebagai komposisi 1080×1920 @30 fps.
// Durasi & data diambil dari public/<id>/data.json (dibuat `autoreels animasi prepare`).
import React from 'react';
import {CalculateMetadataFunction, Composition, staticFile} from 'remotion';
import {Bingkai, BingkaiProps} from './kit/Bingkai';
import {VideoData} from './kit/data';
import {VIDEO} from './videos';

const hitungMetadata: CalculateMetadataFunction<BingkaiProps> = async ({props}) => {
  const res = await fetch(staticFile(`${props.id}/data.json`));
  if (!res.ok) throw new Error(`public/${props.id}/data.json belum ada — jalankan autoreels animasi prepare`);
  const data = (await res.json()) as VideoData;
  return {durationInFrames: Math.ceil(data.durasi * data.fps), fps: data.fps, props: {...props, data}};
};

// komponen dibuat sekali (stabil antar-render)
const KOMPONEN: Record<string, React.FC<BingkaiProps>> = Object.fromEntries(
  Object.entries(VIDEO).map(([id, Isi]) => [id, (p: BingkaiProps) => <Bingkai {...p} isi={Isi} />]),
);

export const Root: React.FC = () => (
  <>
    {Object.keys(VIDEO).map((id) => (
      <Composition
        key={id}
        id={id}
        component={KOMPONEN[id]}
        width={1080}
        height={1920}
        fps={30}
        durationInFrames={300}
        defaultProps={{id, data: null, gaya: null}}
        calculateMetadata={hitungMetadata}
      />
    ))}
  </>
);
