import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Pause, Check, RotateCcw } from 'lucide-react';
import { Button, cx } from '../../components/ui.jsx';
import { formatSec } from '../../lib/format.js';
import PhraseEditor, { phraseAt } from '../../components/PhraseEditor.jsx';

/**
 * Periksa transkrip narasi sebelum video dibuat.
 * Tiap frasa bisa diputar dan dibetulkan; waktu audio tetap, jadi subtitle karaoke tetap pas dengan suara.
 * Frasa yang sudah dikoreksi AI ditandai, dengan opsi kembali ke teks asli.
 */
export default function TranscriptReview({ draft, saving, onSave }) {
  const [texts, setTexts] = useState(() => draft.phrases.map((p) => p.text));
  const [playing, setPlaying] = useState(null);
  const audioRef = useRef(null);
  const stopAt = useRef(null);

  useEffect(() => {
    setTexts(draft.phrases.map((p) => p.text));
  }, [draft]);

  const dirty = texts.some((t, i) => t !== draft.phrases[i].text);
  const fixedCount = draft.phrases.filter((p) => p.ai_fixed).length;

  const [audioTime, setAudioTime] = useState(null);
  const activeIndex = phraseAt(draft.phrases, audioTime);
  const editText = useCallback((i, value) => setTexts((prev) => prev.map((t, k) => (k === i ? value : t))), []);

  const play = useCallback((p) => {
    const a = audioRef.current;
    if (!a) return;
    if (playing === p.index) {
      a.pause();
      setPlaying(null);
      return;
    }
    stopAt.current = p.end;
    a.currentTime = p.start;
    a.play().catch(() => {});
    setPlaying(p.index);
  }, [playing]);

  const onTime = () => {
    const a = audioRef.current;
    if (a) setAudioTime(a.currentTime);
    if (a && stopAt.current != null && a.currentTime >= stopAt.current) {
      a.pause();
      stopAt.current = null;
      setPlaying(null);
    }
  };

  return (
    <div className="mt-5 border-t border-line pt-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-ink">Periksa transkrip</p>
        <p className="text-[13px] text-muted num">
          {`${draft.phrases.length} frasa, ${formatSec(draft.duration)} dtk setelah jeda dibuang`}
          {fixedCount > 0 ? `, ${fixedCount} dikoreksi AI` : ''}
        </p>
      </div>
      <p className="mt-1 text-[13px] text-muted">
        Teks ini jadi subtitle karaoke. Betulkan kata yang salah dengar; waktu tiap frasa tetap mengikuti suara Anda.
      </p>

      {draft.audio_url && (
        <audio ref={audioRef} src={draft.audio_url} preload="auto" onTimeUpdate={onTime} onEnded={() => setPlaying(null)} />
      )}

      <div className="mt-4">
        <PhraseEditor
          phrases={draft.phrases}
          values={texts}
          onChange={editText}
          onPlay={play}
          activeIndex={playing === null ? null : activeIndex}
          label="Transkrip"
        />
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-end gap-3">
        {draft.reviewed && !dirty && (
          <span className="flex items-center gap-1.5 text-[13px] font-semibold text-go-text">
            <Check className="w-4 h-4" aria-hidden="true" />
            Transkrip sudah diperiksa
          </span>
        )}
        {(dirty || !draft.reviewed) && (
          <Button variant="brand" size="sm" icon={Check} loading={saving} onClick={() => onSave(texts)}>
            {saving ? 'Menyimpan…' : 'Transkrip sudah benar, pakai ini'}
          </Button>
        )}
      </div>
    </div>
  );
}
