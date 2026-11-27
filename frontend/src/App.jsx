import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { StudioProvider, useStudio } from './state/studio.jsx';
import { renderSimpleMarkdown } from './lib/format.js';
import { Rail, MobileHeader, BottomNav } from './components/Shell.jsx';
import { Dialog, Button, Toasts } from './components/ui.jsx';
import CreatePage from './pages/create/CreatePage.jsx';
import ImportPage from './pages/ImportPage.jsx';
import AnimasiPage from './pages/AnimasiPage.jsx';
import HistoryPage from './pages/HistoryPage.jsx';
import HooksPage from './pages/materials/HooksPage.jsx';
import HashtagsPage from './pages/materials/HashtagsPage.jsx';
import TrendsPage from './pages/materials/TrendsPage.jsx';
import BrandPage from './pages/materials/BrandPage.jsx';
import PreferencesPage from './pages/materials/PreferencesPage.jsx';
import MaterialsPage from './pages/materials/MaterialsPage.jsx';

/**
 * Racik — Contoh Brand (Garut, Jawa Barat)
 * Kerangka: rail kiri (desktop) / header + menu bawah (HP), halaman aktif, dialog, toast.
 * State & aksi ada di state/studio.jsx; data simulasi (?mock=1) di lib/mock.js.
 */
const PAGES = {
  create: CreatePage,
  import: ImportPage,
  animasi: AnimasiPage,
  history: HistoryPage,
  hooks: HooksPage,
  hashtags: HashtagsPage,
  trends: TrendsPage,
  brand: BrandPage,
  preferences: PreferencesPage,
  materials: MaterialsPage
};

function Layout() {
  const {
    currentPage,
    toasts,
    dismissToast,
    showReportModal,
    setShowReportModal,
    currentJob,
    unsavedModal,
    setUnsavedModal,
    confirmDiscardChanges
  } = useStudio();
  const Page = PAGES[currentPage] || CreatePage;

  return (
    <div className="min-h-screen">
      <a
        href="#konten"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[70] focus:rounded-md focus:bg-ink focus:text-paper focus:px-4 focus:py-2"
      >
        Langsung ke konten
      </a>
      <Rail />
      <MobileHeader />

      <main id="konten" className="lg:pl-60 pb-[calc(6rem+env(safe-area-inset-bottom))] lg:pb-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-10 pt-6 sm:pt-8 lg:pt-12">
          <Page />
        </div>
      </main>

      <BottomNav />

      <Dialog
        open={showReportModal}
        onClose={() => setShowReportModal(false)}
        title="Laporan produksi"
        size="lg"
        labelledBy="report-title"
        actions={
          <Button variant="secondary" onClick={() => setShowReportModal(false)}>
            Tutup
          </Button>
        }
      >
        <div
          className="prose-report text-sm text-ink break-words"
          dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(currentJob?.report_md || 'Laporan belum tersedia.') }}
        />
      </Dialog>

      <Dialog
        open={unsavedModal.open}
        onClose={() => setUnsavedModal({ open: false, targetPage: null })}
        title="Perubahan belum disimpan"
        labelledBy="unsaved-title"
        actions={
          <>
            <Button variant="secondary" onClick={() => setUnsavedModal({ open: false, targetPage: null })} data-autofocus>
              Kembali dan simpan
            </Button>
            <Button variant="danger-solid" icon={AlertTriangle} onClick={confirmDiscardChanges}>
              Buang perubahan
            </Button>
          </>
        }
      >
        <p className="text-sm text-muted">Perubahan di halaman ini akan hilang bila Anda pindah halaman tanpa menyimpan.</p>
      </Dialog>

      <Toasts toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}

export default function App() {
  return (
    <StudioProvider>
      <Layout />
    </StudioProvider>
  );
}
