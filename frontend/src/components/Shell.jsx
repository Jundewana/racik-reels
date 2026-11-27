import React, { useEffect, useState } from 'react';
import { Sun, Moon, Loader2, ChevronDown } from 'lucide-react';
import { getLang, setLang, onLangChange } from '../lib/i18n.js';
import { useStudio } from '../state/studio.jsx';
import { APP_NAME, NAV_PRODUCTION, NAV_MATERIALS, NAV_MOBILE, MATERIAL_PAGE_IDS } from '../lib/constants.js';
import { cx, IconButton } from './ui.jsx';

/** Tanda aplikasi: tiga blok bertumpuk = struktur video (hook kuning, isi ungu, CTA hijau). */
export function ReelGlyph({ className }) {
  return (
    <svg viewBox="0 0 14 24" className={className} aria-hidden="true">
      <rect x="0" y="0" width="14" height="5" rx="1.5" fill="rgb(var(--hook))" />
      <rect x="0" y="6.5" width="14" height="10" rx="1.5" fill="rgb(var(--brand))" />
      <rect x="0" y="18" width="14" height="6" rx="1.5" fill="rgb(var(--go))" />
    </svg>
  );
}

/** [tanda Racik] Racik — Contoh Brand (logo Brand dipakai sebagai favicon di tab) */
function Wordmark({ compact = false }) {
  return (
    <span className="flex items-center gap-2.5 min-w-0">
      <ReelGlyph className={compact ? 'h-6 w-auto shrink-0' : 'h-8 w-auto shrink-0'} />
      <span className="min-w-0">
        <span className={cx('block font-display font-extrabold leading-none text-ink', compact ? 'text-2xl' : 'text-[1.75rem]')}>
          {APP_NAME}
        </span>
        <span className={cx('block text-muted truncate', compact ? 'text-[11px] mt-0.5' : 'text-xs mt-1')}>
          Contoh Brand
        </span>
      </span>
    </span>
  );
}

/** Job yang sedang berjalan: terlihat dari halaman mana pun, klik untuk kembali ke layar Proses. */
function ActiveJobIndicator({ compact = false }) {
  const { activeJob, viewingProcess, goToProcess } = useStudio();
  if (!activeJob || viewingProcess) return null;
  if (compact) {
    return (
      <button
        type="button"
        onClick={goToProcess}
        aria-label={`Video sedang dibuat, ${activeJob.percent}%. Lihat proses`}
        className="inline-flex items-center gap-1.5 h-8 rounded-full bg-brand text-on-brand px-3 text-[13px] font-semibold num"
      >
        <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
        {activeJob.indeterminate ? 'Claude' : `${activeJob.percent}%`}
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={goToProcess}
      className="w-full text-left rounded-md bg-surface border border-line px-3 py-2.5 hover:border-brand/60 transition-colors"
    >
      <span className="flex items-center justify-between gap-2 text-[13px]">
        <span className="flex items-center gap-1.5 font-semibold text-ink">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-brand" aria-hidden="true" />
          Membuat video
        </span>
        <span className="font-display font-bold text-base text-ink num">{activeJob.indeterminate ? '…' : `${activeJob.percent}%`}</span>
      </span>
      <span className="mt-1 block text-[12px] text-muted truncate">{activeJob.label}</span>
      <span className="mt-2 block h-1 rounded-full bg-sunken overflow-hidden" aria-hidden="true">
        <span className={cx('block h-full bg-brand transition-[width] duration-500', activeJob.indeterminate && 'animate-pulse')} style={{ width: activeJob.indeterminate ? '100%' : `${activeJob.percent}%` }} />
      </span>
    </button>
  );
}

function RailLink({ item, active, onClick }) {
  const { Icon } = item;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={cx(
        'group relative w-full flex items-center gap-3 rounded-md pl-4 pr-3 h-10 text-sm text-left transition-colors',
        active ? 'bg-surface text-ink font-semibold' : 'text-muted hover:text-ink hover:bg-sunken/70'
      )}
    >
      <span
        aria-hidden="true"
        className={cx('absolute left-0 top-2 bottom-2 w-[3px] rounded-full', active ? 'bg-brand' : 'bg-transparent')}
      />
      <Icon className={cx('w-4 h-4 shrink-0', active ? 'text-brand' : '')} aria-hidden="true" />
      <span className="truncate">{item.label}</span>
    </button>
  );
}

/** Pilihan bahasa antarmuka: ID (bawaan) / EN. Label tidak ikut diterjemahkan. */
function LangToggle() {
  const [lang, setLocal] = useState(getLang);
  useEffect(() => onLangChange(setLocal), []);
  return (
    <div role="group" aria-label="Bahasa antarmuka" translate="no" className="inline-flex rounded-md border border-line p-0.5 text-xs font-semibold">
      {['id', 'en'].map((code) => (
        <button
          key={code}
          type="button"
          onClick={() => setLang(code)}
          aria-pressed={lang === code}
          lang={code}
          title={code === 'id' ? 'Bahasa Indonesia' : 'English'}
          className={cx('rounded px-2 py-1 uppercase', lang === code ? 'bg-ink text-paper' : 'text-muted hover:text-ink')}
        >
          {code}
        </button>
      ))}
    </div>
  );
}

