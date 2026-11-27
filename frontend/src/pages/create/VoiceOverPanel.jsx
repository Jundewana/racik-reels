import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Mic, Square, Upload, Sparkles, Plus, Trash2, RotateCcw, Check } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { formatSec } from '../../lib/format.js';
import { Button, IconButton, Segmented, cx } from '../../components/ui.jsx';

/**
 * Panel Voice over di halaman hasil.
 * - Suara sendiri (utama): rekam sambil video diputar (teleprompter), atau unggah file dari perekam HP.
 * - Suara AI (Gemini): pilih karakter suara, AI membacakan naskah.
 * Naskah ditulis AI saat pembuatan video; di sini ditinjau/diedit manusia.
 * Endpoint: POST /api/jobs/{id}/voiceover, POST /api/jobs/{id}/voiceover/recording.
 */
const WORDS_PER_SEC = 2.5;
const countWords = (t) => ((t || '').trim() ? t.trim().split(/\s+/).length : 0);

const MODES = [
  { id: 'rekam', label: 'Suara sendiri' },
  { id: 'gemini', label: 'Suara AI' },
  { id: 'none', label: 'Tanpa' }
];

export default function VoiceOverPanel() {
  const { currentJob: job, api, options, showToast, uploadWithProgress, useMock, startPollingProgress } = useStudio();
  const onRerender = (id) => startPollingProgress(id, 'create');

  const vo = job?.edl?.voiceover;
  const total = Number(job?.stats?.total_duration) || 20;
  const [mode, setMode] = useState(vo?.mode && vo.mode !== 'none' ? vo.mode : 'rekam');
  const [voice, setVoice] = useState(vo?.voice || 'Puck');
  const [lines, setLines] = useState(vo?.lines?.length ? vo.lines : [{ at_sec: 0, text: '' }]);
  const [offset, setOffset] = useState(vo?.offset_sec || 0);
  const [busy, setBusy] = useState(false);

  // perekam
  const videoRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const t0Ref = useRef(0);
  const offsetMsRef = useRef(0);
  const [recState, setRecState] = useState('idle'); // idle | recording | done
  const [showRecorder, setShowRecorder] = useState(false);
  const [recBlob, setRecBlob] = useState(null);
  const [recUrl, setRecUrl] = useState('');
  const [now, setNow] = useState(0);
  const canRecordHere = typeof window !== 'undefined' && window.isSecureContext && !!navigator.mediaDevices?.getUserMedia;

  useEffect(() => {
    setMode(vo?.mode && vo.mode !== 'none' ? vo.mode : 'rekam');
    setVoice(vo?.voice || 'Puck');
    setLines(vo?.lines?.length ? vo.lines : [{ at_sec: 0, text: '' }]);
    setOffset(vo?.offset_sec || 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.job_id, job?.reel_url]);

  useEffect(() => () => recUrl && URL.revokeObjectURL(recUrl), [recUrl]);

  const sorted = useMemo(() => [...lines].sort((a, b) => a.at_sec - b.at_sec), [lines]);
  const slotOf = (ln) => {
    const idx = sorted.indexOf(ln);
    const next = sorted[idx + 1];
    return (next ? next.at_sec : total) - ln.at_sec;
  };
  const currentLine = useMemo(() => {
    let cur = null;
    sorted.forEach((ln) => {
      if (now >= ln.at_sec) cur = ln;
    });
    return cur;
  }, [sorted, now]);

  if (!vo) return null; // video impor: voice over tidak tersedia

  const setLine = (i, patch) => setLines((prev) => prev.map((ln, k) => (k === i ? { ...ln, ...patch } : ln)));
  const addLine = () => {
    const last = sorted[sorted.length - 1];
    setLines((prev) => [...prev, { at_sec: Math.min(total - 1, last ? +(last.at_sec + 3).toFixed(1) : 0), text: '' }]);
  };
  const cleanLines = () =>
    sorted.filter((ln) => ln.text.trim()).map((ln) => ({ at_sec: Number(ln.at_sec) || 0, text: ln.text.trim() }));

  const save = async (targetMode) => {
    if (busy) return;
    setBusy(true);
    try {
      const res = await api('POST', `/api/jobs/${encodeURIComponent(job.job_id)}/voiceover`, {
        mode: targetMode,
        voice,
        lines: cleanLines(),
        offset_sec: Number(offset) || 0
      });
      onRerender(res.job_id || job.job_id);
    } finally {
      setBusy(false);
    }
  };

  const uploadRecording = async (blobOrFile, offsetMs) => {
    setBusy(true);
    try {
      const fd = new FormData();
      const name = blobOrFile.name || 'rekaman.webm';
      fd.append('file', blobOrFile, name);
      fd.append('offset_ms', String(Math.round(offsetMs || 0)));
      fd.append('lines_json', JSON.stringify(cleanLines()));
      const url = `/api/jobs/${encodeURIComponent(job.job_id)}/voiceover/recording`;
      const res = useMock ? await api('POST', url, fd) : await uploadWithProgress(url, fd, () => {});
      showToast('Rekaman terkirim, video dirender ulang');
      onRerender(res.job_id || job.job_id);
    } finally {
      setBusy(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || 'audio/webm' });
        setRecBlob(blob);
        setRecUrl(URL.createObjectURL(blob));
        setRecState('done');
      };
      rec.onstart = async () => {
        t0Ref.current = performance.now();
        const v = videoRef.current;
        v.currentTime = 0;
        v.muted = true;
        await v.play();
      };
      recorderRef.current = rec;
      setRecState('recording');
      rec.start(250);
    } catch (err) {
      showToast('Mikrofon tidak bisa dipakai. Izinkan akses mikrofon di browser, lalu coba lagi.', 'error');
    }
  };

  const stopRecording = () => {
    const v = videoRef.current;
    if (v) v.pause();
    if (recorderRef.current && recorderRef.current.state !== 'inactive') recorderRef.current.stop();
  };

  const status =
    vo.mode === 'gemini'
      ? `Terpasang: suara AI (${vo.voice})`
      : vo.mode === 'rekam'
        ? vo.has_recording
          ? 'Terpasang: rekaman suara Anda'
          : 'Belum ada rekaman suara'
        : 'Video ini belum memakai voice over';

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className={cx('text-sm font-semibold', vo.mode === 'rekam' && !vo.has_recording ? 'text-stop-text' : 'text-ink')}>
          {status}
        </p>
        <Segmented label="Sumber suara" value={mode} onChange={setMode} options={MODES} size="sm" />
      </div>

      {mode !== 'none' && (
        <fieldset>
          <div className="flex items-baseline justify-between gap-3 mb-3">
            <legend className="font-display font-bold text-xl text-ink">Naskah</legend>
            <span className="text-[13px] text-muted num">{`video ${formatSec(total)} dtk`}</span>
          </div>
          <ol className="space-y-3">
            {lines.map((ln, i) => {
              const words = countWords(ln.text);
              const need = words / WORDS_PER_SEC + 0.3;
              const slot = slotOf(ln);
              const over = words > 0 && need > slot * 1.25;
              return (
                <li key={i} className="flex items-start gap-2">
                  <input
                    type="number"
                    inputMode="decimal"
                    step="0.1"
                    min="0"
                    max={total}
                    value={ln.at_sec}
                    onChange={(e) => setLine(i, { at_sec: Number(e.target.value) })}
                    aria-label={`Baris ${i + 1} mulai detik ke`}
                    className="field w-20 shrink-0 num px-2"
                  />
                  <div className="flex-1 min-w-0">
                    <input
                      type="text"
                      value={ln.text}
                      onChange={(e) => setLine(i, { text: e.target.value })}
                      aria-label={`Teks baris ${i + 1}`}
                      className={cx('field', over && 'field-invalid')}
                    />
                    <p className={cx('mt-1 text-[12px] num', over ? 'text-stop-text font-semibold' : 'text-muted')}>
                      {`${words} kata, butuh ±${formatSec(need)} dtk dari ${formatSec(slot)} dtk`}
                      {over ? '. Terlalu panjang, persingkat.' : ''}
                    </p>
                  </div>
                  <IconButton
                    label={`Hapus baris ${i + 1}`}
                    icon={Trash2}
                    onClick={() => setLines((prev) => prev.filter((_, k) => k !== i))}
                    className="hover:text-stop-text"
                  />
                </li>
              );
            })}
          </ol>
          <Button variant="ghost" size="sm" icon={Plus} onClick={addLine} className="mt-2 -ml-2">
            Tambah baris
          </Button>
        </fieldset>
      )}

      {mode === 'gemini' && (
        <div className="space-y-4 border-t border-line pt-5">
          <div>
            <p className="text-sm font-semibold text-ink mb-2">Karakter suara</p>
            <Segmented
              label="Karakter suara"
              value={voice}
              onChange={setVoice}
              options={(options.voices || [{ id: 'Puck', description: 'ceria' }]).map((v) => ({
                id: v.id,
                label: `${v.id}, ${v.description}`
              }))}
            />
          </div>
          <p className="text-[13px] text-muted">
            Saat mengunggah ke Instagram, aktifkan label <strong className="text-ink">AI info</strong> karena suaranya dibuat AI.
          </p>
          <Button variant="brand" icon={Sparkles} loading={busy} onClick={() => save('gemini')}>
            Simpan naskah dan buat suara AI
          </Button>
        </div>
      )}

      {mode === 'rekam' && (
        <div className="space-y-4 border-t border-line pt-5">
          <div className="grid sm:grid-cols-2 gap-2">
            <Button
              variant={showRecorder ? 'secondary' : 'record'}
              size="lg"
              icon={Mic}
              onClick={() => setShowRecorder((v) => !v)}
              disabled={!canRecordHere}
              title={canRecordHere ? undefined : 'Rekam langsung hanya bisa dari laptop (127.0.0.1)'}
            >
              {showRecorder ? 'Tutup perekam' : 'Rekam di sini'}
            </Button>
            <Button as="label" variant="secondary" size="lg" icon={Upload} className="cursor-pointer">
              {busy ? 'Mengunggah…' : 'Unggah file rekaman'}
              <input
                type="file"
                accept="audio/*,.m4a,.mp3,.wav,.webm,.ogg,.aac"
                className="sr-only"
                onChange={(e) => {
                  const f = (e.target.files || [])[0];
                  e.target.value = '';
                  if (f) uploadRecording(f, 0);
                }}
              />
            </Button>
          </div>
          {!canRecordHere && (
            <p className="text-[13px] text-muted">
              Di HP: rekam dengan aplikasi perekam suara sambil membaca naskah, lalu unggah filenya (mp3, m4a, atau wav).
            </p>
          )}

          {canRecordHere && showRecorder && (
            <div className="rounded-lg border border-line p-4 space-y-4">
              <p className="text-sm text-muted">
                Tekan <strong className="text-ink">Mulai rekam</strong>: video diputar tanpa suara dan naskah tampil seperti
                teleprompter. Bacakan tiap baris saat muncul. Rekaman berhenti sendiri di akhir video.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 items-center">
                <video
                  ref={videoRef}
                  src={job.reel_url}
                  muted
                  playsInline
                  onTimeUpdate={(e) => setNow(e.currentTarget.currentTime)}
                  onPlaying={() => {
                    if (recState === 'recording' && !offsetMsRef.current) offsetMsRef.current = performance.now() - t0Ref.current;
                  }}
                  onEnded={stopRecording}
                  className="w-24 aspect-[9/16] rounded-lg bg-black object-cover shrink-0"
                />
                <div
                  className="flex-1 w-full min-h-[7rem] rounded-lg bg-[#160F2C] text-white p-5 flex items-center justify-center text-center"
                  aria-live="polite"
                >
                  <span className="font-display font-bold text-3xl leading-tight">
                    {recState === 'recording' ? currentLine?.text || '…' : 'Naskah muncul di sini saat merekam'}
                  </span>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {recState !== 'recording' ? (
                  <Button
                    variant="record"
                    icon={Mic}
                    disabled={busy}
                    onClick={() => {
                      offsetMsRef.current = 0;
                      startRecording();
                    }}
                  >
                    {recState === 'done' ? 'Rekam ulang' : 'Mulai rekam'}
                  </Button>
                ) : (
                  <Button variant="brand" icon={Square} onClick={stopRecording}>
                    Berhenti
                  </Button>
                )}
                {recState === 'done' && recBlob && (
                  <>
                    <audio src={recUrl} controls className="h-10 max-w-full" />
                    <Button variant="primary" icon={Check} loading={busy} onClick={() => uploadRecording(recBlob, offsetMsRef.current)}>
                      Pakai rekaman ini
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}

          {vo.has_recording && (
            <div className="border-t border-line pt-4">
              <label htmlFor="vo-offset" className="text-sm font-semibold text-ink">
                Geser waktu rekaman
              </label>
              <p className="text-[13px] text-muted">Gunakan bila suara terdengar lebih cepat atau lambat dari gambar.</p>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <input
                  id="vo-offset"
                  type="range"
                  min="-1"
                  max="1"
                  step="0.05"
                  value={offset}
                  onChange={(e) => setOffset(Number(e.target.value))}
                  className="flex-1 min-w-[10rem] accent-[rgb(var(--brand))]"
                />
                <span className="w-20 text-sm text-ink num">{`${offset > 0 ? '+' : ''}${Number(offset).toFixed(2)} dtk`}</span>
                <Button variant="secondary" size="sm" icon={RotateCcw} loading={busy} onClick={() => save('rekam')}>
                  Terapkan dan render ulang
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {mode === 'none' && vo.mode !== 'none' && (
        <Button variant="danger" loading={busy} onClick={() => save('none')}>
          Hapus voice over dan render ulang
        </Button>
      )}
    </div>
  );
}
