import React, { useMemo } from 'react';
import { segmentBlocks, formatSec } from '../../lib/format.js';
import { cx } from '../../components/ui.jsx';

/**
 * Strip struktur video: tiap segmen EDL digambar selebar durasinya.
 * Hook = kuning (sama dengan highlight teks di video), isi = ungu, CTA = hijau.
 * Klik blok → video lompat ke awal segmen. Garis tipis = posisi putar saat ini.
 */
const ROLE_LABEL = { hook: 'Hook', isi: 'Isi', bukti: 'Bukti', suasana: 'Suasana', cta: 'CTA' };

function blockClass(role, i) {
  if (role === 'hook') return 'bg-hook text-on-hook';
  if (role === 'cta') return 'bg-go text-on-go';
  return i % 2 ? 'bg-brand/80 text-on-brand' : 'bg-brand text-on-brand';
}

export default function SegmentStrip({ segments, hookText, ctaText, videoDuration, currentTime, onSeek }) {
  const blocks = useMemo(() => segmentBlocks(segments), [segments]);
  const total = blocks.length ? blocks[blocks.length - 1].to : 0;
  if (!blocks.length || !total) return null;

  // Skala ke durasi video sebenarnya (kecepatan segmen tidak dikirim API)
  const scale = videoDuration > 0 ? videoDuration / total : 1;
  const playhead = videoDuration > 0 ? Math.min(100, (currentTime / videoDuration) * 100) : 0;
  const shownTotal = videoDuration > 0 ? videoDuration : total;
  const tickStep = shownTotal > 40 ? 10 : 5;
  const ticks = [];
  for (let t = 0; t <= shownTotal + 0.01; t += tickStep) ticks.push(t);

  const textOf = (b) => (b.role === 'hook' ? hookText : b.role === 'cta' ? ctaText : b.overlay_text) || '';

  return (
    <figure className="min-w-0">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 mb-2.5">
        <span className="font-display font-bold text-xl text-ink">Struktur video</span>
        <span className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-muted">
          <span className="inline-flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-hook" aria-hidden="true" /> Hook
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-brand" aria-hidden="true" /> Isi
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm bg-go" aria-hidden="true" /> CTA
          </span>
          <span className="num">{`${blocks.length} segmen`}</span>
        </span>
      </figcaption>

      <div className="relative">
        <ol className="flex gap-[2px] h-14 strip-grow" aria-label="Segmen video, klik untuk memutar dari segmen itu">
          {blocks.map((b, i) => {
            const text = textOf(b);
            const from = b.from * scale;
            const to = b.to * scale;
            return (
              <li key={b.index} className="min-w-[6px]" style={{ flex: `${b.dur} 1 0%` }}>
                <button
                  type="button"
                  onClick={() => onSeek(from)}
                  title={`${ROLE_LABEL[b.role] || b.role}, ${formatSec(from)}–${formatSec(to)} dtk${text ? `: ${text}` : ''}`}
                  aria-label={`Segmen ${i + 1}, ${ROLE_LABEL[b.role] || b.role}, mulai ${formatSec(from)} detik${text ? `, teks: ${text}` : ''}`}
                  className={cx(
                    'w-full h-full flex flex-col justify-between overflow-hidden px-1.5 py-1 text-left transition-[filter] hover:brightness-110',
                    i === 0 && 'rounded-l-md',
                    i === blocks.length - 1 && 'rounded-r-md',
                    blockClass(b.role, i)
                  )}
                >
                  <span className="text-[11px] font-bold leading-none opacity-80 truncate">{ROLE_LABEL[b.role] || b.role}</span>
                  {text && <span className="text-[12px] font-semibold leading-tight truncate">{text}</span>}
                </button>
              </li>
            );
          })}
        </ol>
        {videoDuration > 0 && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute -top-1 -bottom-1 w-[2px] rounded-full bg-ink"
            style={{ left: `calc(${playhead}% - 1px)` }}
          />
        )}
      </div>

      <div className="relative h-5 mt-1 text-[11px] text-muted num" aria-hidden="true">
        {ticks.map((t) => {
          const pct = (t / shownTotal) * 100;
          // label di tepi kiri/kanan tidak boleh keluar dari strip (mencegah halaman melebar di HP)
          const shift = pct < 4 ? '' : pct > 92 ? '-translate-x-full' : '-translate-x-1/2';
          return (
            <span key={t} className={cx('absolute top-0 whitespace-nowrap', shift)} style={{ left: `${pct}%` }}>
              {`${Math.round(t)} dtk`}
            </span>
          );
        })}
      </div>
    </figure>
  );
}
