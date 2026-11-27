import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Play, Search, RotateCcw } from 'lucide-react';
import { Segmented, cx } from './ui.jsx';
import { formatSec } from '../lib/format.js';

/** Indeks frasa yang sedang terdengar pada detik `t` (atau null). */
export function phraseAt(phrases, t) {
  if (t == null) return null;
  const i = phrases.findIndex((p) => t >= p.start && t < p.end);
  return i >= 0 ? i : null;
}

const Row = memo(function Row({ phrase, i, value, active, onEdit, onPlay, register }) {
  const edited = value !== phrase.text;
  return (
    <li ref={(el) => register(i, el)} className={cx('flex items-start gap-2 px-2 py-1.5', active && 'bg-brand-soft/60')}>
      <button
        type="button"
        onClick={() => onPlay(phrase)}
        aria-label={`Putar frasa ${i + 1} di ${formatSec(phrase.start)} detik`}
        className={cx(
          'mt-1 flex w-16 shrink-0 items-center gap-1 rounded px-1 py-0.5 text-[12px] num',
          active ? 'text-brand font-semibold' : 'text-muted hover:text-ink'
        )}
      >
        <Play className="w-3 h-3" aria-hidden="true" />
        {formatSec(phrase.start)}
      </button>
      <div className="min-w-0 flex-1">
        <input
          type="text"
          value={value}
          onChange={(e) => onEdit(i, e.target.value)}
          aria-label={`Frasa ${i + 1}`}
          className={cx(
            'w-full rounded-md border bg-transparent px-2 py-1 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand',
            edited ? 'border-brand' : 'border-transparent hover:border-line'
          )}
        />
        {phrase.ai_fixed && phrase.original && phrase.original !== value && (
          <p className="mt-0.5 flex items-center gap-2 px-2 text-[12px] text-muted">
            <span className="truncate">{`Asli: ${phrase.original}`}</span>
            <button
              type="button"
              onClick={() => onEdit(i, phrase.original)}
              className="inline-flex shrink-0 items-center gap-1 underline hover:text-ink"
            >
              <RotateCcw className="w-3 h-3" aria-hidden="true" />
              pakai asli
            </button>
          </p>
        )}
      </div>
    </li>
  );
});

/**
 * Editor subtitle per frasa yang ringkas: kotak setinggi tetap (halaman tidak memanjang), saring
 * Perlu dicek / Diubah / Semua, cari kata, dan baris yang sedang terdengar menyala + ikut bergulir.
 *
 * phrases: [{ index, start, end, text, original?, ai_fixed? }] — values: teks saat ini per frasa (urutan sama)
 * onChange(i, teks) · onPlay(phrase) · activeIndex: frasa yang sedang diputar (atau null)
 */
export default function PhraseEditor({ phrases, values, onChange, onPlay, activeIndex = null, label = 'Subtitle' }) {
  const flagged = useMemo(() => phrases.filter((p) => p.ai_fixed).length, [phrases]);
  const changed = phrases.reduce((n, p, i) => n + (values[i] !== p.text ? 1 : 0), 0);
  const [filter, setFilter] = useState(() => (flagged ? 'cek' : 'semua'));
  const [query, setQuery] = useState('');
  const [follow, setFollow] = useState(true);
  const boxRef = useRef(null);
  const rowRefs = useRef(new Map());

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return phrases
      .map((p, i) => ({ p, i }))
      .filter(({ p, i }) => (filter === 'cek' ? p.ai_fixed : filter === 'diubah' ? values[i] !== p.text : true))
      .filter(({ p, i }) => !q || values[i].toLowerCase().includes(q) || (p.original || '').toLowerCase().includes(q));
  }, [phrases, values, filter, query]);

  const handleEdit = useCallback((i, text) => onChange(i, text), [onChange]);
  const handlePlay = useCallback((p) => onPlay(p), [onPlay]);
  const registerRow = useCallback((i, el) => (el ? rowRefs.current.set(i, el) : rowRefs.current.delete(i)), []);

  // gulir di dalam kotak saja ke frasa yang sedang terdengar (halaman tidak ikut melompat)
  useEffect(() => {
    if (!follow || activeIndex === null) return undefined;
    const box = boxRef.current;
    const row = rowRefs.current.get(activeIndex);
    if (!box || !row) return undefined;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const frame = requestAnimationFrame(() =>
      box.scrollTo({ top: row.offsetTop - box.clientHeight / 2 + row.clientHeight / 2, behavior: reduce ? 'auto' : 'smooth' })
    );
    return () => cancelAnimationFrame(frame);
  }, [activeIndex, follow]);

  const options = [
    ...(flagged ? [{ id: 'cek', label: `Perlu dicek ${flagged}` }] : []),
    { id: 'diubah', label: `Diubah ${changed}` },
    { id: 'semua', label: `Semua ${phrases.length}` }
  ];
  const emptyText =
    filter === 'cek' ? 'Tidak ada lagi yang perlu dicek.' : filter === 'diubah' ? 'Belum ada yang diubah.' : 'Tidak ada yang cocok.';

  return (
    <div className="rounded-lg border border-line bg-surface">
      <div className="flex flex-wrap items-center gap-2 border-b border-line p-2">
        <Segmented label={`Saring ${label.toLowerCase()}`} size="sm" value={filter} onChange={setFilter} options={options} />
        <label className="relative min-w-[9rem] flex-1">
          <span className="sr-only">Cari kata</span>
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Cari kata"
            className="w-full rounded-md border border-line bg-sunken py-1.5 pl-8 pr-2 text-[13px] text-ink focus:outline-none focus:ring-2 focus:ring-brand"
          />
        </label>
        <label className="flex cursor-pointer select-none items-center gap-1.5 text-[13px] text-muted">
          <input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} className="accent-[rgb(var(--brand))]" />
          Ikuti suara
        </label>
      </div>
      <ol ref={boxRef} aria-label={label} className="scroll-thin relative max-h-[22rem] divide-y divide-line overflow-y-auto">
        {visible.length === 0 && <li className="px-3 py-6 text-center text-[13px] text-muted">{emptyText}</li>}
        {visible.map(({ p, i }) => (
          <Row
            key={p.index}
            phrase={p}
            i={i}
            value={values[i]}
            active={i === activeIndex}
            onEdit={handleEdit}
            onPlay={handlePlay}
            register={registerRow}
          />
        ))}
      </ol>
    </div>
  );
}
