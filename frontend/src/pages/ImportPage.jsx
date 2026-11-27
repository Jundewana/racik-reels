import React, { useEffect, useState } from 'react';
import { RefreshCw, UploadCloud, FileInput, ArrowLeft } from 'lucide-react';
import { useStudio } from '../state/studio.jsx';
import { formatDateTime } from '../lib/format.js';
import { PageHeader, Section, Button, Field, HookCounter, Segmented, Empty, cx } from '../components/ui.jsx';
import { engineLabel } from '../components/EngineChoice.jsx';

/**
 * Impor video jadi — untuk video yang sudah diedit di video-use (mode chat) atau editor lain.
 * Endpoint: GET /api/import/candidates, POST /api/footage/upload (pillar=impor), POST /api/import.
 */
export default function ImportPage() {
  const { api, options, showToast, uploadWithProgress, useMock, hookStats, setLastSubmitKind, navigateTo, startPollingProgress } =
    useStudio();
  const [candidates, setCandidates] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    video_path: '',
    pillar: 'profil',
    brief: '',
    hook_text: '',
    cta_text: '',
    add_logo: true,
    add_cta: true,
    engine: 'api'
  });
  const set = (patch) => setForm((prev) => ({ ...prev, ...patch }));

  const loadCandidates = async () => {
    const data = await api('GET', '/api/import/candidates');
    const list = data.candidates || [];
    setCandidates(list);
    setForm((prev) => (!prev.video_path && list.length ? { ...prev, video_path: list[0].path } : prev));
  };

  useEffect(() => {
    loadCandidates().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onUpload = async (event) => {
    const file = (event.target.files || [])[0];
    event.target.value = '';
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('pillar', 'impor');
      fd.append('files[]', file);
      const res = useMock ? await api('POST', '/api/footage/upload', fd) : await uploadWithProgress('/api/footage/upload', fd, () => {});
      await loadCandidates();
      if (res.files && res.files[0]) set({ video_path: `${res.folder}/${res.files[0]}` });
      showToast('Video jadi diunggah');
    } finally {
      setUploading(false);
    }
  };

  const submit = async () => {
    if (submitting || !form.video_path.trim()) return;
    setSubmitting(true);
    try {
      const res = await api('POST', '/api/import', {
        video_path: form.video_path.trim(),
        pillar: form.pillar,
        brief: form.brief.trim(),
        hook_text: form.hook_text.trim() || null,
        cta_text: form.add_cta ? form.cta_text.trim() || null : null,
        add_logo: form.add_logo,
        add_cta: form.add_cta,
        engine: form.engine
      });
      setLastSubmitKind('import');
      navigateTo('create');
      startPollingProgress(res.job_id, 'import');
    } finally {
      setSubmitting(false);
    }
  };

  const hs = hookStats(form.hook_text);

  return (
    <div>
      <PageHeader
        title="Impor video dari editor lain"
        description="Untuk video yang sudah diedit di CapCut, video-use, atau aplikasi lain. Racik menyesuaikan ukuran 1080×1920 dan volume suara, menempel watermark dan CTA WhatsApp, menulis caption, menjalankan checklist, lalu menyimpannya di Riwayat."
        actions={
          <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={() => navigateTo('history')}>
            Kembali ke Riwayat
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1fr)_22rem] xl:gap-12 items-start">
        <div className="min-w-0">
          <Section
            id="import-video"
            layout="stack"
            title="Pilih video"
            description="Hasil video-use (footage/…/edit/final.mp4) muncul di sini otomatis."
            aside={
              <Button variant="ghost" size="sm" icon={RefreshCw} onClick={() => loadCandidates().catch(() => {})}>
                Muat ulang
              </Button>
            }
          >
            {candidates.length === 0 ? (
              <Empty title="Belum ada video jadi">Unggah video jadi di bawah, atau tempel lokasi filenya.</Empty>
            ) : (
              <ul role="radiogroup" aria-label="Video jadi" className="space-y-2 max-h-80 overflow-y-auto pr-1 scroll-thin">
                {candidates.map((c) => {
                  const checked = form.video_path === c.path;
                  return (
                    <li key={c.path}>
                      <label
                        className={cx(
                          'flex items-start gap-3 rounded-lg border px-3.5 py-3 cursor-pointer transition-colors',
                          checked ? 'border-brand ring-1 ring-brand bg-brand-soft/60' : 'border-line bg-surface hover:border-ink/35'
                        )}
                      >
                        <input
                          type="radio"
                          name="import_video"
                          checked={checked}
                          onChange={() => set({ video_path: c.path })}
                          className="mt-1 w-4 h-4 accent-[rgb(var(--brand))] shrink-0"
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block text-sm font-semibold text-ink truncate">{c.name}</span>
                          <span className="block text-[13px] text-muted truncate">{c.path}</span>
                          <span className="mt-1 block text-[13px] text-muted num">
                            {`${c.size_mb} MB, ${formatDateTime(c.modified)}`}
                            {c.source === 'video-use' && ', dari video-use'}
                            {c.has_transcript && ', ada transkrip'}
                          </span>
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}

            <div className="mt-5">
              <Button as="label" variant="secondary" icon={UploadCloud} className="cursor-pointer w-full sm:w-auto">
                {uploading ? 'Mengunggah…' : 'Unggah video jadi'}
                <input type="file" accept=".mp4,.mov,video/mp4,video/quicktime" className="sr-only" onChange={onUpload} />
              </Button>
            </div>
            <Field label="Atau tempel lokasi file" htmlFor="import-path" className="mt-5">
              <input
                id="import-path"
                type="text"
                value={form.video_path}
                onChange={(e) => set({ video_path: e.target.value })}
                placeholder="Mis. D:\Video\testimoni\edit\final.mp4"
                spellCheck={false}
                autoComplete="off"
                className="field"
              />
            </Field>
          </Section>
        </div>

        <aside aria-labelledby="import-settings-title" className="xl:sticky xl:top-8 border-t-[3px] border-brand pt-5 space-y-5">
          <h2 id="import-settings-title" className="font-display font-bold text-2xl text-ink">
            Atur
          </h2>
          <div>
            <p className="text-sm font-semibold text-ink mb-1.5">Pilar konten</p>
            <Segmented
              label="Pilar konten"
              size="sm"
              value={form.pillar}
              onChange={(id) => set({ pillar: id })}
              options={(options.pillars || []).map((p) => ({ id: p.id, label: p.label }))}
            />
          </div>
          <Field label="Isi atau tujuan video" htmlFor="import-brief" optional hint="Bila kosong, AI menyimpulkan dari transkrip.">
            <textarea id="import-brief" rows={2} value={form.brief} onChange={(e) => set({ brief: e.target.value })} className="field resize-y" />
          </Field>
          <Field
            label="Teks hook di awal"
            htmlFor="import-hook"
            optional
            aside={<HookCounter stats={hs} id="import-hook-count" />}
            error={hs.over ? 'Terlalu panjang: teks akan tampil kecil.' : null}
          >
            <input
              id="import-hook"
              type="text"
              value={form.hook_text}
              onChange={(e) => set({ hook_text: e.target.value })}
              placeholder="Kosongkan agar memakai hook dari editor"
              aria-describedby="import-hook-count"
              className={cx('field', hs.over && 'field-invalid')}
            />
          </Field>
          <div className="space-y-2">
            <label className="flex items-start gap-2.5 text-sm text-ink cursor-pointer">
              <input
                type="checkbox"
                checked={form.add_cta}
                onChange={(e) => set({ add_cta: e.target.checked })}
                className="mt-0.5 w-4 h-4 accent-[rgb(var(--brand))]"
              />
              Tempel CTA WhatsApp di 3 detik terakhir
            </label>
            {form.add_cta && (
              <input
                type="text"
                value={form.cta_text}
                onChange={(e) => set({ cta_text: e.target.value })}
                placeholder={(options.default_cta || {})[form.pillar] || 'Hubungi kami via WhatsApp!'}
                aria-label="Teks CTA"
                className="field"
              />
            )}
          </div>
          <label className="flex items-start gap-2.5 text-sm text-ink cursor-pointer">
            <input
              type="checkbox"
              checked={form.add_logo}
              onChange={(e) => set({ add_logo: e.target.checked })}
              className="mt-0.5 w-4 h-4 accent-[rgb(var(--brand))]"
            />
            <span>
              Tempel logo
              <span className="block text-[13px] text-muted">Rental Motor untuk pilar rental, Brand untuk lainnya.</span>
            </span>
          </label>
          <div>
            <p className="text-sm font-semibold text-ink mb-1.5">Mesin AI untuk caption</p>
            <Segmented
              label="Mesin AI"
              size="sm"
              value={form.engine}
              onChange={(id) => set({ engine: id })}
              options={(options.engines || [])
                .filter((e) => e.available || e.id === form.engine)
                .map((e) => ({ id: e.id, label: engineLabel(options, e.id) }))}
            />
          </div>
          <Button
            variant="primary"
            size="lg"
            icon={FileInput}
            loading={submitting}
            disabled={!form.video_path.trim()}
            onClick={submit}
            className="w-full"
          >
            {submitting ? 'Mengirim…' : 'Impor dan siapkan unggah'}
          </Button>
          <p className="text-[13px] text-muted">Panduan video-use ada di docs/video-use.md.</p>
        </aside>
      </div>
    </div>
  );
}
