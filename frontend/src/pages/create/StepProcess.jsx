import React, { useEffect, useRef, useState } from 'react';
import { Check, AlertTriangle, Clock, RotateCcw, ChevronDown } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { formatElapsed } from '../../lib/format.js';
import { Button, cx } from '../../components/ui.jsx';
import AiDecisions from './AiDecisions.jsx';
import RemotionProcess from './RemotionProcess.jsx';

export default function StepProcess() {
  const { progress, processSteps, lastSubmitKind, navigateTo, submitCreateJob, setWizardStep, batch, openJobDetail, remotionRuns } =
    useStudio();
  const [showLog, setShowLog] = useState(false);
  const logRef = useRef(null);

  const failed = progress.state === 'gagal';
  const finished = progress.state === 'selesai';
  const percent = Math.min(100, Math.max(0, progress.percent || 0));
  const currentIdx = progress.step_index || 1;
  const currentLabel = processSteps[currentIdx - 1]?.label || progress.step_label || 'Memproses';
  const waitingRateLimit = (progress.log || []).some((line) => line.includes('[menunggu]'));

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [progress.log, showLog]);

  useEffect(() => {
    if (failed) setShowLog(true);
  }, [failed]);

  // Server hanya memperbarui elapsed_sec saat pindah langkah → jam berdetak sendiri di browser,
  // disetel ulang setiap kali nilai dari server berubah.
  const running = !failed && !finished;
  const [clock, setClock] = useState({ base: progress.elapsed_sec || 0, at: Date.now(), now: Date.now() });
  useEffect(() => {
    setClock({ base: progress.elapsed_sec || 0, at: Date.now(), now: Date.now() });
  }, [progress.elapsed_sec]);
  useEffect(() => {
    if (!running) return undefined;
    const id = setInterval(() => setClock((c) => ({ ...c, now: Date.now() })), 1000);
    return () => clearInterval(id);
  }, [running]);
  const elapsed = running ? clock.base + (clock.now - clock.at) / 1000 : progress.elapsed_sec || 0;

  if (lastSubmitKind === 'remotion' && remotionRuns.length) return <RemotionProcess names={remotionRuns} />;

  return (
    <div className="max-w-3xl">
      {batch && (
        <section aria-labelledby="batch-title" className="mb-8">
          <h2 id="batch-title" className="text-sm font-semibold text-ink">
            {`Membuat ${batch.ids.length} Reel, satu per satu`}
          </h2>
          <ol className="mt-3 divide-y divide-line border-y border-line">
            {batch.titles.map((t, i) => {
              const st = (batch.states || {})[batch.ids[i]];
              const current = i === batch.index && !st;
              const status = st === 'selesai' ? 'Selesai' : st === 'gagal' ? 'Gagal' : current
                ? `Sedang dibuat, ${Math.round(percent)}%` : i > batch.index ? 'Menunggu giliran' : '';
              const Icon = st === 'selesai' ? Check : st === 'gagal' ? AlertTriangle : Clock;
              return (
                <li key={batch.ids[i]} aria-current={current ? 'step' : undefined}
                  className={cx('flex items-center gap-3 py-2.5', current && 'bg-brand-soft/40')}>
                  <span className={cx('grid place-items-center w-6 h-6 rounded-full text-[12px] font-semibold num shrink-0',
                    st === 'selesai' ? 'bg-go text-white' : st === 'gagal' ? 'bg-stop text-white'
                      : current ? 'bg-brand text-white' : 'bg-sunken text-muted')}>
                    {st ? <Icon className="w-3.5 h-3.5" aria-hidden="true" /> : i + 1}
                  </span>
                  <span className={cx('min-w-0 flex-1 text-sm truncate', current || st ? 'text-ink' : 'text-muted')}>{t}</span>
                  <span className={cx('shrink-0 text-[13px] num',
                    st === 'selesai' ? 'text-go-text' : st === 'gagal' ? 'text-stop-text' : 'text-muted')}>{status}</span>
                  {st === 'selesai' && (
                    <button type="button" onClick={() => openJobDetail(batch.ids[i]).catch(() => {})}
                      className="shrink-0 text-[13px] font-semibold text-ink underline underline-offset-4 hover:text-brand">
                      Lihat
                    </button>
                  )}
                </li>
              );
            })}
          </ol>
        </section>
      )}
      <div className="border-t border-line pt-8">
        <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-2">
          <p
            className={cx('font-display font-extrabold text-[5.5rem] sm:text-[7rem] leading-[0.8] num', failed ? 'text-stop-text' : 'text-ink')}
            aria-hidden="true"
          >
            {Math.round(percent)}
            <span className="text-[0.45em] text-muted">%</span>
          </p>
          <p className="text-sm text-muted num pb-1">
            Berjalan <span className="text-ink font-semibold">{formatElapsed(elapsed)}</span>
          </p>
        </div>

        <div
          className="mt-6 h-2 rounded-full bg-sunken overflow-hidden"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(percent)}
          aria-label="Progres pembuatan video"
        >
          <div className={cx('h-full transition-[width] duration-500 ease-out', failed ? 'bg-stop' : 'bg-brand')} style={{ width: `${percent}%` }} />
        </div>

        <div className="mt-5" aria-live="polite">
          <h2 className="font-display font-bold text-3xl leading-tight text-ink">
            {failed ? 'Proses berhenti' : finished ? 'Selesai' : `${currentLabel}…`}
          </h2>
          {!failed && progress.detail && <p className="mt-1 text-muted">{progress.detail}</p>}
        </div>

        {waitingRateLimit && !failed && (
          <p className="mt-4 flex items-start gap-2 text-sm text-ink">
            <Clock className="w-4 h-4 mt-0.5 shrink-0 text-muted" aria-hidden="true" />
            Layanan AI sedang penuh. Sistem menunggu sebentar lalu mencoba lagi sendiri.
          </p>
        )}

        {failed && (
          <div className="mt-6 border-l-[3px] border-stop pl-4" role="alert">
            <p className="font-semibold text-stop-text flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" aria-hidden="true" /> Video tidak bisa dibuat
            </p>
            <p className="mt-1 text-sm text-ink break-words">{progress.error || 'Terjadi kendala saat memproses video.'}</p>
            <p className="mt-1 text-[13px] text-muted">Periksa log di bawah untuk rinciannya, lalu coba lagi.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button
                variant="primary"
                icon={RotateCcw}
                onClick={() => (lastSubmitKind === 'import' ? navigateTo('import') : submitCreateJob())}
              >
                Coba lagi
              </Button>
              {lastSubmitKind !== 'import' && (
                <Button variant="secondary" onClick={() => setWizardStep(2)}>
                  Ubah pengaturan
                </Button>
              )}
            </div>
          </div>
        )}
      </div>

      <ol className="mt-10 border-t border-line">
        {processSteps.map((st, idx) => {
          const n = idx + 1;
          const done = n < currentIdx || finished;
          const active = n === currentIdx && progress.state === 'berjalan';
          const stoppedHere = n === currentIdx && failed;
          return (
            <li key={st.key} className="flex items-center gap-4 border-b border-line py-3" aria-current={active ? 'step' : undefined}>
              <span
                className={cx(
                  'w-7 h-7 shrink-0 rounded-full flex items-center justify-center text-[13px] font-bold num',
                  done && 'bg-brand text-on-brand',
                  active && 'border-2 border-brand text-brand',
                  stoppedHere && 'bg-stop text-on-stop',
                  !done && !active && !stoppedHere && 'border border-line text-muted'
                )}
              >
                {done ? <Check className="w-4 h-4" aria-hidden="true" /> : stoppedHere ? '!' : n}
              </span>
              <span
                className={cx(
                  'flex-1 text-sm',
                  active ? 'font-semibold text-ink' : done ? 'text-ink' : st.skipped ? 'text-muted/70 line-through decoration-muted/40' : 'text-muted'
                )}
              >
                {st.label}
              </span>
              {active && <span className="text-[13px] text-brand font-semibold">sedang berjalan</span>}
            </li>
          );
        })}
      </ol>

      <AiDecisions notes={progress.notes} running={running} />

      <div className="mt-6">
        <button
          type="button"
          onClick={() => setShowLog((s) => !s)}
          aria-expanded={showLog}
          aria-controls="process-log"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink"
        >
          <ChevronDown className={cx('w-4 h-4 transition-transform', showLog && 'rotate-180')} aria-hidden="true" />
          {showLog ? 'Sembunyikan log teknis' : 'Lihat log teknis'}
        </button>
        {showLog && (
          <div
            id="process-log"
            ref={logRef}
            className="mt-3 rounded-lg bg-[#160F2C] text-[#D9D3F2] font-mono text-[12.5px] leading-relaxed p-4 max-h-64 overflow-y-auto scroll-thin"
          >
            {(progress.log || []).length > 0 ? (
              progress.log.map((line, i) => (
                <div key={i} translate="no" className="whitespace-pre-wrap break-words">
                  {line}
                </div>
              ))
            ) : (
              <div className="text-[#8F86B3]">Menunggu log dari server…</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
