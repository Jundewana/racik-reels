import React, { useState } from 'react';
import { Trash2, X } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { TREND_SECTIONS } from '../../lib/constants.js';
import { formatDateTime } from '../../lib/format.js';
import { PageHeader, Section, Button, Dialog } from '../../components/ui.jsx';
import { SaveActions, AddRow } from './common.jsx';

export default function TrendsPage() {
  const { trendsConfig, addTrendItem, removeTrendItem, clearAllTrends, saveTrendsConfig } = useStudio();
  const [inputs, setInputs] = useState({});
  const [confirmClear, setConfirmClear] = useState(false);
  const totalItems = TREND_SECTIONS.reduce((n, s) => n + (trendsConfig[s.key] || []).length, 0);

  return (
    <div>
      <PageHeader
        title="Brief tren"
        description="Isi tiap minggu dari pengamatan Anda sendiri. AI hanya memakai tren yang tertulis di sini dan tidak mengarang tren lain. Bila kosong, tren diabaikan."
        actions={
          <>
            <Button variant="danger" icon={Trash2} onClick={() => setConfirmClear(true)} disabled={!totalItems}>
              Kosongkan
            </Button>
            <SaveActions onSave={saveTrendsConfig} label="Simpan brief" />
          </>
        }
      >
        <p className="mt-3 text-sm text-muted">
          Terakhir diperbarui: <span className="text-ink font-semibold">{trendsConfig.updated ? formatDateTime(trendsConfig.updated).split(',')[0] : 'belum pernah'}</span>
        </p>
      </PageHeader>

      {TREND_SECTIONS.map((sec) => {
        const items = trendsConfig[sec.key] || [];
        return (
          <Section key={sec.key} id={`trend-${sec.key}`} title={sec.label} description={`${items.length} poin`}>
            <AddRow
              value={inputs[sec.key] || ''}
              onChange={(v) => setInputs((p) => ({ ...p, [sec.key]: v }))}
              onAdd={() => {
                if (addTrendItem(sec.key, inputs[sec.key])) setInputs((p) => ({ ...p, [sec.key]: '' }));
              }}
              label={`Tambah: ${sec.label}`}
              placeholder={sec.placeholder}
            />
            {items.length > 0 && (
              <ul className="mt-3 border-t border-line">
                {items.map((point, idx) => (
                  <li key={`${idx}-${point}`} className="flex items-start justify-between gap-3 border-b border-line py-2.5 text-sm">
                    <span className="text-ink min-w-0 break-words" translate="no">{point}</span>
                    <button
                      type="button"
                      onClick={() => removeTrendItem(sec.key, idx)}
                      aria-label={`Hapus "${point}"`}
                      className="shrink-0 w-7 h-7 -my-0.5 rounded-md flex items-center justify-center text-muted hover:text-stop-text hover:bg-stop/10"
                    >
                      <X className="w-4 h-4" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        );
      })}

      <Dialog
        open={confirmClear}
        onClose={() => setConfirmClear(false)}
        title="Kosongkan semua tren?"
        actions={
          <>
            <Button variant="ghost" onClick={() => setConfirmClear(false)} data-autofocus>
              Batal
            </Button>
            <Button
              variant="danger-solid"
              onClick={() => {
                clearAllTrends();
                setConfirmClear(false);
              }}
            >
              Kosongkan {totalItems} poin
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted">
          Semua poin di kelima bagian dihapus. Setelah Anda menyimpan, AI berhenti memakai konteks tren sampai brief diisi lagi.
        </p>
      </Dialog>
    </div>
  );
}
