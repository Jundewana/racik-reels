import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Plus, Wand2, Square, Image as ImageIcon, Film, Save, RefreshCw, ChevronDown, Search, FileText, Check, Download } from 'lucide-react';
import { useStudio } from '../state/studio.jsx';
import { formatDateTime } from '../lib/format.js';
import RuangKerja from '../components/RuangKerja.jsx';
import { PageHeader, Button, Field, Empty, StatusMark, Spinner, cx } from '../components/ui.jsx';

/**
 * Racik Animasi: video animasi penuh dari rekaman suara. Claude Code (headless, langganan, tanpa Gemini/Groq) menulis
 * kode animasi + musik + caption, Remotion merender. Gaya visual dipilih dari frame asli video itu sendiri.
 * Endpoint: /api/animasi… (autoreels/server_animasi.py).
 */
const PILLAR_LABEL = { rental: 'Rental motor', konstruksi: 'Konstruksi', profil: 'Profil', lowongan: 'Lowongan', umum: 'Umum' };
const STEP_LABEL = {
  siapkan: 'Menyiapkan suara',
  claude: 'Claude Code bekerja',
  frame: 'Merender frame',
  render: 'Merender video',
  pratinjau: 'Membuat pratinjau gaya'
};
const STATE_LABEL = { selesai: 'selesai', gagal: 'gagal', dihentikan: 'dihentikan', terhenti: 'terhenti' };
const slug = (s) =>
  s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40);

/* ---------------------------------------------------------------------------
 * Palet gaya (cadangan sebelum ada pratinjau frame)
 * ------------------------------------------------------------------------- */
function Palette({ colors, className }) {
  return (
    <span className={cx('flex h-full w-full', className)} aria-hidden="true">
      {colors.map((c, i) => (
        <span key={i} className={i === 0 ? 'flex-[2]' : 'flex-1'} style={{ background: c }} />
      ))}
    </span>
  );
}

/**
 * Pemilih gaya: deretan frame 9:16 video ini dalam tiap gaya (radiogroup). Tanpa pratinjau → palet warna gaya.
 */
