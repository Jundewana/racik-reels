import React from 'react';
import { Cloud, Cpu } from 'lucide-react';
import { useStudio } from '../state/studio.jsx';
import { ChoiceTile, cx } from './ui.jsx';

const ICONS = { api: Cloud, local: Cpu };
const NOTES = {
  api: 'Lebih pintar dan cepat, tapi bisa kena batas kuota harian.',
  local: 'Jalan di GPU laptop: tanpa kuota dan biaya, tapi lebih lambat dan hasilnya bisa kurang rapi. Untuk uji coba.'
};

/** Pilih mesin AI per job: API online (default) atau model lokal Ollama. */
export default function EngineChoice({ value, onChange }) {
  const { options } = useStudio();
  const engines = options.engines || [];
  if (!engines.length) return null;
  return (
    <div role="radiogroup" aria-label="Mesin AI" className="grid sm:grid-cols-2 gap-3">
      {engines.map((e) => {
        const Icon = ICONS[e.id] || Cloud;
        const selected = value === e.id;
        return (
          <ChoiceTile
            key={e.id}
            selected={selected}
            onClick={() => e.available && onChange(e.id)}
            aria-disabled={!e.available}
            className={cx(!e.available && 'opacity-60 cursor-not-allowed hover:border-line')}
          >
            <span className="flex items-center gap-2">
              <Icon className={cx('w-4 h-4', selected ? 'text-brand' : 'text-muted')} aria-hidden="true" />
              <span className="font-display font-bold text-xl leading-tight text-ink">{e.label}</span>
            </span>
            <span className="mt-1 block text-[13px] leading-snug text-muted">{NOTES[e.id]}</span>
            <span className="mt-2 block text-[13px] text-ink break-words">
              Teks: {e.llm}
              <br />
              Gambar: {e.vision}
            </span>
            {!e.available && e.reason && (
              <span className="mt-2 block text-[13px] font-semibold text-stop-text">{e.reason}</span>
            )}
          </ChoiceTile>
        );
      })}
    </div>
  );
}

export const engineLabel = (options, id) => (options.engines || []).find((e) => e.id === id)?.label || id;
