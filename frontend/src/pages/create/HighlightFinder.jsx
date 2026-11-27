import React, { useEffect, useState } from 'react';
import { Scissors, Play, X as XIcon, RotateCcw } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { Button, cx } from '../../components/ui.jsx';
import { formatLength as length } from '../../lib/format.js';

const clock = (sec) => {
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = String(s % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${r}` : `${m}:${r}`;
};
/**
 * Video bicara yang panjang (podcast, kuliah): AI mencari semua bagian 1–3 menit (maks 20) yang berdiri sendiri,
 * pengguna mencentang beberapa, lalu tiap bagian jadi satu Reel (antre, satu per satu).
 */
export default function HighlightFinder({ clip }) {
  const { highlight, startHighlights, highlightRanks: checked, setHighlightRanks: setChecked } =
    useStudio();
  const [previewRank, setPreviewRank] = useState(null);
  const [query, setQuery] = useState('');
  const state = highlight?.state;
  const cands = highlight?.candidates || [];
  const q = query.trim().toLowerCase();
  const shown = q ? cands.filter((c) => `${c.title} ${c.reason} ${c.preview}`.toLowerCase().includes(q)) : cands;

  useEffect(() => {
    if (state === 'selesai') setChecked(cands.filter((c) => c.score >= 4).slice(0, 3).map((c) => c.rank));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, cands.length]);

  const toggle = (rank) => setChecked((prev) => (prev.includes(rank) ? prev.filter((r) => r !== rank) : [...prev, rank]));

  return (
    <div className="mt-4 rounded-lg border border-line bg-surface p-4">
      <p className="text-sm font-semibold text-ink">
        {`Video ini ${length(clip.duration)}, terlalu panjang untuk satu Reel.`}
      </p>
      <p className="mt-1 text-[13px] text-muted">
        AI mencarikan semua bagian 1–3 menit yang menarik dan utuh (maks 20), skor tertinggi di atas. Tiap bagian yang Anda centang jadi satu Reel.
      </p>

      {!highlight && (
        <div className="mt-3">
          <Button variant="brand" size="sm" icon={Scissors} onClick={() => startHighlights()}>
            Cari cuplikan terbaik
          </Button>
          <p className="mt-1.5 text-[13px] text-muted">Transkripsi pertama ±13 menit per jam video; setelah itu tersimpan.</p>
        </div>
      )}

      {state === 'berjalan' && (
        <div className="mt-3" role="status" aria-live="polite">
          <div className="h-2 rounded-full bg-sunken overflow-hidden">
            <div className="h-full bg-brand transition-[width] duration-500" style={{ width: `${highlight.percent || 0}%` }} />
          </div>
          <p className="mt-1.5 text-[13px] text-muted num">{`${highlight.percent || 0}%, ${highlight.detail || ''}`}</p>
        </div>
      )}

      {state === 'gagal' && (
        <div className="mt-3">
          <p className="text-[13px] text-stop-text">{highlight.error || 'Pencarian cuplikan gagal.'}</p>
          <Button variant="secondary" size="sm" icon={RotateCcw} className="mt-2" onClick={() => startHighlights()}>
            Cari lagi
          </Button>
        </div>
      )}

      {state === 'selesai' && (
        <div className="mt-3">
          {cands.length === 0 ? (
            <p className="text-[13px] text-muted">Tidak ada bagian yang cukup utuh untuk dijadikan Reel.</p>
          ) : (
            <>
            {cands.length > 8 && (
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={`Cari di ${cands.length} cuplikan (judul/isi)…`}
                aria-label="Cari cuplikan"
                className="field mb-2 w-full"
              />
            )}
            <ul className="max-h-[30rem] overflow-y-auto divide-y divide-line border-y border-line">
              {shown.length === 0 && <li className="py-3 px-1 text-[13px] text-muted">Tidak ada cuplikan yang cocok.</li>}
              {shown.map((c) => {
                const on = checked.includes(c.rank);
                return (
                  <li key={c.rank} className={cx('py-3', on && 'bg-brand-soft/40')}>
                    <div className="flex items-start gap-3 px-1">
                      <input
                        id={`cup-${c.rank}`}
                        type="checkbox"
                        checked={on}
                        onChange={() => toggle(c.rank)}
                        className="mt-1 w-4 h-4 accent-[rgb(var(--brand))] shrink-0"
                      />
                      <label htmlFor={`cup-${c.rank}`} className="min-w-0 flex-1 cursor-pointer">
                        <span className="block text-sm font-semibold text-ink" translate="no">{c.title}</span>
                        <span className="block text-[13px] text-muted num">
                          {`${clock(c.start)}–${clock(c.end)}, ${length(c.duration)}, skor ${c.score}/5`}
                        </span>
                        {c.reason && <span className="mt-0.5 block text-[13px] text-ink/80">{c.reason}</span>}
                      </label>
                      {highlight.video_url && (
                        <button
                          type="button"
                          onClick={() => setPreviewRank(previewRank === c.rank ? null : c.rank)}
                          aria-label={previewRank === c.rank ? `Tutup pratinjau ${c.title}` : `Putar ${c.title}`}
                          aria-expanded={previewRank === c.rank}
                          className="shrink-0 grid place-items-center w-8 h-8 rounded-md border border-line text-muted hover:text-ink"
                        >
                          {previewRank === c.rank ? <XIcon className="w-3.5 h-3.5" aria-hidden="true" /> : <Play className="w-3.5 h-3.5" aria-hidden="true" />}
                        </button>
                      )}
                    </div>
                    {previewRank === c.rank && (
                      <video
                        src={`${highlight.video_url}#t=${c.start},${c.end}`}
                        controls
                        autoPlay
                        preload="metadata"
                        className="mt-2 w-full max-h-72 rounded-md bg-black"
                      />
                    )}
                  </li>
                );
              })}
            </ul>
            </>
          )}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-[13px] text-ink" aria-live="polite">
              {checked.length
                ? `${checked.length} cuplikan dipilih. Lengkapi pengaturan di bawah, lalu klik "Buat ${checked.length} Reel" di Ringkasan.`
                : 'Centang cuplikan yang ingin dijadikan Reel.'}
            </p>
            <button
              type="button"
              onClick={() => startHighlights({ again: true })}
              title="Cari bagian lain (yang sudah tampil tidak diulang)"
              className="text-[13px] text-muted underline underline-offset-4 hover:text-ink"
            >
              Cari ulang
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
