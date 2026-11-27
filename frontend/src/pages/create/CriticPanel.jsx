import React from 'react';
import { cx } from '../../components/ui.jsx';

// urutan & nama aspek sama dengan autoreels/critic.py (LABELS)
const ASPECTS = [
  ['hook', 'Kekuatan hook'],
  ['instruction_fit', 'Kesesuaian instruksi & pilar'],
  ['flow', 'Alur / koherensi'],
  ['pace', 'Tempo sesuai gaya'],
  ['text_readability', 'Keterbacaan teks'],
  ['cta', 'Kejelasan CTA'],
  ['brand', 'Konsistensi brand']
];

function ScoreBar({ value }) {
  return (
    <span className="flex items-center gap-1" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={cx('h-2 w-5 rounded-sm', n <= value ? (value >= 4 ? 'bg-go' : 'bg-stop') : 'bg-line')}
        />
      ))}
    </span>
  );
}

/** Tab "Penilaian AI": skor rubrik Critic (1–5), catatan, dan riwayat putaran revisi. */
export default function CriticPanel({ critic }) {
  const final = critic?.final;
  if (!final) {
    return (
      <p className="text-sm text-muted border-t border-line pt-4">
        Penilaian Critic tidak tersedia untuk video ini (dibuat sebelum Critic aktif, dilewati, atau AI sedang tidak
        bisa dihubungi). Periksa hook dan alur secara manual.
      </p>
    );
  }
  const rounds = critic.rounds || [];
  return (
    <div className="border-t border-line pt-5 space-y-6">
      <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
        <div>
          <p className="font-display font-bold text-4xl leading-none text-ink num">
            {final.average.toFixed(1)}
            <span className="ml-1 text-base text-muted">/5</span>
          </p>
          <p className="mt-1 text-[13px] text-muted">rata-rata rubrik</p>
        </div>
        <p className={cx('text-sm font-semibold', final.passed ? 'text-go-text' : 'text-stop-text')}>
          {final.passed ? 'Lolos penilaian Critic' : 'Di bawah standar (hook < 4 atau rata-rata < 4)'}
        </p>
      </div>

      <ul className="space-y-2.5">
        {ASPECTS.map(([key, label]) => {
          const v = final.scores?.[key];
          if (v == null) return null;
          return (
            <li key={key} className="flex items-center justify-between gap-4 text-sm">
              <span className="text-ink">{label}</span>
              <span className="flex items-center gap-3">
                <ScoreBar value={v} />
                <span className="w-4 text-right font-semibold text-ink num" aria-label={`${label}: ${v} dari 5`}>
                  {v}
                </span>
              </span>
            </li>
          );
        })}
      </ul>

      {(final.summary || final.hook_comment) && (
        <div className="space-y-1.5 text-sm">
          {final.summary && <p className="text-ink">{final.summary}</p>}
          {final.hook_comment && <p className="text-muted">Hook: {final.hook_comment}</p>}
        </div>
      )}

      {final.revision_notes?.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-ink mb-1.5">Saran yang belum diterapkan</p>
          <ul className="list-disc pl-5 space-y-1 text-sm text-muted">
            {final.revision_notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}

      {rounds.length > 1 && (
        <div>
          <p className="text-sm font-semibold text-ink mb-1.5">Riwayat revisi</p>
          <ol className="space-y-1 text-[13px] text-muted num">
            {rounds.map((r) => (
              <li key={r.round}>
                {`Putaran ${r.round + 1}: rata-rata ${r.average.toFixed(1)}, hook ${r.hook}`}
                {r.round === critic.chosen_round && <span className="ml-1.5 font-semibold text-go-text">dipakai</span>}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
