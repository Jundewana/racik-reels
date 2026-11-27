import React from 'react';
import { Save, X } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { Button, Segmented } from '../../components/ui.jsx';

/** Tombol simpan + penanda perubahan belum disimpan */
export function SaveActions({ onSave, label = 'Simpan', dirtyAware = true }) {
  const { savingConfig, hasUnsavedConfig } = useStudio();
  return (
    <div className="flex items-center gap-3">
      {dirtyAware && hasUnsavedConfig && (
        <span className="text-[13px] font-semibold text-stop-text" role="status">
          Belum disimpan
        </span>
      )}
      <Button variant="primary" icon={Save} loading={savingConfig} onClick={onSave}>
        {label}
      </Button>
    </div>
  );
}

export function PillarSwitch({ value, onChange }) {
  const { options } = useStudio();
  return (
    <Segmented
      label="Pilar konten"
      value={value}
      onChange={onChange}
      options={options.pillars.map((p) => ({ id: p.id, label: p.label }))}
    />
  );
}

/** Chip yang bisa dihapus (hashtag, keyword) */
export function Chip({ children, onRemove, removeLabel }) {
  return (
    <li className="inline-flex items-center gap-1 rounded-full border border-line bg-surface pl-3 pr-1 h-8 text-sm text-ink">
      <span className="truncate max-w-[16rem]">{children}</span>
      <button
        type="button"
        onClick={onRemove}
        aria-label={removeLabel}
        className="w-6 h-6 rounded-full flex items-center justify-center text-muted hover:text-stop-text hover:bg-stop/10"
      >
        <X className="w-3.5 h-3.5" aria-hidden="true" />
      </button>
    </li>
  );
}

/** Isian + tombol Tambah (Enter juga menambah) */
export function AddRow({ id, value, onChange, onAdd, placeholder, label, buttonLabel = 'Tambah', splitOnComma = false }) {
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        onAdd();
      }}
    >
      <input
        id={id}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (splitOnComma && e.key === ',') {
            e.preventDefault();
            onAdd();
          }
        }}
        placeholder={placeholder}
        aria-label={label}
        autoComplete="off"
        className="field flex-1 min-w-0"
      />
      <Button type="submit" variant="secondary" disabled={!value.trim()}>
        {buttonLabel}
      </Button>
    </form>
  );
}
