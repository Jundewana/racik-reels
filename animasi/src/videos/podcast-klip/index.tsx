// Entry terpisah untuk klip podcast (tidak mengubah src/Root.tsx Racik Animasi).
// Render: npx remotion render src/videos/podcast-klip/index.tsx PodcastKlip <out.mp4>
import React from 'react';
import {CalculateMetadataFunction, Composition, registerRoot, staticFile} from 'remotion';
import {KlipData, KlipProps, PodcastKlip} from './Klip';

const hitung: CalculateMetadataFunction<KlipProps> = async () => {
  const res = await fetch(staticFile('podcast-klip/klip.json'));
  if (!res.ok) throw new Error('public/podcast-klip/klip.json belum ada');
  const data = (await res.json()) as KlipData;
  return {durationInFrames: Math.ceil(data.durasi * data.fps), fps: data.fps, props: {data}};
};

const Root: React.FC = () => (
  <Composition
    id="PodcastKlip"
    component={PodcastKlip}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={300}
    defaultProps={{data: null}}
    calculateMetadata={hitung}
  />
);

registerRoot(Root);
