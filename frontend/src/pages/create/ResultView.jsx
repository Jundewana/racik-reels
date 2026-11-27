import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Download,
  Image as ImageIcon,
  FileText,
  Plus,
  Copy,
  RefreshCw,
  ChevronDown,
  Check,
  X as XIcon,
  AlertTriangle
} from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { formatSec, formatStyleName, copyText } from '../../lib/format.js';
import { Button, Field, HookCounter, cx } from '../../components/ui.jsx';
import SegmentStrip from './SegmentStrip.jsx';
import VoiceOverPanel from './VoiceOverPanel.jsx';
import PhraseEditor, { phraseAt } from '../../components/PhraseEditor.jsx';
import CriticPanel from './CriticPanel.jsx';
import VisualReviewPanel from './VisualReviewPanel.jsx';
import VariantPanel from './VariantPanel.jsx';

/**
 * Halaman hasil (langkah 4).
 * Atas: status + angka penting + strip struktur video.
 * Bawah: pratinjau 9:16 (menempel) di kiri, tab Siap posting / Edit teks / Voice over / Checklist di kanan.
 */
export default function ResultView() {
  const {
    currentJob: job,
    api,
    showToast,
    useMock,
    hookStats,
    getPillarLabel,
    startPollingProgress,
    resetWizardToNew,
    setShowReportModal
  } = useStudio();

  const vo = job.edl?.voiceover;
  const isImport = job.source === 'import';
  const waitingRecording = vo?.mode === 'rekam' && !vo?.has_recording;
  const ok = job.status === 'siap_unggah';

  const [tab, setTab] = useState('posting');
  const [showSafeZone, setShowSafeZone] = useState(false);
  const [openGroups, setOpenGroups] = useState({});
  const [form, setForm] = useState({ hook_text: '', cta_text: '', segment_texts: {}, subtitle_texts: [] });
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const videoRef = useRef(null);
  const [videoTime, setVideoTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);

  useEffect(() => {
    // tab awal: langsung ke Voice over bila sedang menunggu rekaman suara
    setTab(waitingRecording ? 'voice' : 'posting');
    const seg = {};
    (job.edl?.segments || []).forEach((s) => {
      if (s.overlay_text !== null && s.overlay_text !== undefined) seg[s.index] = s.overlay_text;
    });
    setForm({
      hook_text: job.edl?.hook_text || '',
      cta_text: job.edl?.cta_text || '',
      segment_texts: seg,
      subtitle_texts: (job.edl?.subtitles || []).map((p) => p.text)
    });
    setOpenGroups({});
    setVideoTime(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.job_id, job.reel_url]);

  const groups = useMemo(() => {
    const map = new Map();
    (job.checklist || []).forEach((it) => {
      if (!map.has(it.group)) map.set(it.group, []);
      map.get(it.group).push(it);
    });
    return [...map.entries()].map(([group, items]) => ({
      group,
      items,
      passed: items.filter((i) => i.passed).length,
      hasFail: items.some((i) => !i.passed && i.required),
      hasWarn: items.some((i) => !i.passed && !i.required)
    }));
  }, [job.checklist]);

  const problems = (job.checklist || []).filter((i) => !i.passed && i.required);
  const notes = (job.checklist || []).filter((i) => !i.passed && !i.required);
  const editableSegments = (job.edl?.segments || []).filter((s) => s.overlay_text !== null && s.overlay_text !== undefined);
  const hs = hookStats(form.hook_text);
  const subtitles = useMemo(() => job.edl?.subtitles || [], [job.edl]);
  const subtitleValues = useMemo(() => subtitles.map((p, i) => form.subtitle_texts[i] ?? p.text), [subtitles, form.subtitle_texts]);
  const subtitlesChanged = subtitleValues.some((v, i) => v !== subtitles[i].text);
  const editSubtitle = useCallback(
    (i, value) =>
      setForm((f) => ({ ...f, subtitle_texts: subtitles.map((p, k) => (k === i ? value : f.subtitle_texts[k] ?? p.text)) })),
    [subtitles]
  );
  const playPhrase = useCallback((p) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = p.start;
    v.play().catch(() => {});
  }, []);

  const copyCaption = async () => {
    await copyText(job.caption || '');
    setCopied(true);
    showToast('Caption disalin');
    setTimeout(() => setCopied(false), 2000);
  };

  const submitRerender = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const res = await api('POST', `/api/jobs/${encodeURIComponent(job.job_id)}/rerender`, {
        hook_text: form.hook_text.trim(),
        cta_text: form.cta_text.trim(),
        segment_texts: { ...form.segment_texts },
        subtitle_texts: subtitlesChanged ? form.subtitle_texts : null
      });
      startPollingProgress(res.job_id || job.job_id, isImport ? 'import' : 'create');
    } finally {
      setBusy(false);
    }
  };

  const mockDownload = (e, label) => {
    if (useMock) {
      e.preventDefault();
      showToast(`Mode simulasi: ${label} bisa diunduh saat terhubung ke laptop.`);
    }
  };

  const seek = (t) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = t;
    v.play().catch(() => {});
  };

  const stats = [
    { label: 'durasi', value: formatSec(job.stats?.total_duration), unit: 'dtk' },
    ...(isImport
      ? []
      : [
          { label: 'potongan', value: job.stats?.segments || 0, unit: '' },
          { label: 'pas ketukan', value: Math.round((job.stats?.beat_accuracy || 0) * 100), unit: '%' }
        ]),
    ...(job.critic?.final ? [{ label: 'skor AI Critic', value: job.critic.final.average.toFixed(1), unit: '/5' }] : []),
    { label: 'waktu proses', value: Math.round(job.stats?.process_sec || 0), unit: 'dtk' },
    { label: 'biaya AI', value: `$${(job.stats?.cost_usd || 0).toFixed(3)}`, unit: '' }
  ];

  const tabs = [
    { id: 'posting', label: 'Siap posting' },
    { id: 'edit', label: 'Edit teks' },
    ...(vo ? [{ id: 'voice', label: 'Voice over', dot: waitingRecording }] : []),
    ...(isImport ? [] : [{ id: 'critic', label: 'Penilaian AI', dot: (job.critic?.final && !job.critic.final.passed) || (job.visual?.issues || []).some((x) => x.severity === 'berat') }]),
    { id: 'checklist', label: 'Checklist', count: problems.length || notes.length, alert: problems.length > 0 }
  ];

  const headline = ok ? 'Siap unggah' : waitingRecording ? 'Tinggal rekam suara' : 'Perlu tinjau';
  const explanation = ok
    ? 'Video lolos semua pemeriksaan wajib. Salin caption, unduh video, lalu posting.'
    : waitingRecording
      ? 'Naskah voice over sudah jadi. Rekam atau unggah suara Anda di tab Voice over.'
      : `${problems.length} pemeriksaan wajib belum lolos. Lihat tab Checklist untuk cara memperbaikinya.`;

  return (
    <div>
      {/* ---------- Status & angka ---------- */}
      <div className="border-t border-line pt-6">
        <div className="flex flex-wrap items-start justify-between gap-x-10 gap-y-5">
          <div className="min-w-0 max-w-xl">
            <p
              className={cx(
                'font-display font-extrabold text-4xl sm:text-5xl leading-none',
                ok ? 'text-go-text' : 'text-stop-text'
              )}
            >
              {headline}
            </p>
            <p className="mt-2 text-ink">{explanation}</p>
            <p className="mt-1 text-[13px] text-muted break-all">
              {getPillarLabel(job.pillar)}
              {job.style ? `, gaya ${formatStyleName(job.style)}` : ''}
              {isImport ? ', video impor' : ''}. ID {job.job_id}
            </p>
            {job.models && Object.keys(job.models).length > 0 && (
              <p className="text-[13px] text-muted break-words">
                {job.engine === 'local' ? 'AI lokal' : 'AI online'}:{' '}
                {Object.values(job.models)
                  .map((m) => String(m).split('/').slice(1).join('/') || m)
                  .filter((m, i, arr) => arr.indexOf(m) === i)
                  .join(', ')}
              </p>
            )}
          </div>
          <dl className="flex flex-wrap gap-x-7 gap-y-3">
            {stats.map((s) => (
              <div key={s.label} className="flex flex-col-reverse">
                <dt className="mt-1 text-[13px] text-muted">{s.label}</dt>
                <dd className="font-display font-bold text-3xl leading-none text-ink num">
                  {s.value}
                  {s.unit && <span className="ml-0.5 text-base text-muted">{s.unit}</span>}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        {!isImport && (job.edl?.segments || []).length > 0 && (
          <div className="mt-8">
            <SegmentStrip
              segments={job.edl.segments}
              hookText={job.edl.hook_text}
              ctaText={job.edl.cta_text}
              videoDuration={videoDuration}
              currentTime={videoTime}
              onSeek={seek}
            />
          </div>
        )}
      </div>

      {/* ---------- Pratinjau + tab ---------- */}
      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[17rem_minmax(0,1fr)] xl:gap-12 items-start">
        <div className="lg:sticky lg:top-8 flex flex-col items-center lg:items-stretch gap-3">
          <div className="relative w-full max-w-[17rem] aspect-[9/16] rounded-xl overflow-hidden bg-[#0C0818] shadow-[0_18px_40px_rgb(12_8_26/0.28)]">
            <video
              ref={videoRef}
              key={job.reel_url}
              src={job.reel_url}
              poster={job.cover_url || undefined}
              muted
              loop
              playsInline
              controls
              preload="metadata"
              onTimeUpdate={(e) => setVideoTime(e.currentTarget.currentTime)}
              onLoadedMetadata={(e) => setVideoDuration(e.currentTarget.duration || 0)}
              className="w-full h-full object-cover"
            />
            {!job.cover_url && videoDuration === 0 && (
              <div className="absolute inset-0 flex items-center justify-center p-6 text-center pointer-events-none">
                <span className="font-display font-extrabold text-2xl leading-tight text-white/85">{job.edl?.hook_text}</span>
              </div>
            )}
            {showSafeZone && (
              <div className="absolute inset-0 pointer-events-none flex flex-col justify-between">
                <div className="h-[15%] bg-stop/45 border-b-2 border-dashed border-white/80 flex items-center justify-center">
                  <span className="text-[11px] font-semibold text-white bg-black/60 px-2 py-0.5 rounded">Tertutup tombol IG</span>
                </div>
                <div className="h-[20%] bg-stop/45 border-t-2 border-dashed border-white/80 flex items-center justify-center">
                  <span className="text-[11px] font-semibold text-white bg-black/60 px-2 py-0.5 rounded">Tertutup caption IG</span>
                </div>
              </div>
            )}
          </div>

          <label className="self-center lg:self-start inline-flex items-center gap-2 text-[13px] text-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showSafeZone}
              onChange={(e) => setShowSafeZone(e.target.checked)}
              className="w-4 h-4 accent-[rgb(var(--brand))]"
            />
            Tampilkan area yang tertutup tampilan Instagram
          </label>

          <div className="w-full max-w-[17rem] flex flex-col gap-2">
            <Button
              as="a"
              href={job.reel_url || '#'}
              download={`${job.job_id}.mp4`}
              onClick={(e) => mockDownload(e, 'video')}
              variant="primary"
              icon={Download}
            >
              Unduh video
            </Button>
            <div className="grid grid-cols-2 gap-2">
              <Button
                as="a"
                href={job.cover_url || '#'}
                download={`${job.job_id}.jpg`}
                onClick={(e) => mockDownload(e, 'cover')}
                variant="secondary"
                size="sm"
                icon={ImageIcon}
              >
                Cover
              </Button>
              <Button variant="secondary" size="sm" icon={FileText} onClick={() => setShowReportModal(true)}>
                Laporan
              </Button>
            </div>
            <VariantPanel job={job} />
            <Button variant="ghost" size="sm" icon={Plus} onClick={resetWizardToNew}>
              Buat video baru
            </Button>
          </div>
        </div>

        <div className="min-w-0">
          <div role="tablist" aria-label="Detail hasil" className="flex gap-6 border-b border-line overflow-x-auto overflow-y-hidden scroll-thin">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                id={`tab-${t.id}`}
                aria-selected={tab === t.id}
                aria-controls={`panel-${t.id}`}
                onClick={() => setTab(t.id)}
                className={cx(
                  'relative shrink-0 inline-flex items-center gap-1.5 pb-3 pt-1 text-sm font-semibold whitespace-nowrap transition-colors',
                  tab === t.id ? 'text-ink' : 'text-muted hover:text-ink'
                )}
              >
                {t.label}
                {t.count > 0 && (
                  <span
                    className={cx(
                      'min-w-[1.25rem] h-5 px-1 rounded-full text-[12px] font-bold flex items-center justify-center num',
                      t.alert ? 'bg-stop text-on-stop' : 'bg-sunken text-ink'
                    )}
                  >
                    {t.count}
                  </span>
                )}
                {t.dot && <span className="w-2 h-2 rounded-full bg-stop" aria-label="perlu tindakan" />}
                <span
                  aria-hidden="true"
                  className={cx('absolute left-0 right-0 -bottom-px h-[3px] rounded-t-full', tab === t.id ? 'bg-brand' : 'bg-transparent')}
                />
              </button>
            ))}
          </div>

          <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="pt-6">
            {/* ---------- Siap posting ---------- */}
            {tab === 'posting' && (
              <div className="space-y-6">
                <div>
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <h3 className="font-display font-bold text-xl text-ink">Caption & hashtag</h3>
                    <Button variant="primary" size="sm" icon={copied ? Check : Copy} onClick={copyCaption} disabled={!job.caption}>
                      {copied ? 'Disalin' : 'Salin caption'}
                    </Button>
                  </div>
                  <div className="rounded-lg bg-sunken p-4 text-[15px] leading-relaxed text-ink whitespace-pre-wrap break-words max-h-80 overflow-y-auto scroll-thin">
                    {job.caption ? <span translate="no">{job.caption}</span> : 'Caption belum tersedia.'}
                  </div>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-ink mb-1.5">Saat posting di Instagram</h3>
                  <ul className="text-sm text-muted space-y-1 list-disc pl-5">
                    <li>Audio trending (bila ada di brief tren) ditambahkan manual di aplikasi Instagram.</li>
                    {vo?.mode === 'gemini' && (
                      <li>
                        Aktifkan label <strong className="text-ink">AI info</strong> karena voice over memakai suara AI.
                      </li>
                    )}
                    {!ok && (
                      <li className="text-stop-text font-semibold">
                        Jangan diposting dulu: {problems.length} pemeriksaan wajib belum lolos.
                      </li>
                    )}
                  </ul>
                </div>
              </div>
            )}

            {/* ---------- Edit teks ---------- */}
            {tab === 'edit' && (
              <div className="space-y-5 max-w-2xl">
                <p className="text-sm text-muted">Ubah tulisan di video lalu render ulang. Tidak memanggil AI, jadi tanpa biaya.</p>
                <Field
                  label="Hook (3 detik pertama)"
                  htmlFor="rv-hook"
                  aside={<HookCounter stats={hs} id="rv-hook-count" />}
                  error={hs.over ? 'Terlalu panjang: teks akan tampil kecil. Persingkat.' : null}
                >
                  <input
                    id="rv-hook"
                    type="text"
                    value={form.hook_text}
                    onChange={(e) => setForm((p) => ({ ...p, hook_text: e.target.value }))}
                    aria-describedby="rv-hook-count"
                    className={cx('field', hs.over && 'field-invalid')}
                  />
                </Field>
                <Field label="Ajakan (CTA)" htmlFor="rv-cta">
                  <input
                    id="rv-cta"
                    type="text"
                    value={form.cta_text}
                    onChange={(e) => setForm((p) => ({ ...p, cta_text: e.target.value }))}
                    className="field"
                  />
                </Field>
                {editableSegments.length > 0 && (
                  <fieldset className="space-y-2">
                    <legend className="text-sm font-semibold text-ink mb-1.5">Teks di tengah video</legend>
                    {editableSegments.map((s) => (
                      <div key={s.index} className="flex items-center gap-3">
                        <span className="w-14 shrink-0 text-[13px] text-muted num">{`${formatSec(s.start)} dtk`}</span>
                        <input
                          type="text"
                          value={form.segment_texts[s.index] || ''}
                          onChange={(e) =>
                            setForm((p) => ({ ...p, segment_texts: { ...p.segment_texts, [s.index]: e.target.value } }))
                          }
                          aria-label={`Teks segmen ${s.index + 1}`}
                          className="field"
                        />
                      </div>
                    ))}
                  </fieldset>
                )}
                {subtitles.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-ink">Subtitle (karaoke)</p>
                    <p className="mt-0.5 mb-2 text-[13px] text-muted">
                      Betulkan kata yang salah dengar. Klik waktu untuk memutar bagian itu; waktu suara tidak berubah.
                    </p>
                    <PhraseEditor
                      phrases={subtitles}
                      values={subtitleValues}
                      onChange={editSubtitle}
                      onPlay={playPhrase}
                      activeIndex={phraseAt(subtitles, videoTime)}
                    />
                  </div>
                )}
                {vo && vo.mode !== 'none' && (
                  <p className="text-[13px] text-muted">Selama voice over aktif, teks tengah diganti subtitle dari naskah voice over.</p>
                )}
                <div className="flex justify-end pt-1">
                  <Button variant="brand" icon={RefreshCw} loading={busy} onClick={submitRerender}>
                    {busy ? 'Memulai…' : 'Render ulang'}
                  </Button>
                </div>
              </div>
            )}

            {/* ---------- Voice over ---------- */}
            {tab === 'voice' && vo && <VoiceOverPanel />}

            {/* ---------- Penilaian Critic ---------- */}
            {tab === 'critic' && (
              <div className="space-y-6">
                <VisualReviewPanel visual={job.visual} />
                <CriticPanel critic={job.critic} />
              </div>
            )}

            {/* ---------- Checklist ---------- */}
            {tab === 'checklist' && (
              <div className="border-t border-line">
                {groups.map((g) => {
                  const open = openGroups[g.group] ?? (g.hasFail || g.hasWarn);
                  const panelId = `cg-${g.group.replace(/\W+/g, '-')}`;
                  return (
                    <div key={g.group} className="border-b border-line">
                      <button
                        type="button"
                        onClick={() => setOpenGroups((p) => ({ ...p, [g.group]: !open }))}
                        aria-expanded={open}
                        aria-controls={panelId}
                        className="w-full flex items-center justify-between gap-3 py-3.5 text-left"
                      >
                        <span className="flex items-center gap-2.5 text-sm font-semibold text-ink">
                          <span
                            aria-hidden="true"
                            className={cx('w-2.5 h-2.5 rounded-full', g.hasFail ? 'bg-stop' : g.hasWarn ? 'bg-muted' : 'bg-go')}
                          />
                          {g.group}
                        </span>
                        <span className="flex items-center gap-2 text-[13px] text-muted num">
                          {`${g.passed} dari ${g.items.length} lolos`}
                          <ChevronDown className={cx('w-4 h-4 transition-transform', open && 'rotate-180')} aria-hidden="true" />
                        </span>
                      </button>
                      {open && (
                        <ul id={panelId} className="pb-4 pl-5 space-y-2.5">
                          {g.items.map((it, i) => {
                            const Icon = it.passed ? Check : it.required ? XIcon : AlertTriangle;
                            return (
                              <li key={i} className="flex items-start gap-2.5 text-sm">
                                <Icon
                                  className={cx(
                                    'w-4 h-4 mt-0.5 shrink-0',
                                    it.passed ? 'text-go-text' : it.required ? 'text-stop-text' : 'text-muted'
                                  )}
                                  aria-label={it.passed ? 'lolos' : it.required ? 'gagal' : 'catatan'}
                                />
                                <span className="min-w-0">
                                  <span className="text-ink">{it.name}</span>
                                  {it.detail && <span className="block text-[13px] text-muted break-words">{it.detail}</span>}
                                </span>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
