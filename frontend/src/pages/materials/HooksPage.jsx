import React, { useState } from 'react';
import { Pencil, Trash2, Plus } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { HOOK_TYPES, hookTypeLabel } from '../../lib/constants.js';
import { PageHeader, Section, Button, IconButton, Field, HookCounter, Dialog, Empty, cx } from '../../components/ui.jsx';
import { SaveActions, PillarSwitch } from './common.jsx';

function TypeSelect({ id, value, onChange, label = 'Tipe hook' }) {
  return (
    <select id={id} aria-label={label} value={value} onChange={(e) => onChange(e.target.value)} className="field sm:w-48">
      {HOOK_TYPES.map((t) => (
        <option key={t.id} value={t.id}>
          {t.label}
        </option>
      ))}
    </select>
  );
}

export default function HooksPage() {
  const {
    hooksConfig,
    activeConfigPillar,
    setActiveConfigPillar,
    addHookItem,
    updateHookItem,
    deleteHookItem,
    saveHooksConfig,
    hookStats,
    getPillarLabel
  } = useStudio();
  const [draft, setDraft] = useState({ text: '', type: 'pertanyaan' });
  const [editing, setEditing] = useState(null); // { idx, text, type }
  const [confirmIdx, setConfirmIdx] = useState(null);
  const list = hooksConfig[activeConfigPillar] || [];
  const ds = hookStats(draft.text);

  const add = () => {
    const text = draft.text.trim();
    if (!text) return;
    addHookItem({ type: draft.type, text });
    setDraft((p) => ({ ...p, text: '' }));
  };

  return (
    <div>
      <PageHeader
        title="Pustaka hook"
        description="Kalimat pembuka yang tampil besar di 3 detik pertama. AI memilih atau mengadaptasi dari daftar ini, dan Anda bisa memakainya langsung saat membuat video."
        actions={<SaveActions onSave={saveHooksConfig} label="Simpan pustaka" />}
      />

      <div className="mb-6">
        <PillarSwitch
          value={activeConfigPillar}
          onChange={(id) => {
            setActiveConfigPillar(id);
            setEditing(null);
          }}
        />
      </div>

      <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,1fr)_17rem] xl:gap-12 items-start">
        <div className="min-w-0">
          <Section id="hook-add" layout="stack" title={`Tambah hook ${getPillarLabel(activeConfigPillar)}`}>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                add();
              }}
              className="space-y-2"
            >
              <Field
                label="Teks hook"
                htmlFor="new-hook-text"
                aside={<HookCounter stats={ds} id="new-hook-count" />}
                error={ds.over ? 'Terlalu panjang: di video akan tampil kecil.' : null}
              >
                <div className="flex flex-col sm:flex-row gap-2">
                  <input
                    id="new-hook-text"
                    type="text"
                    value={draft.text}
                    onChange={(e) => setDraft((p) => ({ ...p, text: e.target.value }))}
                    placeholder="Mis. Liburan ke Garut?"
                    aria-describedby="new-hook-count"
                    autoComplete="off"
                    className={cx('field flex-1 min-w-0', ds.over && 'field-invalid')}
                  />
                  <TypeSelect value={draft.type} onChange={(type) => setDraft((p) => ({ ...p, type }))} />
                  <Button type="submit" variant="brand" icon={Plus} disabled={!draft.text.trim()}>
                    Tambah
                  </Button>
                </div>
              </Field>
            </form>
          </Section>

          <Section id="hook-list" layout="stack" title={`${list.length} hook tersimpan`}>
            {list.length === 0 ? (
              <Empty title="Belum ada hook untuk pilar ini">Tambahkan minimal 3 hook agar AI punya pilihan.</Empty>
            ) : (
              <ul className="border-t border-line">
                {list.map((item, idx) => {
                  const isEditing = editing?.idx === idx;
                  const es = isEditing ? hookStats(editing.text) : null;
                  return (
                    <li key={`${idx}-${item.text}`} className="border-b border-line py-4">
                      {!isEditing ? (
                        <div className="flex items-start gap-4">
                          <span className="mt-2 w-1 self-stretch rounded-full bg-hook shrink-0" aria-hidden="true" />
                          <div className="flex-1 min-w-0">
                            <p className="font-display font-bold text-2xl leading-tight text-ink break-words" translate="no">{item.text}</p>
                            <p className="mt-0.5 text-[13px] text-muted">{hookTypeLabel(item.type)}</p>
                          </div>
                          <div className="flex shrink-0">
                            <IconButton
                              label={`Ubah hook "${item.text}"`}
                              icon={Pencil}
                              onClick={() => setEditing({ idx, text: item.text, type: item.type })}
                            />
                            <IconButton
                              label={`Hapus hook "${item.text}"`}
                              icon={Trash2}
                              onClick={() => setConfirmIdx(idx)}
                              className="hover:text-stop-text"
                            />
                          </div>
                        </div>
                      ) : (
                        <form
                          className="space-y-2"
                          onSubmit={(e) => {
                            e.preventDefault();
                            const text = editing.text.trim();
                            if (!text) return;
                            updateHookItem(idx, { text, type: editing.type });
                            setEditing(null);
                          }}
                        >
                          <div className="flex flex-col sm:flex-row gap-2">
                            <input
                              type="text"
                              value={editing.text}
                              onChange={(e) => setEditing((p) => ({ ...p, text: e.target.value }))}
                              aria-label="Teks hook"
                              autoComplete="off"
                              className={cx('field flex-1 min-w-0', es.over && 'field-invalid')}
                              autoFocus
                            />
                            <TypeSelect value={editing.type} onChange={(type) => setEditing((p) => ({ ...p, type }))} />
                          </div>
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <HookCounter stats={es} />
                            <div className="flex gap-2">
                              <Button variant="ghost" size="sm" onClick={() => setEditing(null)}>
                                Batal
                              </Button>
                              <Button type="submit" variant="brand" size="sm" disabled={!editing.text.trim()}>
                                Terapkan
                              </Button>
                            </div>
                          </div>
                        </form>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </Section>
        </div>

        <aside aria-labelledby="hook-types-title" className="border-t border-line pt-6">
          <h2 id="hook-types-title" className="font-display font-bold text-xl text-ink">
            Tipe hook
          </h2>
          <dl className="mt-3 space-y-3 text-sm">
            {HOOK_TYPES.map((t) => (
              <div key={t.id}>
                <dt className="font-semibold text-ink">{t.label}</dt>
                <dd className="text-muted">{t.desc}</dd>
              </div>
            ))}
          </dl>
        </aside>
      </div>

      <Dialog
        open={confirmIdx !== null}
        onClose={() => setConfirmIdx(null)}
        title="Hapus hook ini?"
        actions={
          <>
            <Button variant="ghost" onClick={() => setConfirmIdx(null)} data-autofocus>
              Batal
            </Button>
            <Button
              variant="danger-solid"
              icon={Trash2}
              onClick={() => {
                deleteHookItem(confirmIdx);
                setConfirmIdx(null);
              }}
            >
              Hapus hook
            </Button>
          </>
        }
      >
        <p className="text-ink font-display font-bold text-xl">{list[confirmIdx]?.text}</p>
        <p className="mt-2 text-sm text-muted">Hook hilang dari pustaka setelah Anda menekan Simpan pustaka.</p>
      </Dialog>
    </div>
  );
}
