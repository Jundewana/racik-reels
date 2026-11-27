// Render banyak frame diam dengan SATU bundle (jauh lebih cepat daripada `remotion still` berulang).
// Pakai: node scripts/stills.mjs <id-komposisi> <folder-keluaran> '<json [[frame, "nama.jpg", gaya?], ...]>' [skala]
// gaya (opsional per frame) = override gaya untuk pratinjau tanpa mengubah data.json.
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';

const [, , id, outDir, daftarJson, skala = '0.5'] = process.argv;
const daftar = JSON.parse(daftarJson);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const chromiumOptions = {gl: 'angle'};
const komposisi = new Map();
for (const [frame, nama, gaya = ''] of daftar) {
  if (!komposisi.has(gaya)) {
    const inputProps = gaya ? {gaya} : {};
    komposisi.set(gaya, await selectComposition({serveUrl, id, inputProps, chromiumOptions}));
  }
  const composition = komposisi.get(gaya);
  await renderStill({
    composition,
    serveUrl,
    frame,
    output: path.join(outDir, nama),
    scale: Number(skala),
    imageFormat: 'jpeg',
    jpegQuality: 90,
    inputProps: composition.props,
    chromiumOptions,
  });
  console.log(`frame ${frame} ${gaya} -> ${nama}`);
}