function StylePicker({ styles, value, onChange, previews, disabled, compact = false }) {
  return (
    <div role="radiogroup" aria-label="Gaya animasi" className={cx('grid gap-3', compact ? 'grid-cols-5' : 'grid-cols-3 sm:grid-cols-5')}>
      {styles.map((g) => {
        const on = value === g.id;
        const img = previews?.[g.id];
        return (
          <button
            key={g.id}
            type="button"
            role="radio"
            aria-checked={on}
            disabled={disabled}
            title={g.deskripsi}
            onClick={() => onChange(g.id)}
            className={cx('group text-left rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:opacity-60', !disabled && 'cursor-pointer')}
          >
            <span
              className={cx(
                'relative block overflow-hidden rounded-lg bg-sunken transition-[box-shadow,transform]',
                compact ? 'aspect-square' : 'aspect-[9/16]',
                on ? 'ring-[3px] ring-brand ring-offset-2 ring-offset-paper' : 'ring-1 ring-line group-hover:ring-ink/40'
              )}
            >
              {img && !compact ? <img src={img} alt="" width={432} height={768} className="h-full w-full object-cover" loading="lazy" /> : <Palette colors={g.warna} />}
              {on && (
                <span className="absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-full bg-brand text-on-brand">
                  <Check className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
              )}
            </span>
            <span className={cx('mt-1.5 block text-[13px] leading-tight', on ? 'font-semibold text-ink' : 'text-muted')}>{g.nama}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Video baru
 * ------------------------------------------------------------------------- */
function NewForm({ sources, pillars, styles, onCreated, onCancel }) {
  const { uploadWithProgress, showToast } = useStudio();
  const [form, setForm] = useState({ nama: '', pilar: 'rental', brief: '', sumber: '', rentang: '', gaya: 'racik-flat', dimensi: '2d' });
  const [file, setFile] = useState(null);
  const [fileUrl, setFileUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [lanjut, setLanjut] = useState(false);
  const set = (p) => setForm((f) => ({ ...f, ...p }));
  const namaFinal = slug(form.nama);

  useEffect(() => {
    if (!file) {
      setFileUrl('');
      return undefined;
    }
    const url = URL.createObjectURL(file);
    setFileUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const previewSrc = fileUrl || (form.sumber ? `/media/footage/${form.sumber.split('/').map(encodeURIComponent).join('/')}` : '');

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    if (namaFinal.length < 2) return showToast('Isi nama video (huruf kecil, angka, tanda -).', 'error');
    if (!file && !form.sumber) return showToast('Unggah rekaman suara atau pilih file yang sudah ada.', 'error');
    setBusy(true);
    try {
      const fd = new FormData();
      Object.entries({ ...form, nama: namaFinal }).forEach(([k, v]) => fd.append(k, v));
      if (file) fd.append('file', file);
      await uploadWithProgress('/api/animasi', fd, () => {});
      showToast('Suara sedang disiapkan');
      onCreated(namaFinal);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="max-w-2xl">
      <h2 className="font-display text-3xl font-extrabold text-ink" style={{ textWrap: 'balance' }}>
        Video animasi baru
      </h2>
      <p className="mt-1 text-sm text-muted">Rekaman suara Anda jadi dasarnya: setiap teks dan gerak muncul tepat saat katanya diucapkan.</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Field label="Nama video" htmlFor="an-nama" hint={form.nama ? `Disimpan sebagai ${namaFinal || '-'}` : 'Contoh: promo-libur-akhir-tahun'}>
          <input id="an-nama" name="nama" className="field" value={form.nama} onChange={(e) => set({ nama: e.target.value })} autoComplete="off" spellCheck={false} placeholder="promo-sewa-motor…" />
        </Field>
        <Field label="Pilar" htmlFor="an-pilar">
          <select id="an-pilar" name="pilar" className="field" value={form.pilar} onChange={(e) => set({ pilar: e.target.value })}>
            {pillars.map((p) => (
              <option key={p} value={p}>
                {PILLAR_LABEL[p] || p}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <Field label="Tujuan video" htmlFor="an-brief" optional className="mt-4">
        <input id="an-brief" name="brief" autoComplete="off" className="field break-words" value={form.brief} onChange={(e) => set({ brief: e.target.value })} placeholder="Promo sewa motor untuk wisatawan libur akhir tahun…" />
      </Field>

      <fieldset className="mt-6">
        <legend className="text-sm font-semibold text-ink">Rekaman suara</legend>
        <div className="mt-2 grid gap-4 sm:grid-cols-2">
          <Field label="Unggah" htmlFor="an-file" hint="m4a, mp3, wav, atau video">
            <input id="an-file" name="file" type="file" accept="audio/*,video/*" className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-sunken file:px-3 file:py-2 file:text-ink" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </Field>
          <Field label="Atau pakai file yang ada" htmlFor="an-src">
            <select id="an-src" name="sumber" className="field" value={form.sumber} disabled={!!file} onChange={(e) => set({ sumber: e.target.value })}>
              <option value="">Pilih file…</option>
              {sources.map((s) => (
                <option key={s} value={s} translate="no">
                  {s}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {previewSrc && (
          <audio key={previewSrc} src={previewSrc} controls preload="metadata" className="mt-3 w-full h-9" />
        )}
      </fieldset>

      <fieldset className="mt-6">
        <legend className="text-sm font-semibold text-ink">Dunia animasi</legend>
        <div role="radiogroup" aria-label="Dunia animasi" className="mt-2 grid gap-3 sm:grid-cols-2">
          {[
            { id: '2d', nama: '2D flat', desk: 'Ilustrasi datar: cepat dirender, jalan di laptop mana pun.' },
            { id: '3d', nama: '3D', desk: 'Dunia 3D kartun dengan kamera bergerak. Render lebih lama, memakai kartu grafis.' }
          ].map((d) => (
            <button
              key={d.id}
              type="button"
              role="radio"
              aria-checked={form.dimensi === d.id}
              onClick={() => set({ dimensi: d.id })}
              className={cx(
                'rounded-lg border px-4 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                form.dimensi === d.id ? 'border-brand ring-1 ring-brand bg-brand-soft/60' : 'border-line bg-surface hover:border-ink/35'
              )}
            >
              <span className="block font-display text-lg font-extrabold text-ink">{d.nama}</span>
              <span className="mt-0.5 block text-[13px] text-muted">{d.desk}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="mt-6">
        <legend className="text-sm font-semibold text-ink">Gaya</legend>
        <p className="mt-0.5 text-[13px] text-muted">Bisa diganti kapan saja tanpa membuat ulang animasinya.</p>
        <div className="mt-3">
          <StylePicker styles={styles} value={form.gaya} onChange={(g) => set({ gaya: g })} compact />
        </div>
      </fieldset>

      <button type="button" className="mt-5 inline-flex items-center gap-1 text-[13px] font-semibold text-muted hover:text-ink" onClick={() => setLanjut((v) => !v)} aria-expanded={lanjut}>
        <ChevronDown className={cx('h-4 w-4 transition-transform', lanjut && 'rotate-180')} aria-hidden="true" />
        Ambil sebagian rekaman
      </button>
      {lanjut && (
        <Field label="Bagian rekaman (detik)" htmlFor="an-rentang" optional hint="Untuk rekaman panjang seperti podcast: 120-180, atau beberapa bagian 2615-2622,2518-2547 (urutan boleh diubah)." className="mt-3">
          <input id="an-rentang" name="rentang" inputMode="decimal" autoComplete="off" className="field num" value={form.rentang} onChange={(e) => set({ rentang: e.target.value })} placeholder="120-180…" />
        </Field>
      )}

      <div className="mt-6 flex flex-wrap gap-2">
        <Button type="submit" variant="primary" icon={Plus} disabled={busy}>
          {busy ? 'Mengunggah…' : 'Siapkan suara'}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          Batal
        </Button>
      </div>
    </form>
  );
}

/* ---------------------------------------------------------------------------
 * Editor transkrip
 * ------------------------------------------------------------------------- */
function TranscriptEditor({ video, onSaved, disabled }) {
  const { api, showToast } = useStudio();
  const [words, setWords] = useState(() => video.kata.map((k) => k.text));
  const [saving, setSaving] = useState(false);
  useEffect(() => setWords(video.kata.map((k) => k.text)), [video.nama, video.kata]);
  const changed = words.filter((w, i) => w !== video.kata[i]?.text).length;
  const save = async () => {
    setSaving(true);
    try {
      await api('PUT', `/api/animasi/${video.nama}/transkrip`, { kata: words });
      showToast('Transkrip disimpan');
      onSaved();
    } finally {
      setSaving(false);
    }
  };
  return (
    <div>
      <audio controls preload="none" src={`/api/animasi/${video.nama}/audio`} className="w-full" />
      <div className="mt-3 h-48 overflow-y-auto rounded-lg border border-line bg-surface p-2 scroll-thin" translate="no">
        <div className="flex flex-wrap gap-1">
          {words.map((w, i) => (
            <input
              key={i}
              aria-label={`Kata ke-${i + 1}, detik ${video.kata[i].start.toFixed(1)}`}
              title={`${video.kata[i].start.toFixed(2)} dtk`}
              value={w}
              disabled={disabled}
              spellCheck={false}
              onChange={(e) => setWords((ws) => ws.map((x, j) => (j === i ? e.target.value : x)))}
              size={Math.max(3, w.length)}
              className={cx(
                'rounded border bg-transparent px-1.5 py-0.5 text-[13px] text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                w !== video.kata[i].text ? 'border-hook bg-hook/15' : 'border-transparent hover:border-line'
              )}
            />
          ))}
        </div>
      </div>
      <div className="mt-2 flex items-center gap-3">
        <Button variant="secondary" size="sm" icon={Save} onClick={save} disabled={!changed || saving || disabled}>
          Simpan transkrip
        </Button>
        <span className="text-[13px] text-muted" aria-live="polite">
          {changed ? `${changed} kata diubah` : 'Klik kata yang salah dengar untuk membetulkannya. Waktunya tidak berubah.'}
        </span>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Langkah berurutan (rel vertikal)
 * ------------------------------------------------------------------------- */
function Step({ n, title, status, children, aside }) {
  return (
    <li className="relative pl-12 pb-10 last:pb-0">
      <span className="absolute left-[15px] top-9 bottom-0 w-px bg-line" aria-hidden="true" />
      <span
        className={cx(
          'absolute left-0 top-0 grid h-8 w-8 place-items-center rounded-full font-display text-base font-extrabold num',
          status === 'done' ? 'bg-go text-on-go' : status === 'active' ? 'bg-brand text-on-brand' : 'bg-sunken text-muted'
        )}
        aria-hidden="true"
      >
        {status === 'done' ? <Check className="h-4 w-4" /> : n}
      </span>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-xl font-extrabold text-ink">
          <span className="sr-only">{`Langkah ${n}: `}</span>
          {title}
        </h3>
        {aside}
      </div>
      <div className="mt-3">{children}</div>
    </li>
  );
}

function Detail({ nama, styles, onChanged }) {
  const { api, showToast } = useStudio();
  const [v, setV] = useState(null);
  const [instruksi, setInstruksi] = useState('');
  const [agen, setAgen] = useState('claude');
  const [showLog, setShowLog] = useState(false);
  const logRef = useRef(null);

  const load = async () => {
    const data = await api('GET', `/api/animasi/${nama}`);
    setV(data);
    return data;
  };

  useEffect(() => {
    setV(null);
    load()
      .then((d) => d?.agen && setAgen(d.agen))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nama]);

  const running = v?.state === 'berjalan';
  useEffect(() => {
    if (!running) return undefined;
    const id = setInterval(() => {
      load()
        .then((d) => d.state !== 'berjalan' && onChanged())
        .catch(() => {});
    }, 2000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, nama]);

  useEffect(() => {
    if (showLog && logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [showLog, v?.log?.length]);

  if (!v) {
    return (
      <div className="flex justify-center py-16">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  const act = async (path, body = {}) => {
    await api('POST', `/api/animasi/${nama}/${path}`, body);
    await load();
    onChanged();
  };
  const pickStyle = async (gaya) => {
    if (gaya === v.gaya) return;
    await api('PUT', `/api/animasi/${nama}/gaya`, { gaya });
    showToast(v.hasil ? 'Gaya diganti. Render ulang untuk menerapkannya.' : 'Gaya diganti');
    await load();
  };

  const siap = v.siap;
  const footage = v.mode === 'footage';
  const hasPreviews = v.pratinjau_gaya && Object.keys(v.pratinjau_gaya).length > 0;
  const styleNow = styles.find((g) => g.id === v.gaya);
  const previewImg = v.pratinjau_gaya?.[v.gaya];
  const resultStale = v.hasil && v.hasil_gaya && v.gaya !== v.hasil_gaya; // gaya diganti setelah render terakhir

  return (
    <div>
      {/* kepala */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line pb-5">
        <div className="min-w-0">
          <h2 className="font-display text-3xl font-extrabold text-ink truncate" translate="no">
            {v.nama}
          </h2>
          <p className="mt-1 text-sm text-muted">
            {PILLAR_LABEL[v.pilar] || v.pilar}
            {v.dimensi === '3d' ? ', 3D' : ''}
            {v.durasi ? `, ${Math.round(v.durasi)} detik` : ''}
            {footage ? ', footage + Remotion' : styleNow ? `, gaya ${styleNow.nama}` : ''}
          </p>
          {v.brief && (
            <p className="mt-1 max-w-prose break-words text-sm text-ink" translate="no">
              {v.brief}
            </p>
          )}
        </div>
        {v.state && (
          <span
            role="status"
            className={cx(
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[13px] font-semibold',
              running ? 'bg-brand-soft text-brand' : v.state === 'gagal' ? 'bg-stop/10 text-stop-text' : 'bg-sunken text-muted'
            )}
          >
            {running && <Spinner className="h-3.5 w-3.5" />}
            {running ? STEP_LABEL[v.langkah] || v.langkah : `${STEP_LABEL[v.langkah] || v.langkah} ${STATE_LABEL[v.state] || v.state}`}
          </span>
        )}
      </div>
      {(running || v.state === 'gagal') && v.detail && (
        <p className={cx('mt-3 text-[13px] line-clamp-2', v.state === 'gagal' ? 'text-stop-text' : 'text-muted')} translate="no">
          {v.detail}
        </p>
      )}

      <div className="mt-8 grid gap-10 lg:grid-cols-[17rem_minmax(0,1fr)] lg:gap-12">
        {/* ponsel: video jadi, atau pratinjau gaya */}
        <aside className="lg:sticky lg:top-8 self-start">
          <div className="mx-auto w-full max-w-[17rem] rounded-[2rem] bg-ink p-2.5 shadow-[0_24px_48px_-24px_rgb(var(--ink)/0.6)]">
            <div className="relative aspect-[9/16] overflow-hidden rounded-[1.5rem] bg-sunken">
              {v.hasil ? (
                <video key={v.hasil.url} src={v.hasil.url} controls playsInline className="h-full w-full object-cover" />
              ) : previewImg ? (
                <img src={previewImg} alt={`Pratinjau gaya ${styleNow?.nama || ''}`} width={432} height={768} className="h-full w-full object-cover" />
              ) : (
                <div className="grid h-full place-items-center p-6 text-center text-[13px] text-muted">
                  {siap ? 'Video muncul di sini setelah Claude Code merender.' : 'Menyiapkan suara…'}
                </div>
              )}
            </div>
          </div>
          {v.hasil && (
            <div className="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-[13px]">
              <StatusMark status={v.hasil.status} />
              <a href={v.hasil.url} download className="inline-flex items-center gap-1 font-semibold text-brand hover:underline">
                <Download className="h-3.5 w-3.5" aria-hidden="true" />
                Unduh MP4
              </a>
              <a href={v.hasil.report_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-muted hover:text-ink">
                <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                Laporan
              </a>
            </div>
          )}
          {resultStale && <p className="mt-2 text-center text-[12px] text-muted">Video ini masih gaya lama.</p>}
        </aside>

        {/* langkah */}
        <ol className="min-w-0">
          {footage ? (
            <Step n={1} title="Footage disiapkan" status={!siap ? 'active' : 'done'}>
              <p className="text-sm text-muted max-w-prose">
                {siap ? 'Klip dinormalisasi dan adegan dianalisis. Claude melihat lembar kontak adegan lalu memotong dan menyusunnya dengan Remotion.' : 'Menganalisis footage (adegan, kualitas, beat)…'}
              </p>
            </Step>
          ) : (
          <Step n={1} title="Periksa transkrip" status={!siap ? 'active' : 'done'}>
            {siap ? (
              <TranscriptEditor video={v} disabled={running} onSaved={load} />
            ) : (
              <p className="text-sm text-muted">Transkripsi berjalan di laptop, biasanya kurang dari semenit.</p>
            )}
          </Step>
          )}

          {!footage && (
          <Step
            n={2}
            title="Pilih gaya"
            status={siap ? 'done' : 'pending'}
            aside={
              v.punya_kode && (
                <Button variant="ghost" size="sm" icon={ImageIcon} onClick={() => act('pratinjau-gaya')} disabled={running}>
                  {hasPreviews ? 'Perbarui pratinjau' : 'Lihat video ini di semua gaya'}
                </Button>
              )
            }
          >
            <StylePicker styles={styles} value={v.gaya} onChange={(g) => pickStyle(g).catch(() => {})} previews={v.pratinjau_gaya} disabled={running || !siap} />
            {styleNow && <p className="mt-3 text-[13px] text-muted max-w-prose">{styleNow.deskripsi}</p>}
          </Step>
          )}

          <Step n={footage ? 2 : 3} title={v.punya_kode ? 'Revisi komposisi' : 'Buat komposisi Remotion'} status={!siap ? 'pending' : v.hasil ? 'done' : 'active'}>
            <p className="text-sm text-muted max-w-prose">
              {footage ? 'Agen memilih potongan terbaik dari footage Anda, menulis komposisi Remotion (potongan, transisi, teks, musik) dan caption, memeriksa frame, lalu merender.' : 'Agen menyusun adegan, menulis kode animasi, musik orisinal, dan caption, memeriksa frame, lalu merender.'}
            </p>
            <div role="radiogroup" aria-label="Pilih agen penyusun" className="mt-4 inline-flex rounded-lg border border-line bg-sunken p-1 gap-1">
              {[
                { id: 'claude', label: 'Claude Code' },
                { id: 'antigravity', label: 'Antigravity (Cadangan)' }
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  role="radio"
                  aria-checked={agen === opt.id}
                  disabled={running}
                  onClick={() => setAgen(opt.id)}
                  className={cx(
                    'rounded-md px-3 py-1.5 text-[13px] font-semibold transition-colors',
                    agen === opt.id ? 'bg-surface text-ink shadow-sm' : 'text-muted hover:text-ink'
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <Field label={v.punya_kode ? 'Apa yang perlu diubah?' : 'Arahan untuk penyusun'} htmlFor="an-instruksi" optional className="mt-4">
              <textarea
                id="an-instruksi"
                name="instruksi"
                autoComplete="off"
                rows={3}
                className="field"
                value={instruksi}
                onChange={(e) => setInstruksi(e.target.value)}
                placeholder={v.punya_kode ? 'Hook lebih besar, adegan 3 pakai peta, musik lebih santai…' : 'Tonjolkan bonus helm & jas hujan, suasana ceria…'}
              />
            </Field>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Button variant="primary" icon={Wand2} onClick={() => act('claude', { instruksi, agen })} disabled={!siap || running}>
                {v.punya_kode
                  ? (agen === 'antigravity' ? 'Revisi dengan Antigravity' : 'Revisi dengan Claude Code')
                  : (agen === 'antigravity' ? 'Buat dengan Antigravity' : 'Buat dengan Claude Code')}
              </Button>
              {running && v.langkah === 'claude' && (
                <Button variant="danger" icon={Square} onClick={() => act('stop')}>
                  Hentikan
                </Button>
              )}
              {v.punya_kode && !running && (
                <>
                  <Button variant="ghost" size="sm" icon={Film} onClick={() => act('render')} disabled={!v.punya_caption}>
                    Render ulang dengan gaya ini
                  </Button>
                  <Button variant="ghost" size="sm" icon={ImageIcon} onClick={() => act('stills')}>
                    Render frame
                  </Button>
                </>
              )}
            </div>
            <p className="mt-2 text-[12px] text-muted">Biasanya 5 sampai 15 menit. Halaman boleh ditutup; prosesnya tetap berjalan di laptop.</p>

            {(running || v.punya_kode) && (
              <div className="mt-6">
                <p className="mb-2 font-display text-lg font-bold text-ink">Ruang Kerja</p>
                <RuangKerja nama={nama} agen={agen} running={running && v.langkah === 'claude'} lembarUrl={v.lembar_url} punyaKode={v.punya_kode} />
              </div>
            )}

            {v.log?.length > 0 && (
              <div className="mt-5">
                <button type="button" className="inline-flex items-center gap-1 text-[13px] font-semibold text-muted hover:text-ink" onClick={() => setShowLog((s) => !s)} aria-expanded={showLog}>
                  <ChevronDown className={cx('h-4 w-4 transition-transform', showLog && 'rotate-180')} aria-hidden="true" />
                  Catatan proses
                </button>
                {showLog && (
                  <pre ref={logRef} className="mt-2 h-56 overflow-y-auto whitespace-pre-wrap rounded-md bg-sunken p-3 text-[12px] leading-relaxed text-ink scroll-thin" translate="no">
                    {v.log.join('\n')}
                  </pre>
                )}
              </div>
            )}
          </Step>

          {(v.hasil?.caption || v.lembar_url) && (
            <li className="pl-12 pt-2 space-y-6">
              {v.hasil?.caption && (
                <Field label="Caption Instagram" htmlFor="an-caption">
                  <textarea id="an-caption" readOnly rows={6} className="field text-[13px]" value={v.hasil.caption} translate="no" />
                </Field>
              )}
              {v.lembar_url && (
                <figure>
                  <img src={v.lembar_url} alt="Frame diam tiap kalimat" width={1080} height={2400} className="h-auto w-full rounded-lg border border-line" loading="lazy" />
                  <figcaption className="mt-1 text-[12px] text-muted">Frame diam di tengah tiap kalimat</figcaption>
                </figure>
              )}
            </li>
          )}
        </ol>
      </div>
    </div>
  );
}

const videoFromUrl = () => new URLSearchParams(window.location.search).get('video');

export default function AnimasiPage() {
  const { api } = useStudio();
  const [list, setList] = useState({ videos: [], sources: [], pillars: [], styles: [] });
  const [selected, setSelected] = useState(videoFromUrl);
  const [creating, setCreating] = useState(false);
  const [q, setQ] = useState('');
  const [loaded, setLoaded] = useState(false);

  const reload = async () => {
    const data = await api('GET', '/api/animasi');
    setList(data);
    setLoaded(true);
    setSelected((cur) => cur || data.videos[0]?.nama || null);
    if (!data.videos.length) setCreating(true);
  };

  useEffect(() => {
    reload().catch(() => setLoaded(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (selected) url.searchParams.set('video', selected);
    else url.searchParams.delete('video');
    window.history.replaceState(window.history.state, '', url);
  }, [selected]);

  const shown = useMemo(() => list.videos.filter((x) => !q || `${x.nama} ${x.brief}`.toLowerCase().includes(q.toLowerCase())), [list.videos, q]);

  return (
    <div>
      <PageHeader
        title="Animasi"
        description="Reel animasi penuh dari rekaman suara Anda, dibuat oleh Claude Code dan dirender di laptop."
        actions={
          <>
            <Button variant="ghost" size="sm" icon={RefreshCw} onClick={() => reload().catch(() => {})}>
              Muat ulang
            </Button>
            <Button variant="primary" size="sm" icon={Plus} onClick={() => setCreating(true)}>
              Video animasi baru
            </Button>
          </>
        }
      />
      <div className="grid grid-cols-1 items-start gap-8 xl:grid-cols-[15rem_minmax(0,1fr)] xl:gap-10">
        <nav aria-label="Video animasi" className="min-w-0">
          {list.videos.length > 8 && (
            <label className="relative mb-2 block">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
              <input className="field pl-8" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari video…" aria-label="Cari video animasi" name="cari" autoComplete="off" />
            </label>
          )}
          {loaded && list.videos.length === 0 ? (
            <Empty title="Belum ada animasi">Mulai dari rekaman suara Anda.</Empty>
          ) : (
            <ul className="max-h-[30rem] space-y-1 overflow-y-auto pr-1 scroll-thin">
              {shown.map((x) => {
                const on = selected === x.nama && !creating;
                return (
                  <li key={x.nama}>
                    <button
                      type="button"
                      onClick={() => {
                        setCreating(false);
                        setSelected(x.nama);
                      }}
                      aria-current={on ? 'true' : undefined}
                      className={cx(
                        'w-full rounded-md border-l-[3px] px-3 py-2.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand',
                        on ? 'border-brand bg-brand-soft/60' : 'border-transparent hover:bg-sunken'
                      )}
                    >
                      <span className="flex items-center justify-between gap-2">
                        <span className={cx('truncate text-sm', on ? 'font-semibold text-ink' : 'text-ink')} translate="no">
                          {x.nama}
                        </span>
                        {x.state === 'berjalan' ? <Spinner className="h-3.5 w-3.5 shrink-0" /> : x.hasil && <StatusMark status={x.hasil.status} className="shrink-0 [&>span:last-child]:sr-only" />}
                      </span>
                      <span className="mt-0.5 block truncate text-[12px] text-muted">
                        {`${PILLAR_LABEL[x.pilar] || x.pilar}, ${formatDateTime(new Date(x.diubah * 1000).toISOString())}`}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </nav>
        <div className="min-w-0">
          {creating ? (
            <NewForm
              sources={list.sources}
              pillars={list.pillars.length ? list.pillars : Object.keys(PILLAR_LABEL)}
              styles={list.styles}
              onCancel={() => setCreating(false)}
              onCreated={(nama) => {
                setCreating(false);
                setSelected(nama);
                setTimeout(() => reload().catch(() => {}), 800);
              }}
            />
          ) : selected ? (
            <Detail key={selected} nama={selected} styles={list.styles} onChanged={() => reload().catch(() => {})} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
