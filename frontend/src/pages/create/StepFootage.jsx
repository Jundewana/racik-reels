import React, { useState } from 'react';
import { UploadCloud, Film, ArrowRight, AlertTriangle, Play, Check, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { pillarIcon } from '../../lib/constants.js';
import { formatSec } from '../../lib/format.js';
import { Section, ChoiceTile, Button, IconButton, Field, Empty, Dialog, cx } from '../../components/ui.jsx';

function ClipTile({ clip, selected, onToggle, onPreview }) {
  const [broken, setBroken] = useState(false);
  const vertical = clip.height > clip.width;
  const checkId = `clip-${clip.name}`;
  return (
    <li className={cx('min-w-0 transition-opacity', !selected && 'opacity-55')}>
      <button
        type="button"
        onClick={onPreview}
        aria-label={`Putar preview ${clip.name}`}
        className={cx(
          'group relative block w-full aspect-video rounded-md overflow-hidden bg-sunken',
          selected ? 'ring-2 ring-brand ring-offset-2 ring-offset-paper' : ''
        )}
      >
        {clip.thumb_url && !broken ? (
          <img
            src={clip.thumb_url}
            alt=""
            loading="lazy"
            width="320"
            height="180"
            onError={() => setBroken(true)}
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="w-full h-full flex items-center justify-center text-muted/60">
            <Film className="w-6 h-6" aria-hidden="true" />
          </span>
        )}
        <span className="absolute inset-0 flex items-center justify-center bg-[rgb(12_8_26/0.35)] opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition-opacity">
          <span className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center">
            <Play className="w-5 h-5 text-[#1C1433] translate-x-px" aria-hidden="true" />
          </span>
        </span>
        <span className="absolute bottom-1.5 right-1.5 rounded bg-[rgb(12_8_26/0.75)] px-1.5 py-0.5 text-[12px] font-semibold text-white num">
          {`${formatSec(clip.duration)} dtk`}
        </span>
      </button>
      <label htmlFor={checkId} className="mt-2 flex items-start gap-2 cursor-pointer">
        <input
          id={checkId}
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="mt-0.5 w-4 h-4 shrink-0 accent-[rgb(var(--brand))]"
        />
        <span className="min-w-0">
          <span className="block text-[13px] font-medium text-ink truncate" title={clip.name}>
            {clip.name}
          </span>
          <span className="block text-[12px] text-muted num">
            {vertical ? 'Vertikal' : 'Horizontal'}, {clip.size_mb} MB
          </span>
        </span>
      </label>
    </li>
  );
}

/** Preview klip footage mentah + pilih/batal pakai, dengan navigasi ke klip sebelum/berikutnya. */
function ClipPreview({ index, onClose, onNavigate }) {
  const { clips, isClipSelected, toggleClip, useMock } = useStudio();
  const clip = clips[index];
  if (!clip) return null;
  const selected = isClipSelected(clip.name);
  const vertical = clip.height > clip.width;
  return (
    <Dialog
      open
      onClose={onClose}
      size="lg"
      title={clip.name}
      labelledBy="clip-preview-title"
      actions={
        <>
          <span className="mr-auto self-center text-[13px] text-muted num">{`${index + 1} dari ${clips.length}`}</span>
          <IconButton label="Klip sebelumnya" icon={ChevronLeft} onClick={() => onNavigate(-1)} disabled={index === 0} />
          <IconButton
            label="Klip berikutnya"
            icon={ChevronRight}
            onClick={() => onNavigate(1)}
            disabled={index === clips.length - 1}
          />
          <Button variant={selected ? 'secondary' : 'brand'} icon={selected ? X : Check} onClick={() => toggleClip(clip.name)}>
            {selected ? 'Jangan pakai klip ini' : 'Pakai klip ini'}
          </Button>
        </>
      }
    >
      <div className="rounded-lg overflow-hidden bg-[#0C0818] flex items-center justify-center">
        {clip.video_url ? (
          <video
            key={clip.video_url}
            src={clip.video_url}
            poster={clip.thumb_url || undefined}
            controls
            autoPlay
            muted
            playsInline
            preload="metadata"
            className="w-full max-h-[60vh] object-contain"
          />
        ) : (
          <p className="px-6 py-16 text-center text-sm text-white/80 max-w-md">
            {useMock
              ? 'Mode simulasi: preview video tersedia saat terhubung ke laptop.'
              : 'Server Racik masih versi lama sehingga belum bisa memutar preview. Tutup terminal server lalu jalankan lagi: python main.py --web'}
          </p>
        )}
      </div>
      <p className="mt-3 text-[13px] text-muted num">
        {`${formatSec(clip.duration)} dtk, ${clip.width}×${clip.height} (${vertical ? 'vertikal' : 'horizontal'}), ${clip.size_mb} MB. `}
        <span className={selected ? 'text-go-text font-semibold' : 'text-stop-text font-semibold'}>
          {selected ? 'Dipakai untuk video ini.' : 'Tidak dipakai.'}
        </span>
      </p>
    </Dialog>
  );
}

export default function StepFootage() {
  const {
    options,
    form,
    clips,
    loadingClips,
    uploadQueue,
    selectPillar,
    selectFolder,
    uploadFiles,
    getPillarLabel,
    setWizardStep,
    selectedClipNames,
    isClipSelected,
    toggleClip,
    selectAllClips,
    clearClipSelection
  } = useStudio();
  const [dragging, setDragging] = useState(false);
  const [previewIdx, setPreviewIdx] = useState(null);
  const nSelected = selectedClipNames.length;

  return (
    <div>
      <Section id="pilar" title="Pilar konten" description="Menentukan struktur cerita, gaya bawaan, dan hashtag.">
        <div role="radiogroup" aria-label="Pilar konten" className="grid grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5 gap-3">
          {options.pillars.map((p) => {
            const Icon = pillarIcon(p.id);
            const selected = form.pillar === p.id;
            return (
              <ChoiceTile key={p.id} selected={selected} onClick={() => selectPillar(p.id)} className="flex flex-col gap-3">
                <Icon className={cx('w-5 h-5', selected ? 'text-brand' : 'text-muted')} aria-hidden="true" />
                <span>
                  <span className="block font-display font-bold text-xl leading-tight text-ink">{p.label}</span>
                  <span className="mt-1 block text-[13px] leading-snug text-muted line-clamp-2">{p.default_brief}</span>
                </span>
              </ChoiceTile>
            );
          })}
        </div>
      </Section>

      <Section id="footage" title="Video mentah" description="Unggah dari laptop atau HP, atau pakai folder yang sudah berisi video.">
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[18rem_minmax(0,1fr)]">
          <div className="space-y-5">
            <label
              htmlFor="footage-file-input"
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setDragging(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                if (e.dataTransfer?.files?.length) uploadFiles(e.dataTransfer.files);
              }}
              className={cx(
                'flex flex-col items-center justify-center text-center gap-2 rounded-lg border-2 border-dashed px-4 py-7 cursor-pointer transition-colors',
                dragging ? 'border-brand bg-brand-soft' : 'border-line hover:border-brand/60 bg-surface'
              )}
            >
              <UploadCloud className="w-7 h-7 text-brand" aria-hidden="true" />
              <span className="text-sm font-semibold text-ink">Tarik video ke sini, atau pilih file</span>
              <span className="text-[13px] text-muted">
                .mp4 atau .mov, boleh banyak sekaligus. Masuk ke folder {getPillarLabel(form.pillar)}.
              </span>
              <input
                id="footage-file-input"
                type="file"
                accept=".mp4,.mov,video/mp4,video/quicktime"
                multiple
                className="sr-only"
                onChange={(e) => {
                  if (e.target.files?.length) uploadFiles(e.target.files);
                  e.target.value = '';
                }}
              />
            </label>

            {uploadQueue.length > 0 && (
              <ul className="space-y-3" aria-label="Unggahan">
                {uploadQueue.map((u) => (
                  <li key={u.id} className="text-[13px]">
                    <div className="flex items-center justify-between gap-3 mb-1">
                      <span className="truncate text-ink">{u.name}</span>
                      <span
                        className={cx(
                          'shrink-0 num font-semibold',
                          u.status === 'done' ? 'text-go-text' : u.status === 'error' ? 'text-stop-text' : 'text-muted'
                        )}
                      >
                        {u.status === 'done' ? 'Selesai' : u.status === 'error' ? 'Gagal' : `${u.progress}%`}
                      </span>
                    </div>
                    <div className="h-1 rounded-full bg-sunken overflow-hidden">
                      <div
                        className={cx('h-full transition-[width] duration-150', u.status === 'error' ? 'bg-stop' : 'bg-brand')}
                        style={{ width: `${u.progress}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <Field label="Folder footage" htmlFor="folder-select">
              <select id="folder-select" value={form.input_path} onChange={(e) => selectFolder(e.target.value)} className="field">
                {options.footage_folders.map((f) => (
                  <option key={f.path} value={f.path}>
                    {`${f.path} (${f.count} video)`}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <div className="min-w-0">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2 mb-3">
              <p className="text-sm text-muted" aria-live="polite">
                <span className="font-display font-bold text-2xl text-ink num">{nSelected}</span>
                {` dari ${clips.length} klip dipakai, di `}
                <span className="text-ink">{form.input_path}</span>
              </p>
              {clips.length > 0 && (
                <span className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={selectAllClips} disabled={nSelected === clips.length}>
                    Pilih semua
                  </Button>
                  <Button variant="ghost" size="sm" onClick={clearClipSelection} disabled={nSelected === 0}>
                    Kosongkan
                  </Button>
                </span>
              )}
            </div>
            {loadingClips ? (
              <p className="py-12 text-center text-sm text-muted">Memuat daftar klip…</p>
            ) : clips.length === 0 ? (
              <Empty
                title="Folder ini masih kosong"
                action={
                  <Button as="label" htmlFor="footage-file-input" variant="brand" icon={UploadCloud} className="cursor-pointer">
                    Unggah video
                  </Button>
                }
              >
                Unggah minimal satu video mentah supaya AI punya adegan untuk dipilih.
              </Empty>
            ) : (
              <ul className="grid grid-cols-2 sm:grid-cols-3 2xl:grid-cols-4 gap-x-3 gap-y-4 xl:max-h-[30rem] xl:overflow-y-auto xl:pr-1 scroll-thin">
                {clips.map((clip, i) => (
                  <ClipTile
                    key={clip.name}
                    clip={clip}
                    selected={isClipSelected(clip.name)}
                    onToggle={() => toggleClip(clip.name)}
                    onPreview={() => setPreviewIdx(i)}
                  />
                ))}
              </ul>
            )}
          </div>
        </div>
      </Section>

      <div className="border-t border-line pt-6 flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-3">
        {nSelected === 0 && (
          <p className="text-[13px] text-muted flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4" aria-hidden="true" /> Pilih minimal 1 klip untuk lanjut.
          </p>
        )}
        <Button variant="primary" size="lg" iconEnd={ArrowRight} onClick={() => setWizardStep(2)} disabled={nSelected === 0}>
          Lanjut ke pengaturan
        </Button>
      </div>

      {previewIdx !== null && (
        <ClipPreview
          index={previewIdx}
          onClose={() => setPreviewIdx(null)}
          onNavigate={(d) => setPreviewIdx((i) => Math.min(clips.length - 1, Math.max(0, i + d)))}
        />
      )}
    </div>
  );
}