function ThemeToggle({ compact }) {
  const { darkMode, setDarkMode } = useStudio();
  if (compact) {
    return (
      <IconButton
        label={darkMode ? 'Pakai tema terang' : 'Pakai tema gelap'}
        icon={darkMode ? Sun : Moon}
        onClick={() => setDarkMode((d) => !d)}
      />
    );
  }
  return (
    <button
      type="button"
      onClick={() => setDarkMode((d) => !d)}
      className="w-full flex items-center gap-3 rounded-md px-4 h-10 text-sm text-muted hover:text-ink hover:bg-sunken/70 transition-colors"
    >
      {darkMode ? <Sun className="w-4 h-4" aria-hidden="true" /> : <Moon className="w-4 h-4" aria-hidden="true" />}
      {darkMode ? 'Tema terang' : 'Tema gelap'}
    </button>
  );
}

/** Rail kiri (desktop ≥ lg) */
export function Rail() {
  const { currentPage, navigateTo, useMock, trendsConfig } = useStudio();
  const onMaterial = MATERIAL_PAGE_IDS.includes(currentPage);
  const [materialsOpen, setMaterialsOpen] = useState(onMaterial);
  useEffect(() => {
    if (onMaterial) setMaterialsOpen(true); // sedang di salah satu halaman bahan → grup terbuka
  }, [onMaterial]);
  const trendAge = trendsConfig?.updated ? Math.floor((Date.now() - Date.parse(trendsConfig.updated)) / 86400000) : null;
  const trendStale = trendAge === null || trendAge > 7; // Director membaca brief tren: ingatkan bila > 7 hari
  return (
    <aside className="hidden lg:flex fixed inset-y-0 left-0 w-60 flex-col border-r border-line bg-paper z-30">
      <div className="px-5 pt-6 pb-8">
        <Wordmark />
      </div>
      <div className="px-3 -mt-3 mb-5 empty:hidden">
        <ActiveJobIndicator />
      </div>
      <nav aria-label="Navigasi utama" className="flex-1 overflow-y-auto px-3 space-y-8">
        <div className="space-y-0.5">
          {NAV_PRODUCTION.map((item) => (
            <RailLink key={item.id} item={item} active={currentPage === item.id} onClick={() => navigateTo(item.id)} />
          ))}
        </div>
        <div>
          <button
            type="button"
            onClick={() => setMaterialsOpen((v) => !v)}
            aria-expanded={materialsOpen}
            aria-controls="nav-materials"
            className="flex w-full items-center justify-between rounded-md px-4 py-1.5 text-[13px] font-semibold text-muted hover:text-ink"
          >
            <span className="flex items-center gap-2">
              Bahan untuk AI
              {trendStale && !materialsOpen && (
                <span className="h-2 w-2 rounded-full bg-brand" aria-label="Brief tren perlu diperbarui" />
              )}
            </span>
            <ChevronDown className={cx('w-4 h-4 transition-transform', materialsOpen && 'rotate-180')} aria-hidden="true" />
          </button>
          {materialsOpen && (
            <div id="nav-materials" className="mt-1 space-y-0.5">
              {NAV_MATERIALS.map((item) => (
                <RailLink
                  key={item.id}
                  item={item.id === 'trends' && trendStale ? { ...item, label: `${item.label} (perlu diperbarui)` } : item}
                  active={currentPage === item.id}
                  onClick={() => navigateTo(item.id)}
                />
              ))}
            </div>
          )}
        </div>
      </nav>
      <div className="px-3 pb-5 pt-3 space-y-2">
        {useMock && (
          <p className="mx-1 rounded-md bg-brand-soft px-3 py-2 text-[13px] text-ink">
            Mode simulasi: data contoh, tidak terhubung ke laptop.
          </p>
        )}
        <div className="flex items-center gap-2">
          <div className="flex-1"><ThemeToggle /></div>
          <LangToggle />
        </div>
      </div>
    </aside>
  );
}

/** Header atas (HP & tablet) */
export function MobileHeader() {
  const { useMock } = useStudio();
  return (
    <header
      className="lg:hidden sticky top-0 z-30 bg-paper/95 backdrop-blur border-b border-line"
      style={{ paddingTop: 'env(safe-area-inset-top)' }}
    >
      <div className="flex items-center justify-between gap-3 px-4 h-14">
        <Wordmark compact />
        <div className="flex items-center gap-1.5">
          <ActiveJobIndicator compact />
          {useMock && <span className="text-xs font-semibold text-muted">Simulasi</span>}
          <LangToggle />
          <ThemeToggle compact />
        </div>
      </div>
    </header>
  );
}

/** Menu bawah (HP & tablet): 4 item agar tidak terpotong di layar 360 px */
export function BottomNav() {
  const { currentPage, navigateTo, isMaterialPage } = useStudio();
  return (
    <nav
      aria-label="Navigasi utama"
      className="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-surface/95 backdrop-blur border-t border-line"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="grid grid-cols-3 h-16">
        {NAV_MOBILE.map(({ id, short, Icon }) => {
          const active = currentPage === id || (id === 'materials' && isMaterialPage);
          return (
            <button
              key={id}
              type="button"
              onClick={() => navigateTo(id)}
              aria-current={active ? 'page' : undefined}
              className={cx(
                'relative flex flex-col items-center justify-center gap-1 text-[12px] transition-colors',
                active ? 'text-brand font-semibold' : 'text-muted'
              )}
            >
              <span
                aria-hidden="true"
                className={cx('absolute top-0 inset-x-6 h-[3px] rounded-b-full', active ? 'bg-brand' : 'bg-transparent')}
              />
              <Icon className="w-5 h-5" aria-hidden="true" />
              {short}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
