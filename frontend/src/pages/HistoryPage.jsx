import React, { useState } from 'react';
import { Clapperboard, Loader2, ArrowRight, FileVideo } from 'lucide-react';
import { useStudio } from '../state/studio.jsx';
import { formatSec, formatDateTime } from '../lib/format.js';
import { PageHeader, Segmented, Button, Empty, StatusMark } from '../components/ui.jsx';
import { ReelGlyph } from '../components/Shell.jsx';

function Cover({ job }) {
  const [broken, setBroken] = useState(false);
  if (job.cover_url && !broken) {
    return (
      <img
        src={job.cover_url}
        alt=""
        loading="lazy"
        width="270"
        height="480"
        onError={() => setBroken(true)}
        className="w-full h-full object-cover transition-transform duration-200 group-hover:scale-[1.03]"
      />
    );
  }
  // Tanpa cover: tampilkan teks hook seperti di video
  return (
    <div className="w-full h-full flex flex-col justify-between p-3 bg-[#1B1238]">
      <ReelGlyph className="h-5 w-auto self-start opacity-80" />
      <span className="font-display font-extrabold text-xl leading-tight text-white line-clamp-4">{job.hook_text}</span>
    </div>
  );
}

export default function HistoryPage() {
  const {
    options,
    jobs,
    filteredJobs,
    historyFilter,
    setHistoryFilter,
    openJobDetail,
    navigateTo,
    getPillarLabel,
    resetWizardToNew,
    activeJob,
    goToProcess
  } = useStudio();

  return (
    <div>
      <PageHeader
        title="Riwayat"
        description="Semua video yang pernah dibuat di laptop ini. Buka satu untuk menonton, menyalin caption, atau mengubah teks."
        actions={
          <Button variant="ghost" size="sm" icon={FileVideo} onClick={() => navigateTo('import')}>
            Impor video dari editor lain
          </Button>
        }
      />

      {activeJob && (
        <section
          aria-label="Video yang sedang dibuat"
          className="mb-8 rounded-lg border border-brand/40 bg-brand-soft/50 p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center gap-4"
        >
          <div className="flex-1 min-w-0">
            <p className="flex items-center gap-2 font-display font-bold text-xl text-ink">
              <Loader2 className="w-5 h-5 animate-spin text-brand" aria-hidden="true" />
              Sedang dibuat
              <span className="num">{`${activeJob.percent}%`}</span>
            </p>
            <p className="mt-0.5 text-sm text-muted truncate">
              {activeJob.label}. Muncul di daftar ini setelah selesai.
            </p>
            <div className="mt-3 h-1.5 rounded-full bg-sunken overflow-hidden" aria-hidden="true">
              <div className="h-full bg-brand transition-[width] duration-500" style={{ width: `${activeJob.percent}%` }} />
            </div>
          </div>
          <Button variant="brand" iconEnd={ArrowRight} onClick={goToProcess} className="shrink-0">
            Lihat proses
          </Button>
        </section>
      )}

      <div className="flex flex-wrap items-center gap-3 border-t border-line pt-5 mb-6">
        <Segmented
          label="Saring status"
          size="sm"
          value={historyFilter.status}
          onChange={(id) => setHistoryFilter((p) => ({ ...p, status: id }))}
          options={[
            { id: 'all', label: 'Semua' },
            { id: 'siap_unggah', label: 'Siap unggah' },
            { id: 'perlu_tinjau', label: 'Perlu tinjau' }
          ]}
        />
        <select
          aria-label="Saring pilar"
          value={historyFilter.pillar}
          onChange={(e) => setHistoryFilter((p) => ({ ...p, pillar: e.target.value }))}
          className="field w-auto h-9 py-0 text-sm"
        >
          <option value="all">Semua pilar</option>
          {options.pillars.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
        <span className="text-[13px] text-muted num ml-auto">{`${filteredJobs.length} dari ${jobs.length} video`}</span>
      </div>

      {filteredJobs.length === 0 ? (
        jobs.length === 0 ? (
          <Empty
            title="Belum ada video"
            action={
              <Button variant="primary" icon={Clapperboard} onClick={resetWizardToNew}>
                Buat video pertama
              </Button>
            }
          >
            Video yang selesai dibuat akan muncul di sini.
          </Empty>
        ) : (
          <Empty
            title="Tidak ada yang cocok"
            action={
              <Button variant="secondary" onClick={() => setHistoryFilter({ pillar: 'all', status: 'all' })}>
                Tampilkan semua
              </Button>
            }
          >
            Tidak ada video dengan saringan ini.
          </Empty>
        )
      ) : (
        <ul className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 gap-x-4 gap-y-8">
          {filteredJobs.map((job) => (
            <li key={job.job_id} className="min-w-0">
              <button
                type="button"
                onClick={() => openJobDetail(job.job_id).catch(() => {})}
                className="group block w-full text-left rounded-lg"
              >
                <div className="relative aspect-[9/16] rounded-lg overflow-hidden bg-sunken">
                  <Cover job={job} />
                  <span className="absolute top-2 right-2 rounded bg-[rgb(12_8_26/0.75)] px-1.5 py-0.5 text-[12px] font-semibold text-white num">
                    {`${formatSec(job.duration)} dtk`}
                  </span>
                </div>
                <p className="mt-2.5 font-display font-bold text-lg leading-tight text-ink line-clamp-2 group-hover:underline decoration-2 underline-offset-2">
                  {job.hook_text || 'Tanpa teks hook'}
                </p>
                <StatusMark status={job.status} className="mt-1" />
                <p className="text-[13px] text-muted truncate">
                  {getPillarLabel(job.pillar)}
                  {job.source === 'import' ? ', impor' : ''}
                </p>
                <p className="text-[13px] text-muted">{formatDateTime(job.created)}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
