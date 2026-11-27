import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Save } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { formatDateTime } from '../../lib/format.js';
import { t } from '../../lib/i18n.js';
import { PageHeader, Section, Button } from '../../components/ui.jsx';

/**
 * Preferensi pemilik: dipelajari dari editan Anda atas hasil AI (hook, CTA, subtitle, caption, …),
 * dirangkum ke config/preferensi.md dan dibaca Director di setiap job berikutnya.
 */
const CONFIRM_OVERWRITE = 'Perubahan yang belum disimpan di bagian "Ringkasan otomatis" akan ditimpa. Lanjut?';

export default function PreferencesPage() {
  const { api, showToast } = useStudio();
  const [status, setStatus] = useState(null);
  const [text, setText] = useState('');
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(''); // '' | 'save' | 'summarize'

  const apply = useCallback((st) => {
    setStatus(st);
    setText(st?.text || '');
    setDirty(false);
  }, []);

  useEffect(() => {
    let alive = true;
    api('GET', '/api/config/preferences')
      .then((st) => alive && apply(st))
      .catch(() => alive && setStatus({ edited_jobs: 0, new_since_summary: 0, last_summarized: null, text: '' }));
    return () => {
      alive = false;
    };
    // api dibuat ulang tiap render; cukup dimuat sekali saat halaman dibuka
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const run = async (kind, method, path, body, okMsg) => {
    setBusy(kind);
    try {
      apply(await api(method, path, body));
      showToast(okMsg);
    } catch {
      /* pesan error sudah ditampilkan api() */
    } finally {
      setBusy('');
    }
  };

  const onSave = () => run('save', 'PUT', '/api/config/preferences', { text }, 'Preferensi disimpan');
  const onSummarize = () => {
    if (dirty && !window.confirm(t(CONFIRM_OVERWRITE))) return;
    run('summarize', 'POST', '/api/config/preferences/summarize', null, 'Preferensi dirangkum ulang');
  };

  const edited = status?.edited_jobs ?? 0;
  const fresh = status?.new_since_summary ?? 0;

  return (
    <div>
      <PageHeader
        title="Preferensi"
        description="AI belajar dari editan Anda: setiap kali Anda mengubah hook, CTA, subtitle, atau teks lalu render ulang, perubahannya dicatat. Rangkumannya dibaca AI saat membuat video berikutnya."
        actions={
          <>
            <Button
              variant="secondary"
              icon={RefreshCw}
              loading={busy === 'summarize'}
              disabled={!edited || !!busy}
              onClick={onSummarize}
            >
              Rangkum ulang
            </Button>
            <Button variant="primary" icon={Save} loading={busy === 'save'} disabled={!dirty || !!busy} onClick={onSave}>
              Simpan
            </Button>
          </>
        }
      >
        <p className="mt-3 text-sm text-muted" role="status">
          Video yang diedit: <span className="text-ink font-semibold">{edited}</span>
          {' · '}belum dirangkum: <span className={fresh ? 'text-stop-text font-semibold' : 'text-ink font-semibold'}>{fresh}</span>
          {' · '}rangkuman terakhir:{' '}
          <span className="text-ink font-semibold">
            {status?.last_summarized ? formatDateTime(status.last_summarized.replace(' ', 'T')) : 'belum pernah'}
          </span>
        </p>
      </PageHeader>

      <Section
        id="pref-text"
        title="Isi preferensi"
        description='Bagian "Ringkasan otomatis" ditulis AI (boleh diedit/dihapus). Tulis aturan Anda sendiri di bawah "Catatan manual" — bagian itu tidak pernah diubah AI.'
      >
        {!status ? (
          <p className="text-sm text-muted">Memuat…</p>
        ) : !text && !edited ? (
          <p className="text-sm text-muted">
            Belum ada editan yang tercatat. Edit hasil video (hook, CTA, subtitle, teks) lalu render ulang — setelah beberapa
            video, tekan "Rangkum ulang". Video yang dibuat sebelum fitur ini tidak ikut tercatat.
          </p>
        ) : (
          <textarea
            rows={16}
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setDirty(true);
            }}
            aria-label="Isi preferensi"
            placeholder={'## Catatan manual\n- Contoh: CTA selalu sebut "chat WhatsApp"'}
            className="field w-full resize-y font-mono text-[13px] leading-relaxed"
            translate="no"
          />
        )}
        {dirty && (
          <p className="mt-2 text-[13px] font-semibold text-stop-text" role="status">
            Belum disimpan
          </p>
        )}
      </Section>
    </div>
  );
}
