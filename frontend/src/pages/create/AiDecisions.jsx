import React, { useEffect, useRef } from 'react';
import { Sparkles } from 'lucide-react';
import { formatElapsed } from '../../lib/format.js';

/**
 * "Keputusan AI": catatan langsung dari pipeline (progress.notes) — kalimat yang dipilih, adegan terbaik,
 * hook & alasan tiap potongan dari Director, nilai Critic, perbaikan otomatis, cek visual.
 * Kotak setinggi tetap + gulir; catatan terbaru terbuka, yang lama dilipat.
 */
export default function AiDecisions({ notes = [], running }) {
  const boxRef = useRef(null);

  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight;
  }, [notes.length]);

  if (!notes.length) {
    return running ? (
      <section aria-labelledby="ai-dec-title" className="mt-10">
        <h2 id="ai-dec-title" className="flex items-center gap-2 text-sm font-semibold text-ink">
          <Sparkles className="w-4 h-4 text-brand" aria-hidden="true" /> Keputusan AI
        </h2>
        <p className="mt-2 text-sm text-muted">Keputusan AI akan muncul di sini begitu AI selesai menilai tiap langkah.</p>
      </section>
    ) : null;
  }

  return (
    <section aria-labelledby="ai-dec-title" className="mt-10">
      <h2 id="ai-dec-title" className="flex items-center gap-2 text-sm font-semibold text-ink">
        <Sparkles className="w-4 h-4 text-brand" aria-hidden="true" /> Keputusan AI
        <span className="text-muted font-normal">· {notes.length}</span>
      </h2>
      <div ref={boxRef} className="mt-3 max-h-96 overflow-y-auto border-y border-line" aria-live="polite">
        {notes.map((n, i) => (
          <details
            key={`${n.at}-${n.title}`}
            open={i === notes.length - 1}
            className="group border-b border-line last:border-b-0 py-2.5"
          >
            <summary className="flex cursor-pointer list-none items-baseline gap-3 text-sm">
              <span className="num text-[12px] text-muted w-11 shrink-0">{formatElapsed(n.at)}</span>
              <span className="font-semibold text-ink">{n.title}</span>
              {!!n.lines?.length && (
                <span className="ml-auto text-[12px] text-muted group-open:hidden">{n.lines.length} baris</span>
              )}
            </summary>
            {!!n.lines?.length && (
              <ul className="mt-1.5 ml-14 space-y-0.5 text-[13px] text-ink/90" translate="no">
                {n.lines.map((line, j) => (
                  <li key={j} className="break-words">
                    {line}
                  </li>
                ))}
              </ul>
            )}
          </details>
        ))}
      </div>
    </section>
  );
}
