import React from 'react';
import { cx } from '../../components/ui.jsx';

/** Cek visual video jadi (autoreels/review.py): AI melihat frame reel.mp4 setelah render. */
export default function VisualReviewPanel({ visual }) {
  if (!visual) return null;
  if (visual.error) {
    return (
      <section aria-labelledby="visual-title" className="border-t border-line pt-5">
        <h3 id="visual-title" className="text-sm font-semibold text-ink">Cek visual video jadi</h3>
        <p className="mt-1 text-sm text-muted">
          Tidak tersedia (AI tidak bisa dihubungi). Tonton videonya sekali sebelum posting.
        </p>
      </section>
    );
  }
  const frames = Object.fromEntries((visual.frames || []).map((f) => [f.frame, f]));
  const issues = [...(visual.issues || [])].sort((a, b) => (a.severity === b.severity ? a.frame - b.frame : a.severity === 'berat' ? -1 : 1));
  const severe = issues.some((x) => x.severity === 'berat');
  return (
    <section aria-labelledby="visual-title" className="border-t border-line pt-5 space-y-4">
      <div className="flex flex-wrap items-end gap-x-8 gap-y-2">
        <div>
          <h3 id="visual-title" className="text-sm font-semibold text-ink">Cek visual video jadi</h3>
          <p className="mt-0.5 text-[13px] text-muted">AI melihat frame dari video yang sudah dirender.</p>
        </div>
        <p className="font-display font-bold text-3xl leading-none text-ink num">
          {visual.score}
          <span className="ml-1 text-base text-muted">/5</span>
        </p>
        <p className={cx('text-sm font-semibold', severe ? 'text-stop-text' : 'text-go-text')}>
          {severe ? 'Ada masalah berat' : issues.length ? 'Hanya catatan ringan' : 'Tidak ada masalah'}
        </p>
      </div>
      {visual.summary && <p className="text-sm text-ink" translate="no">{visual.summary}</p>}
      {issues.length > 0 && (
        <ul className="space-y-2">
          {issues.map((x) => (
            <li key={`${x.frame}-${x.problem}`} className="rounded-lg border border-line px-3.5 py-2.5 text-sm">
              <p className="flex flex-wrap items-center gap-x-2 text-[13px] text-muted">
                <span className={cx('font-semibold', x.severity === 'berat' ? 'text-stop-text' : 'text-ink')}>
                  {x.severity === 'berat' ? 'Berat' : 'Ringan'}
                </span>
                <span>Frame {x.frame}</span>
                {frames[x.frame] && <span className="num">detik {frames[x.frame].sec.toFixed(1)}</span>}
              </p>
              <p className="mt-0.5 text-ink" translate="no">{x.problem}</p>
              {x.fix && <p className="mt-0.5 text-[13px] text-muted" translate="no">{x.fix}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
