import React, { useEffect, useState } from 'react';
import { ArrowLeft, Clapperboard, Upload, FileText, ChevronDown, Mic } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { VOICEOVER_MODES } from '../../lib/constants.js';
import { formatStyleName, formatSec, formatLength } from '../../lib/format.js';
import { Section, ChoiceTile, Button, Field, HookCounter, Segmented, cx } from '../../components/ui.jsx';
import EngineChoice, { engineLabel } from '../../components/EngineChoice.jsx';
import TranscriptReview from './TranscriptReview.jsx';
import MusicPicker from './MusicPicker.jsx';
import HighlightFinder from './HighlightFinder.jsx';

const QUICK_DURATIONS = [15, 20, 30, 45];
const LONG_TALK_SEC = 300; // video bicara > 5 menit → tawarkan cari cuplikan
const TALK_MAX_SEC = 600;
const TALK_HINT_SEC = 180; // klip > 3 menit kemungkinan video bicara/podcast // > 10 menit → wajib lewat cari cuplikan (sama dengan server)

export default function StepSettings() {
  const {
    options,
    form,
    setForm,
    clips,
    selectedClipNames,
    hookStats,
    hooksConfig,
    getPillarLabel,
    getMusicName,
    submittingJob,
    submitCreateJob,
    setWizardStep,
    narrations,
    uploadNarration,
    uploadingNarration,
    narrationDraft,
    transcribing,
    savingDraft,
    selectNarration,
    transcribeNarration,
    saveNarrationDraft,
    transcribeTalk,
    resetNarrationDraft,
    highlight,
    highlightRanks,
    createFromHighlights,
    creatingClips
  } = useStudio();
  const isNarasi = form.flow === 'narasi';
  const isBicara = form.flow === 'bicara';
  // video bicara: pembicara diambil dari klip yang sudah dipilih di langkah Footage (bawaan: yang terpanjang)
  const pickedClips = clips.filter((c) => selectedClipNames.includes(c.name));
  const talkClip = pickedClips.find((c) => c.name === form.talk_clip) || null;
  const tooLongTalk = isBicara && (talkClip?.duration || 0) > TALK_MAX_SEC;
  // cuplikan dicentang → tombol utama membuat satu Reel per cuplikan (bukan satu Reel dari seluruh video)
  const fromClips = isBicara && highlight?.state === 'selesai' && highlightRanks.length > 0;
  // draf transkrip video bicara hanya berlaku untuk video & panjang Reel yang sama
  const talkDraft = isBicara && narrationDraft?.kind === 'bicara' && narrationDraft.speaker_clip === form.talk_clip
    && Boolean(narrationDraft.talk_full) === Boolean(form.talk_full) ? narrationDraft : null;
  const talkDraftPending = Boolean(talkDraft) && !form.narration_draft && !fromClips;
  useEffect(() => {
    if (narrationDraft?.kind === 'bicara' && !talkDraft) resetNarrationDraft();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.talk_clip, form.talk_full, form.flow]);
  const longestPicked = pickedClips.reduce((a, c) => ((c.duration || 0) > (a?.duration || 0) ? c : a), null);
  useEffect(() => {
    if (!isBicara) return;
    if (!form.talk_clip || !pickedClips.some((c) => c.name === form.talk_clip)) {
      setForm((prev) => ({ ...prev, talk_clip: longestPicked ? longestPicked.name : null }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isBicara, selectedClipNames.join('|')]);
  const chosenNarration = narrations.find((n) => n.path === form.narration_path);
  const set = (patch) => setForm((prev) => ({ ...prev, ...patch }));
  const hs = hookStats(form.hook_text);
  const suggestions = hooksConfig[form.pillar] || [];
  const selectedStyle = options.styles.find((s) => s.id === form.style);

  const [showAdvanced, setShowAdvanced] = useState(false);
  const purposeLabel = { promosi: 'Promosi (dengan CTA)', informasi: 'Informasi (tanpa CTA)' }[form.purpose] || 'Dipilih AI';
  const privacyLabel = [form.blur_faces && !isBicara && 'blur wajah', form.blur_plates && 'blur pelat'].filter(Boolean).join(', ') || 'Tanpa blur';
  const advancedSummary = `Tujuan: ${purposeLabel.toLowerCase()}. Watermark ${form.logo !== false ? 'tampil' : 'mati'}. `
    + `Privasi: ${privacyLabel.toLowerCase()}. Mesin AI: ${engineLabel(options, form.engine)}.`;
  // footage vs alur: video panjang (podcast/kuliah) cocoknya Video bicara; b-roll pendek cocoknya Video dulu/Narasi
  const longClips = pickedClips.filter((c) => (c.duration || 0) > TALK_HINT_SEC);
  const tooLongMontage = !isBicara && pickedClips.some((c) => (c.duration || 0) > TALK_MAX_SEC);
  const brollOnly = isBicara && pickedClips.length > 0 && pickedClips.every((c) => (c.duration || 0) < 20);
  const summary = [
    ['Pilar', getPillarLabel(form.pillar)],
    ['Footage', `${selectedClipNames.length} dari ${clips.length} klip, ${form.input_path}`],
    ['Gaya', formatStyleName(form.style)],
    ['Alur', isNarasi ? 'Narasi dulu (ikut suara)' : isBicara ? 'Video bicara' : 'Video dulu (ikut musik)'],
    form.purpose && ['Tujuan', purposeLabel],
    ...(isBicara ? [['Pembicara', form.talk_clip || 'Belum dipilih']] : []),
    ['Durasi', isNarasi ? (chosenNarration ? `±${Math.round(chosenNarration.duration)} detik, mengikuti narasi` : 'mengikuti narasi')
      : isBicara ? (form.talk_full ? 'Utuh, ikut panjang video (maks 3 mnt)' : 'Ringkas 30–45 detik')
      : `${form.duration} detik`],
    form.hook_text.trim() && ['Hook', form.hook_text.trim()],
    ['Musik', form.no_music ? 'Tanpa musik' : form.music_file ? getMusicName(form.music_file) : 'Otomatis sesuai gaya'],
    isNarasi && ['Narasi', chosenNarration ? chosenNarration.name : 'Belum dipilih'],
    !isNarasi && !isBicara && form.voiceover !== 'none'
      && ['Voice over', { rekam: 'Suara sendiri, direkam nanti', gemini: `Suara AI (${form.voice})` }[form.voiceover]],
    form.engine !== 'api' && ['Mesin AI', engineLabel(options, form.engine)],
    form.logo === false && ['Watermark', 'Tanpa watermark'],
    privacyLabel !== 'Tanpa blur' && ['Privasi', privacyLabel]
  ].filter(Boolean); // nilai bawaan disembunyikan; lihat Pengaturan lanjutan

  return (
    <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1fr)_20rem] xl:gap-12 items-start">
      <div className="min-w-0">
        <Section
          id="flow"
          layout="stack"
          title="Alur"
          description="Pilih apa yang menentukan tempo video: ketukan musik, atau suara narasi."
        >
          <div role="radiogroup" aria-label="Alur" className="grid sm:grid-cols-3 gap-3">
            <ChoiceTile selected={!isNarasi && !isBicara} onClick={() => set({ flow: 'video' })}>
              <span className="block font-display font-bold text-xl leading-tight text-ink">Video dulu</span>
              <span className="mt-1 block text-[13px] leading-snug text-muted">
                Montase ikut ketukan musik, durasi Anda tentukan. Voice over opsional, direkam setelah video jadi.
              </span>
            </ChoiceTile>
            <ChoiceTile selected={isNarasi} onClick={() => set({ flow: 'narasi' })}>
              <span className="block font-display font-bold text-xl leading-tight text-ink">Narasi dulu</span>
              <span className="mt-1 block text-[13px] leading-snug text-muted">
                Rekaman suara jadi patokan: gambar dipilih per kalimat, durasi mengikuti narasi, subtitle karaoke otomatis.
              </span>
            </ChoiceTile>
            <ChoiceTile selected={isBicara} onClick={() => set({ flow: 'bicara' })}>
              <span className="block font-display font-bold text-xl leading-tight text-ink">Video bicara</span>
              <span className="mt-1 block text-[13px] leading-snug text-muted">
                Orang bicara ke kamera (penjelasan, testimoni, podcast): diringkas AI jadi 30–45 dtk atau dipakai utuh, fokus ke wajah, subtitle karaoke.
              </span>
            </ChoiceTile>
          </div>

          {!isBicara && longClips.length > 0 && (
            <div className={cx('mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border px-3.5 py-3',
              tooLongMontage ? 'border-stop/50' : 'border-line')} role="status">
              <p className={cx('min-w-0 flex-1 text-[13px]', tooLongMontage ? 'font-semibold text-stop-text' : 'text-ink')}>
                {tooLongMontage
                  ? `${longClips[0].name} (${formatLength(longClips[0].duration)}) terlalu panjang untuk ${isNarasi ? 'Narasi dulu' : 'Video dulu'}. Kalau isinya orang bicara (podcast/kuliah), pakai Video bicara lalu Cari cuplikan; kalau b-roll, potong dulu jadi klip pendek.`
                  : `${longClips[0].name} (${formatLength(longClips[0].duration)}) sepertinya video orang bicara. Alur Video bicara memakai suaranya langsung dan fokus ke wajah.`}
              </p>
              <Button variant="secondary" size="sm" icon={Mic} onClick={() => set({ flow: 'bicara' })}>
                Pakai Video bicara
              </Button>
            </div>
          )}
          {brollOnly && (
            <p className="mt-4 rounded-lg border border-line px-3.5 py-3 text-[13px] text-ink" role="status">
              Klip yang dipilih pendek-pendek (di bawah 20 dtk), seperti b-roll. Video bicara butuh video orang yang berbicara;
              untuk b-roll pakai Video dulu, atau Narasi dulu bila ada rekaman suara.
            </p>
          )}

          {isBicara && (
            <div className="mt-5">
              <p className="text-sm font-semibold text-ink mb-2">Video pembicara</p>
              {pickedClips.length === 0 ? (
                <p className="text-sm text-stop-text">Pilih minimal satu video di langkah Footage.</p>
              ) : pickedClips.length === 1 ? (
                <p className="text-sm text-ink">
                  {pickedClips[0].name}
                  <span className="text-muted num">{pickedClips[0].duration ? `, ${formatLength(pickedClips[0].duration)}` : ''}</span>
                  <span className="block text-[13px] text-muted">Dari video yang Anda pilih di langkah Footage.</span>
                </p>
              ) : (
                <>
                  <label htmlFor="talk-clip" className="sr-only">Video pembicara</label>
                  <select
                    id="talk-clip"
                    value={form.talk_clip || ''}
                    onChange={(e) => set({ talk_clip: e.target.value })}
                    className="w-full max-w-md rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand"
                  >
                    {pickedClips.map((c) => (
                      <option key={c.name} value={c.name}>
                        {c.duration ? `${c.name} (${formatLength(c.duration)})` : c.name}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1.5 text-[13px] text-muted">
                    Video lain yang Anda pilih di langkah Footage dipakai sebagai sisipan gambar (b-roll).
                  </p>
                </>
              )}
              <div className="mt-4">
                <p className="text-sm font-semibold text-ink mb-2">Panjang Reel</p>
                <Segmented
                  label="Panjang Reel"
                  value={form.talk_full ? 'utuh' : 'ringkas'}
                  onChange={(id) => set({ talk_full: id === 'utuh' })}
                  options={[
                    { id: 'ringkas', label: 'Ringkas 30–45 dtk' },
                    { id: 'utuh', label: 'Utuh, ikut panjang video' }
                  ]}
                />
                <p className="mt-1.5 text-[13px] text-muted">
                  {form.talk_full
                    ? 'Seluruh ucapan dipakai (jeda, "eee", dan pengulangan tetap dibuang), maksimal 3 menit sesuai batas Reels. Cocok untuk cuplikan pembahasan yang utuh.'
                    : 'AI memilih kalimat terkuat dan menyusunnya jadi Reel 30–45 detik dengan hook di awal.'}
                </p>
              </div>
              {talkClip && !tooLongTalk && !fromClips && (
                <div className="mt-4">
                  {!talkDraft ? (
                    <>
                      <Button variant="secondary" size="sm" icon={FileText} loading={transcribing} onClick={transcribeTalk}>
                        {transcribing ? 'Mentranskripsi…' : 'Transkrip & periksa subtitle'}
                      </Button>
                      <p className="mt-1.5 text-[13px] text-muted">
                        Disarankan: AI memilih kalimat dan membetulkan salah dengar, lalu Anda periksa sebelum video dibuat.
                        Tanpa ini, subtitle hanya dikoreksi AI (masih bisa dibetulkan di halaman Hasil).
                      </p>
                    </>
                  ) : (
                    <TranscriptReview draft={talkDraft} saving={savingDraft} onSave={saveNarrationDraft} />
                  )}
                </div>
              )}
              {talkClip && (talkClip.duration || 0) > LONG_TALK_SEC && <HighlightFinder clip={talkClip} />}
            </div>
          )}

          {isNarasi && (
            <div className="mt-5">
              <p className="text-sm font-semibold text-ink mb-2">Rekaman narasi</p>
              {narrations.length === 0 ? (
                <p className="text-sm text-muted mb-3">Belum ada rekaman. Unggah dari HP atau laptop (mp3, m4a, wav, atau video).</p>
              ) : (
                <ul role="radiogroup" aria-label="Rekaman narasi" className="space-y-2 mb-3">
                  {narrations.map((n) => {
                    const checked = form.narration_path === n.path;
                    return (
                      <li
                        key={n.path}
                        className={cx(
                          'rounded-lg border px-3.5 py-3 transition-colors',
                          checked ? 'border-brand ring-1 ring-brand bg-brand-soft/60' : 'border-line bg-surface'
                        )}
                      >
                        <label className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="radio"
                            name="narration_choice"
                            checked={checked}
                            onChange={() => selectNarration(n.path)}
                            className="w-4 h-4 accent-[rgb(var(--brand))] shrink-0"
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block text-sm font-semibold text-ink truncate">{n.name}</span>
                            <span className="block text-[13px] text-muted num">{`${formatSec(n.duration)} dtk, ${n.size_mb} MB`}</span>
                          </span>
                        </label>
                        {checked && n.url && <audio src={n.url} controls preload="none" className="mt-2 w-full h-9" />}
                      </li>
                    );
                  })}
                </ul>
              )}
              <Button as="label" variant="secondary" size="sm" icon={Upload} className="cursor-pointer">
                {uploadingNarration ? 'Mengunggah…' : 'Unggah rekaman narasi'}
                <input
                  type="file"
                  accept="audio/*,video/*,.m4a,.mp3,.wav,.aac,.mp4,.mov"
                  className="sr-only"
                  onChange={(e) => {
                    const f = (e.target.files || [])[0];
                    e.target.value = '';
                    if (f) uploadNarration(f);
                  }}
                />
              </Button>
              <p className="mt-2 text-[13px] text-muted">
                Jeda panjang dan "eee/emm" dibuang otomatis. Maksimal 90 detik setelah dibersihkan.
              </p>

              {form.narration_path && !narrationDraft && (
                <div className="mt-4">
                  <Button variant="brand" size="sm" icon={FileText} loading={transcribing} onClick={transcribeNarration}>
                    {transcribing ? 'Mentranskripsi… (±1 menit)' : 'Transkrip & periksa'}
                  </Button>
                  <p className="mt-1.5 text-[13px] text-muted">
                    Suara diubah jadi teks, salah dengar dikoreksi AI, lalu Anda periksa sebelum video dibuat.
                  </p>
                </div>
              )}
              {narrationDraft && (
                <TranscriptReview draft={narrationDraft} saving={savingDraft} onSave={saveNarrationDraft} />
              )}
            </div>
          )}
        </Section>

        <Section id="brief" layout="stack" title="Instruksi" description="Pesan utama video. AI memakainya untuk memilih adegan dan menulis teks.">
          <textarea
            id="brief-input"
            aria-labelledby="brief-title"
            rows={3}
            value={form.brief}
            onChange={(e) => set({ brief: e.target.value })}
            placeholder="Mis. promo sewa motor untuk wisatawan yang mau keliling Garut"
            className="field resize-y"
          />
        </Section>

        <Section id="style" layout="stack" title="Gaya editing" description="Menentukan tempo potongan, transisi, dan suasana musik.">
          <div role="radiogroup" aria-label="Gaya editing" className="grid sm:grid-cols-2 gap-3">
            {options.styles.map((st) => (
              <ChoiceTile key={st.id} selected={form.style === st.id} onClick={() => set({ style: st.id })}>
                <span className="block font-display font-bold text-xl leading-tight text-ink">{formatStyleName(st.id)}</span>
                <span className="mt-1 block text-[13px] leading-snug text-muted">{st.description}</span>
                <span className="mt-3 block text-[13px] text-ink num">
                  Potongan {formatSec(st.cut_pace_sec[0])}–{formatSec(st.cut_pace_sec[1])} dtk, musik {st.music_mood_default}
                </span>
              </ChoiceTile>
            ))}
          </div>
        </Section>

        {!isNarasi && !isBicara && (
        <Section id="duration" layout="stack" title="Durasi" description="Hasil akhir boleh meleset ±10% agar potongan jatuh di ketukan musik.">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <p className="font-display font-extrabold text-5xl leading-none text-ink num">
              {form.duration}
              <span className="ml-1.5 text-xl font-bold text-muted">detik</span>
            </p>
            <Segmented
              label="Durasi cepat"
              size="sm"
              value={QUICK_DURATIONS.includes(Number(form.duration)) ? Number(form.duration) : null}
              onChange={(sec) => set({ duration: sec })}
              options={QUICK_DURATIONS.map((s) => ({ id: s, label: `${s} dtk` }))}
            />
          </div>
          <input
            type="range"
            min={8}
            max={90}
            step={1}
            value={form.duration}
            onChange={(e) => set({ duration: Number(e.target.value) })}
            aria-label="Target durasi (detik)"
            className="mt-4 w-full accent-[rgb(var(--brand))] cursor-pointer"
          />
          <div className="flex justify-between text-[12px] text-muted num">
            <span>8 dtk</span>
            <span>90 dtk</span>
          </div>
        </Section>
        )}

        <Section id="text" layout="stack" title="Teks di video" description="Kosongkan bila ingin AI yang menulis.">
          <div className="space-y-5">
            <Field
              label="Hook di 3 detik pertama"
              htmlFor="hook-input"
              optional
              aside={<HookCounter stats={hs} id="hook-count" />}
              error={hs.over ? 'Terlalu panjang: teks akan tampil kecil. Persingkat agar terbaca dalam 1,5 detik.' : null}
            >
              <input
                id="hook-input"
                type="text"
                value={form.hook_text}
                onChange={(e) => set({ hook_text: e.target.value })}
                placeholder="Kosongkan agar AI memilih"
                aria-describedby="hook-count"
                className={cx('field', hs.over && 'field-invalid')}
              />
            </Field>
            {suggestions.length > 0 && (
              <div>
                <p className="text-[13px] text-muted mb-2">Dari pustaka hook {getPillarLabel(form.pillar)}:</p>
                <div className="flex flex-wrap gap-2">
                  {suggestions.map((h, idx) => {
                    const active = form.hook_text === h.text;
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => set({ hook_text: h.text })}
                        aria-pressed={active}
                        className={cx(
                          'rounded-md border-l-[3px] border-hook px-2.5 py-1 text-[13px] font-semibold transition-colors',
                          active ? 'bg-hook text-on-hook' : 'bg-hook/15 text-ink hover:bg-hook/30'
                        )}
                      >
                        {h.text}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            <Field label="Ajakan (CTA) di akhir video" htmlFor="cta-input" optional hint="Bila kosong, memakai CTA default pilar ini.">
              <input
                id="cta-input"
                type="text"
                value={form.cta_text}
                onChange={(e) => set({ cta_text: e.target.value })}
                placeholder={options.default_cta[form.pillar] || 'Booking sekarang via WhatsApp (000) 0000000!'}
                className="field"
              />
            </Field>
          </div>
        </Section>

        {!isNarasi && !isBicara && (
        <Section id="voice" layout="stack" title="Voice over" description="AI menulis naskahnya. Anda bisa memeriksa dan mengedit naskah di halaman hasil.">
          <div role="radiogroup" aria-label="Voice over" className="grid sm:grid-cols-3 gap-3">
            {VOICEOVER_MODES.map((o) => (
              <ChoiceTile key={o.id} selected={form.voiceover === o.id} onClick={() => set({ voiceover: o.id })} className="p-3.5">
                <span className="block text-sm font-semibold text-ink">{o.label}</span>
                <span className="mt-0.5 block text-[13px] leading-snug text-muted">{o.desc}</span>
              </ChoiceTile>
            ))}
          </div>
          {form.voiceover === 'gemini' && (
            <div className="mt-4">
              <p className="text-sm font-semibold text-ink mb-2">Karakter suara</p>
              <Segmented
                label="Karakter suara"
                value={form.voice}
                onChange={(id) => set({ voice: id })}
                options={(options.voices || []).map((v) => ({ id: v.id, label: `${v.id}, ${v.description}` }))}
              />
            </div>
          )}
        </Section>
        )}

        <Section id="music" layout="stack" title="Musik latar" description="Semua lagu bebas royalti. Dengarkan cuplikan 10 detik sebelum memilih.">
          <MusicPicker
            value={form.music_file}
            onChange={(path) => set({ music_file: path })}
            styleMood={selectedStyle?.music_mood_default}
            noMusic={Boolean(form.no_music)}
            onNoMusic={(v) => set({ no_music: v })}
            silentHint={
              isNarasi || isBicara
                ? 'Hanya suara narasi atau pembicara, tanpa latar musik'
                : 'Video senyap; tambahkan audio trending sendiri saat unggah di Instagram'
            }
          />
        </Section>

        <Section
          id="advanced"
          layout="stack"
          title="Pengaturan lanjutan"
          description={advancedSummary}
          aside={
            <Button
              variant="ghost"
              size="sm"
              icon={ChevronDown}
              onClick={() => setShowAdvanced((v) => !v)}
              aria-expanded={showAdvanced}
              aria-controls="advanced-panel"
              className={cx('[&_svg]:transition-transform', showAdvanced && '[&_svg]:rotate-180')}
            >
              {showAdvanced ? 'Tutup' : 'Ubah'}
            </Button>
          }
        />
        {showAdvanced && (
          <div id="advanced-panel">
        <Section id="purpose" layout="stack" title="Tujuan video">
            <Segmented
              label="Tujuan video"
              value={form.purpose || ''}
              onChange={(id) => set({ purpose: id })}
              options={[
                { id: '', label: 'Pilih otomatis' },
                { id: 'promosi', label: 'Promosi' },
                { id: 'informasi', label: 'Informasi' }
              ]}
            />
            <p className="mt-1.5 text-[13px] text-muted">
              Promosi: ada ajakan booking/konsultasi + nomor WhatsApp di akhir. Informasi (kuliah, edukasi, ucapan): tanpa
              CTA, musik lebih pelan.
            </p>
          </Section>

        <Section id="logo" layout="stack" title="Watermark" description="Logo kecil di pojok video sebagai tanda akun.">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.logo !== false}
              onChange={(e) => set({ logo: e.target.checked })}
              className="mt-1 w-4 h-4 accent-[rgb(var(--brand))]"
            />
            <span>
              <span className="block text-sm font-semibold text-ink">Tampilkan watermark</span>
              <span className="block text-[13px] text-muted">Matikan bila video akan diunggah ulang oleh pihak lain atau ingin tampil polos.</span>
            </span>
          </label>
        </Section>

        <Section
          id="privacy"
          layout="stack"
          title="Privasi"
          description="Samarkan otomatis bila video memperlihatkan pelanggan tanpa izin atau pelat nomor. Biarkan mati bila wajah memang ingin ditampilkan."
        >
          <div className="space-y-3">
            {[
              {
                key: 'blur_faces',
                label: 'Samarkan wajah',
                hint: isBicara ? 'Tidak tersedia untuk video bicara: wajah pembicara ikut tersamar.' : 'Deteksi wajah otomatis, tiap frame.',
                off: isBicara
              },
              { key: 'blur_plates', label: 'Samarkan pelat nomor', hint: 'Pelat kecil atau miring bisa terlewat; periksa hasilnya.' }
            ].map((o) => (
              <label key={o.key} className={cx('flex items-start gap-3', o.off ? 'opacity-60' : 'cursor-pointer')}>
                <input
                  type="checkbox"
                  disabled={o.off}
                  checked={!o.off && Boolean(form[o.key])}
                  onChange={(e) => set({ [o.key]: e.target.checked })}
                  className="mt-1 w-4 h-4 accent-[rgb(var(--brand))]"
                />
                <span>
                  <span className="block text-sm font-semibold text-ink">{o.label}</span>
                  <span className="block text-[13px] text-muted">{o.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </Section>

        {(
          <Section id="penyusun" layout="stack" title="Penyusun edit" description="Siapa yang memilih potongan dan menyusun video dari footage Anda.">
            <div role="radiogroup" aria-label="Penyusun edit" className="grid sm:grid-cols-3 gap-3">
              <ChoiceTile selected={!form.remotion} onClick={() => set({ remotion: false })}>
                <span className="font-display font-bold text-xl leading-tight text-ink">Director AI</span>
                <span className="mt-1 block text-[13px] leading-snug text-muted">Gemini atau Groq memilih potongan, FFmpeg merender. Cepat dan murah, tapi gaya dan potongan lebih kaku.</span>
              </ChoiceTile>
              <ChoiceTile selected={Boolean(form.remotion) && (form.agen || 'claude') === 'claude'} onClick={() => set({ remotion: true, agen: 'claude' })}>
                <span className="font-display font-bold text-xl leading-tight text-ink">Claude + Remotion</span>
                <span className="mt-1 block text-[13px] leading-snug text-muted">Claude Code melihat footage, memotong, dan menulis komposisi Remotion. Memakai langganan Claude Anda, butuh sekitar 5 sampai 15 menit.</span>
              </ChoiceTile>
              <ChoiceTile selected={Boolean(form.remotion) && form.agen === 'antigravity'} onClick={() => set({ remotion: true, agen: 'antigravity' })}>
                <span className="font-display font-bold text-xl leading-tight text-ink">Antigravity + Remotion</span>
                <span className="mt-1 block text-[13px] leading-snug text-muted">Cadangan saat Claude limit: agen Antigravity (API Gemini) melihat lembar kontak dan menulis komposisi Remotion yang sama.</span>
              </ChoiceTile>
            </div>
            {form.remotion && (
              <label className="mt-3 flex items-start gap-3 rounded-lg border border-line p-3 cursor-pointer">
                <input
                  type="checkbox"
                  name="musik_claude"
                  disabled={Boolean(form.no_music)}
                  checked={Boolean(form.musik_claude) && !form.no_music}
                  onChange={(e) => set({ musik_claude: e.target.checked })}
                  className="mt-1 w-4 h-4 accent-[rgb(var(--brand))]"
                />
                <span>
                  <span className="block text-sm font-semibold text-ink">Musik dan efek suara orisinal dari Claude</span>
                  <span className="block text-[13px] text-muted">Claude menggubah lagu dan efek suara sendiri (bebas hak cipta) alih-alih memakai lagu dari folder musik. Hasilnya bergaya jingle ceria dan butuh waktu sedikit lebih lama.</span>
                </span>
              </label>
            )}
          </Section>
        )}

        {!form.remotion && (
        <Section id="engine" layout="stack" title="Mesin AI" description="Siapa yang melihat adegan dan menyusun edit. Render video tetap di laptop ini.">
          <EngineChoice value={form.engine} onChange={(engine) => set({ engine })} />
        </Section>
        )}
          </div>
        )}
      </div>

      <aside aria-labelledby="summary-title" className="xl:sticky xl:top-8 border-t-[3px] border-brand pt-5">
        <h2 id="summary-title" className="font-display font-bold text-2xl text-ink">
          Ringkasan
        </h2>
        <dl className="mt-4 divide-y divide-line text-sm">
          {summary.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 py-2.5">
              <dt className="text-muted shrink-0">{k}</dt>
              <dd className="font-medium text-ink text-right min-w-0 break-words">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 text-[13px] text-muted">
          Proses berjalan di laptop ini, jadi biarkan laptop tetap menyala sampai video selesai.
        </p>
        <div className="mt-5 flex flex-col gap-2">
          {isNarasi && !form.narration_draft && (
            <p className="text-[13px] font-semibold text-stop-text">
              {!form.narration_path ? 'Pilih atau unggah rekaman narasi dulu.' : 'Transkrip & periksa narasi dulu.'}
            </p>
          )}
          {isBicara && !fromClips && talkClip && (talkClip.duration || 0) > LONG_TALK_SEC && (
            <p className={cx('text-[13px]', tooLongTalk ? 'font-semibold text-stop-text' : 'text-muted')}>
              {tooLongTalk
                ? `Video pembicara ${formatLength(talkClip.duration)}: terlalu panjang untuk satu Reel. Pakai "Cari cuplikan terbaik" di atas.`
                : `Video pembicara ${formatLength(talkClip.duration)}: satu Reel dari seluruh video butuh waktu lama. Lebih cepat lewat "Cari cuplikan terbaik".`}
            </p>
          )}
          {talkDraftPending && (
            <p className="text-[13px] font-semibold text-stop-text">Simpan transkrip dulu: klik "Transkrip sudah benar, pakai ini".</p>
          )}
          {isBicara && !form.talk_clip && (
            <p className="text-[13px] font-semibold text-stop-text">Pilih video pembicara dulu.</p>
          )}
          <Button
            variant="primary"
            size="lg"
            icon={Clapperboard}
            loading={submittingJob || creatingClips}
            onClick={fromClips ? () => createFromHighlights() : submitCreateJob}
            disabled={!fromClips && ((isNarasi && !form.narration_draft) || talkDraftPending || tooLongMontage
              || (isBicara && (!form.talk_clip || tooLongTalk)))}
          >
            {submittingJob || creatingClips ? 'Mengirim…' : fromClips ? `Buat ${highlightRanks.length} Reel` : 'Buat video'}
          </Button>
          <Button variant="ghost" icon={ArrowLeft} onClick={() => setWizardStep(1)}>
            Kembali ke footage
          </Button>
        </div>
      </aside>
    </div>
  );
}
