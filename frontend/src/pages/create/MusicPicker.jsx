import React, { useMemo, useState } from 'react';
import { Play, Square, ChevronDown } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { trackTitle } from '../../lib/format.js';
import { Segmented, cx } from '../../components/ui.jsx';

const MOOD_LABELS = { upbeat: 'Upbeat', santai: 'Santai', inspiratif: 'Inspiratif', dramatis: 'Dramatis' };
const moodLabel = (m) => MOOD_LABELS[m] || m.charAt(0).toUpperCase() + m.slice(1);

/**
 * Pemilih musik latar yang ringkas.
 * Bawaan: "Otomatis sesuai gaya" saja (pilihan kebanyakan orang). Daftar lagu dibuka lewat "Pilih lagu sendiri",
 * dikelompokkan per suasana (sesuai folder assets/music/<mood>/), satu baris per lagu dengan tombol putar ikon.
 */
export default function MusicPicker({ value, onChange, styleMood, noMusic = false, onNoMusic, silentHint }) {
  const { options, playingTrackPath, toggleMusicPreview, stopMusicPreview } = useStudio();
  const tracks = options.music || [];
  const moods = useMemo(() => {
    const counts = new Map();
    tracks.forEach((t) => counts.set(t.mood, (counts.get(t.mood) || 0) + 1));
    return [...counts.entries()];
  }, [tracks]);
  const chosen = tracks.find((t) => t.path === value);
  const [open, setOpen] = useState(Boolean(chosen));
  const [mood, setMood] = useState(
    chosen?.mood || (moods.some(([m]) => m === styleMood) ? styleMood : moods[0]?.[0])
  );
  const visible = tracks.filter((t) => t.mood === mood);

  const selectAuto = () => {
    stopMusicPreview();
    onNoMusic?.(false);
    onChange(null);
  };
  const selectNone = () => {
    stopMusicPreview();
    onChange(null);
    onNoMusic?.(true);
  };
  const auto = !value && !noMusic;

  return (
    <div role="radiogroup" aria-label="Musik latar">
      <label
        className={cx(
          'flex items-center gap-3 rounded-lg border px-3.5 py-3 cursor-pointer transition-colors',
          auto ? 'border-brand ring-1 ring-brand bg-brand-soft/60' : 'border-line bg-surface'
        )}
      >
        <input
          type="radio"
          name="music_choice"
          checked={auto}
          onChange={selectAuto}
          className="w-4 h-4 accent-[rgb(var(--brand))] shrink-0"
        />
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-ink">Otomatis sesuai gaya</span>
          <span className="block text-[13px] text-muted">
            {styleMood ? `Lagu ${moodLabel(styleMood).toLowerCase()} yang ketukannya paling pas dengan potongan` : 'Dipilih dari suasana gaya'}
          </span>
        </span>
      </label>

      <label
        className={cx(
          'mt-2 flex items-center gap-3 rounded-lg border px-3.5 py-3 cursor-pointer transition-colors',
          noMusic ? 'border-brand ring-1 ring-brand bg-brand-soft/60' : 'border-line bg-surface'
        )}
      >
        <input
          type="radio"
          name="music_choice"
          checked={noMusic}
          onChange={selectNone}
          className="w-4 h-4 accent-[rgb(var(--brand))] shrink-0"
        />
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-ink">Tanpa musik</span>
          <span className="block text-[13px] text-muted">{silentHint}</span>
        </span>
      </label>

      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="music-list"
        className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-ink hover:text-brand"
      >
        <ChevronDown className={cx('w-4 h-4 transition-transform', open && 'rotate-180')} aria-hidden="true" />
        {chosen && !noMusic ? `Lagu pilihan: ${trackTitle(chosen.name)}` : `Pilih lagu sendiri (${tracks.length} lagu)`}
      </button>

      {open && (
        <div id="music-list" className="mt-3 rounded-lg border border-line bg-surface">
          <div className="px-3 pt-3">
            <Segmented
              label="Suasana musik"
              size="sm"
              value={mood}
              onChange={setMood}
              options={moods.map(([m, n]) => ({ id: m, label: `${moodLabel(m)} ${n}` }))}
            />
          </div>
          <ul className="mt-2 divide-y divide-line">
            {visible.map((track) => {
              const playing = playingTrackPath === track.path;
              const checked = value === track.path;
              const title = trackTitle(track.name);
              return (
                <li key={track.path} className={cx('flex items-center gap-3 px-3.5 py-2', checked && 'bg-brand-soft/60')}>
                  <label className="flex items-center gap-3 flex-1 min-w-0 cursor-pointer">
                    <input
                      type="radio"
                      name="music_choice"
                      checked={checked && !noMusic}
                      onChange={() => {
                        onNoMusic?.(false);
                        onChange(track.path);
                      }}
                      className="w-4 h-4 accent-[rgb(var(--brand))] shrink-0"
                    />
                    <span className={cx('text-sm truncate', checked ? 'font-semibold text-ink' : 'text-ink')} title={track.name}>
                      {title}
                    </span>
                  </label>
                  <button
                    type="button"
                    onClick={() => toggleMusicPreview(track)}
                    aria-label={playing ? `Hentikan cuplikan ${title}` : `Putar cuplikan 10 detik ${title}`}
                    aria-pressed={playing}
                    className={cx(
                      'shrink-0 grid place-items-center w-8 h-8 rounded-md border transition-colors',
                      playing ? 'border-brand bg-brand text-white' : 'border-line text-muted hover:text-ink'
                    )}
                  >
                    {playing ? <Square className="w-3.5 h-3.5" aria-hidden="true" /> : <Play className="w-3.5 h-3.5" aria-hidden="true" />}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
