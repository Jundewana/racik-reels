import React, { useEffect, useRef, useState } from 'react';
import { Square, Plus, RotateCcw, Wand2, Check, AlertTriangle, Clock, ArrowRight } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { formatElapsed } from '../../lib/format.js';
import { Button, Spinner, cx } from '../../components/ui.jsx';
import RuangKerja from '../../components/RuangKerja.jsx';

const fmtTime = (epochSec) => {
  if (!epochSec) return '';
  const d = new Date(epochSec * 1000);
  return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

/**
 * Langkah Proses untuk mesin Remotion (Claude Code / Antigravity): footage disiapkan, agen menyusun video
 * (Ruang Kerja tampil langsung), lalu hasilnya muncul di sini. Banyak cuplikan = daftar, dikerjakan satu per satu.
 * Endpoint: /api/animasi/{nama}.
 */
const stepLabel = (langkah, agentName) =>
  ({
    siapkan: 'Menyiapkan footage',
    claude: `${agentName} menyusun video`,
    render: 'Merender video',
    frame: 'Merender frame'
  })[langkah] || langkah;

export default function RemotionProcess({ names }) {
  const { api, form, resetWizardToNew, openJobDetail } = useStudio();
  const wasRunning = useRef({});
  const [revisi, setRevisi] = useState('');
  const [sel, setSel] = useState(names[0]);
  const [all, setAll] = useState({});
  const [nowSec, setNowSec] = useState(() => Date.now() / 1000);

  useEffect(() => {
    setSel(names[0]);
  }, [names]);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      const out = {};
      await Promise.all(
        names.map(async (n) => {
          try {
            out[n] = await api('GET', `/api/animasi/${n}`);
          } catch {
            /* belum ada: dicoba lagi */
          }
        })
      );
      if (!stop) setAll((cur) => ({ ...cur, ...out }));
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      stop = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [names.join('|')]);

  const v = all[sel];
  const agen = v?.agen || form?.agen || 'claude';
  const agentName = agen === 'antigravity' ? 'Antigravity' : 'Claude Code';
  const agentShort = agen === 'antigravity' ? 'Antigravity' : 'Claude';
  const running = v?.state === 'berjalan';
  const claudeRunning = running && v?.langkah === 'claude';
  const failed = v && ['gagal', 'terhenti', 'dihentikan'].includes(v.state) && !v.hasil;
  const percent = v?.hasil ? 100 : Math.min(100, Math.max(0, Number(v?.persen || 0)));
  const elapsed = v?.mulai ? Math.max(0, (v?.selesai_pada || (running ? nowSec : v.mulai)) - v.mulai) : 0;

  useEffect(() => {
    if (!running) return undefined;
    const id = setInterval(() => setNowSec(Date.now() / 1000), 1000);
    return () => clearInterval(id);
  }, [running]);

  // selesai (berjalan → jadi) dan satu video: otomatis pindah ke langkah Hasil, seperti Reel biasa
  useEffect(() => {
    if (!v) return;
    const was = wasRunning.current[sel];
    wasRunning.current[sel] = running;
    if (was && !running && v.hasil?.job_id && names.length === 1) openJobDetail(v.hasil.job_id).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, v?.hasil?.job_id]);
  const retry = (overrideAgen = agen) => api('POST', `/api/animasi/${sel}/claude`, { instruksi: '', agen: overrideAgen });
  const revise = () => api('POST', `/api/animasi/${sel}/claude`, { instruksi: revisi, agen }).then(() => setRevisi(''));
  const stop = () => api('POST', `/api/animasi/${sel}/stop`);

  return (
    <div className="max-w-3xl">
      {names.length > 1 && (
        <ol className="mb-6 divide-y divide-line border-y border-line">
          {names.map((n) => {
            const x = all[n];
            const xAgent = (x?.agen || agen) === 'antigravity' ? 'Antigravity' : 'Claude Code';
            const st = x?.hasil ? 'Selesai' : x?.state === 'berjalan' ? stepLabel(x.langkah, xAgent) : x?.state === 'gagal' ? 'Gagal' : 'Menunggu giliran';
            const Icon = x?.hasil ? Check : x?.state === 'gagal' ? AlertTriangle : Clock;
            return (
              <li key={n}>
                <button
                  type="button"
                  onClick={() => setSel(n)}
                  aria-current={sel === n ? 'true' : undefined}
                  className={cx('flex w-full items-center gap-3 px-1 py-2.5 text-left', sel === n && 'bg-brand-soft/40')}
                >
                  <Icon className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate text-sm text-ink" translate="no">
                    {n}
                  </span>
                  <span className="shrink-0 text-[12px] text-muted">{st}</span>
                </button>
              </li>
            );
          })}
        </ol>
      )}

      <div className="border-t border-line pt-6 mb-6">
        <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-2">
          <p
            className={cx('font-display font-extrabold text-[4.5rem] sm:text-[5.5rem] leading-[0.8] num', failed ? 'text-stop-text' : 'text-ink')}
            aria-hidden="true"
          >
            {Math.round(percent)}
            <span className="text-[0.45em] text-muted">%</span>
          </p>
          <div className="text-right text-sm text-muted num pb-1">
            <p>
              Berjalan <span className="text-ink font-semibold">{formatElapsed(elapsed)}</span>
            </p>
            {v?.mulai && (
              <p className="text-[12px]" translate="no">
                Mulai {fmtTime(v.mulai)}
                {v?.selesai_pada ? ` · Selesai ${fmtTime(v.selesai_pada)}` : ''}
              </p>
            )}
          </div>
        </div>
        <div
          className="mt-4 h-2 rounded-full bg-sunken overflow-hidden"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(percent)}
          aria-label="Progres pembuatan video"
        >
          <div className={cx('h-full transition-[width] duration-500 ease-out', failed ? 'bg-stop' : 'bg-brand')} style={{ width: `${percent}%` }} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-display text-2xl font-extrabold text-ink" translate="no">
          {sel}
        </h2>
        {v?.state && (
          <span
            role="status"
            className={cx(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[13px] font-semibold',
              running ? 'bg-brand-soft text-brand' : failed ? 'bg-stop/10 text-stop-text' : 'bg-sunken text-muted'
            )}
          >
            {running && <Spinner className="h-3.5 w-3.5" />}
            {running ? stepLabel(v.langkah, agentName) : v.hasil ? 'Selesai' : v.state}
          </span>
        )}
      </div>
      {(running || failed) && v?.detail && (
        <p className={cx('mt-2 text-[13px] line-clamp-2', failed ? 'text-stop-text' : 'text-muted')} translate="no">
          {v.detail}
        </p>
      )}
      <p className="mt-2 text-[12px] text-muted">Biasanya 5 sampai 15 menit. Halaman boleh ditutup; prosesnya tetap berjalan di laptop.</p>

      <div className="mt-6">
        <p className="mb-2 font-display text-lg font-bold text-ink">Ruang Kerja</p>
        <RuangKerja nama={sel} agen={agen} running={claudeRunning} lembarUrl={v?.lembar_url} punyaKode={Boolean(v?.punya_kode)} />
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {claudeRunning && (
          <Button variant="danger" icon={Square} onClick={() => stop().catch(() => {})}>
            Hentikan
          </Button>
        )}
        {failed && (
          <>
            <Button variant="primary" icon={RotateCcw} onClick={() => retry(agen).catch(() => {})}>
              {`Coba lagi dengan ${agentShort}`}
            </Button>
            <Button variant="secondary" icon={RotateCcw} onClick={() => retry(agen === 'antigravity' ? 'claude' : 'antigravity').catch(() => {})}>
              {agen === 'antigravity' ? 'Coba dengan Claude' : 'Coba dengan Antigravity'}
            </Button>
          </>
        )}
      </div>

      {v?.hasil && (
        <section className="mt-8 border-t border-line pt-6">
          <p className="text-sm text-ink">
            Video sudah jadi. Lihat, unduh, dan salin caption di langkah Hasil.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="primary" icon={ArrowRight} onClick={() => openJobDetail(v.hasil.job_id).catch(() => {})}>
              Lihat hasil
            </Button>
            <Button variant="ghost" icon={Plus} onClick={resetWizardToNew}>
              Buat video lain
            </Button>
          </div>
          <div className="mt-6">
            <label htmlFor="rm-revisi" className="block text-sm font-semibold text-ink">
              {`Mau diubah? Tulis arahan untuk ${agentShort}`}
            </label>
            <textarea
              id="rm-revisi"
              name="revisi"
              autoComplete="off"
              rows={3}
              className="field mt-1"
              value={revisi}
              onChange={(e) => setRevisi(e.target.value)}
              placeholder="Hook lebih besar, potongan lebih cepat, hapus adegan ke-3…"
            />
            <div className="mt-3">
              <Button variant="secondary" icon={Wand2} onClick={() => revise().catch(() => {})} disabled={!revisi.trim() || running}>
                {`Revisi dengan ${agentShort}`}
              </Button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
