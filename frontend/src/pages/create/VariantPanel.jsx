import React, { useMemo, useState } from 'react';
import { ChevronDown, Copy } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { Button, cx } from '../../components/ui.jsx';

const DURATIONS = [15, 20, 30, 45];

/** Pilihan varian sesuai alur job (server: autoreels/server.py create_variants). */
function variantOptions(v) {
  const opts = [];
  if (v.flow === 'video') {
    for (const d of DURATIONS) {
      if (Math.abs(d - v.duration) > 2) opts.push({ key: `d${d}`, label: `${d} detik`, change: { duration: d } });
    }
  }
  if (v.flow === 'bicara') {
    opts.push(v.talk_full
      ? { key: 'ringkas', label: 'Versi ringkas 30–45 dtk', change: { talk_full: false } }
      : { key: 'utuh', label: 'Versi utuh (maks 3 mnt)', change: { talk_full: true } });
  }
  if (v.purpose !== 'informasi') {
    opts.push({ key: 'nocta', label: 'Tanpa CTA', change: { purpose: 'informasi' } });
  }
  return opts;
}

/** Buat beberapa Reel dari proyek yang sama tanpa mengulang analisis footage (hanya AI penyusun edit yang dipanggil). */
export default function VariantPanel({ job }) {
  const { createVariants } = useStudio();
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState([]);
  const [busy, setBusy] = useState(false);
  const options = useMemo(() => (job.variant?.available ? variantOptions(job.variant) : []), [job.variant]);
  if (options.length === 0) return null;

  const toggle = (key) => setPicked((p) => (p.includes(key) ? p.filter((k) => k !== key) : [...p, key]));
  const chosen = options.filter((o) => picked.includes(o.key));
  const submit = async () => {
    setBusy(true);
    try {
      await createVariants(job.job_id, chosen.map((o) => o.change), chosen.map((o) => o.label));
      setPicked([]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border-t border-line pt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="variant-panel"
        className="flex w-full items-center justify-between text-sm font-semibold text-ink"
      >
        <span className="flex items-center gap-2">
          <Copy className="w-4 h-4" aria-hidden="true" />
          Buat varian
        </span>
        <ChevronDown className={cx('w-4 h-4 transition-transform', open && 'rotate-180')} aria-hidden="true" />
      </button>
      {open && (
        <div id="variant-panel" className="mt-2 space-y-2.5">
          <p className="text-[13px] text-muted">
            Footage, gaya, dan teks yang sama. Analisis video tidak diulang, jadi lebih cepat dan murah.
          </p>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Pilihan varian">
            {options.map((o) => (
              <label
                key={o.key}
                className={cx(
                  'cursor-pointer rounded-md border px-3 py-1.5 text-[13px]',
                  picked.includes(o.key) ? 'border-brand bg-brand-soft text-ink font-semibold' : 'border-line text-muted'
                )}
              >
                <input type="checkbox" className="sr-only" checked={picked.includes(o.key)} onChange={() => toggle(o.key)} />
                {o.label}
              </label>
            ))}
          </div>
          <Button variant="secondary" size="sm" disabled={!chosen.length || busy} onClick={submit}>
            {chosen.length ? `Buat ${chosen.length} varian` : 'Pilih varian'}
          </Button>
        </div>
      )}
    </div>
  );
}
