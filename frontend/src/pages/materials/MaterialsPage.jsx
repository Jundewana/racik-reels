import React from 'react';
import { ChevronRight } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { NAV_MATERIALS } from '../../lib/constants.js';
import { PageHeader } from '../../components/ui.jsx';

/** Daftar halaman "Bahan AI" untuk HP (di desktop sudah ada di rail kiri). */
export default function MaterialsPage() {
  const { navigateTo } = useStudio();
  return (
    <div>
      <PageHeader title="Bahan AI" description="Semua yang dibaca AI saat menyusun video dan menulis caption." />
      <ul className="border-t border-line">
        {NAV_MATERIALS.map(({ id, label, desc, Icon }) => (
          <li key={id} className="border-b border-line">
            <button type="button" onClick={() => navigateTo(id)} className="w-full flex items-center gap-4 py-4 text-left">
              <Icon className="w-5 h-5 text-brand shrink-0" aria-hidden="true" />
              <span className="flex-1 min-w-0">
                <span className="block font-display font-bold text-xl text-ink">{label}</span>
                <span className="block text-sm text-muted">{desc}</span>
              </span>
              <ChevronRight className="w-5 h-5 text-muted shrink-0" aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
