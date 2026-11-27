import React from 'react';
import { Check } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { WIZARD_STEPS } from '../../lib/constants.js';
import { PageHeader, cx } from '../../components/ui.jsx';
import StepFootage from './StepFootage.jsx';
import StepSettings from './StepSettings.jsx';
import StepProcess from './StepProcess.jsx';
import ResultView from './ResultView.jsx';

const STEP_COPY = {
  1: 'Pilih pilar konten dan video mentahnya. AI akan memilih adegan terbaik dari semua klip.',
  2: 'Tulis instruksi singkat dan atur gayanya. Bagian yang dikosongkan akan diisi AI.',
  3: 'Laptop sedang memotong, menyusun, dan merender video. Halaman ini boleh ditinggal.',
  4: 'Periksa video, salin caption, lalu unggah ke Instagram.'
};

/** Penunjuk langkah: urutan nyata 1–4, jadi bernomor. */
function Stepper() {
  const { wizardStep, setWizardStep, canJumpToStep } = useStudio();
  return (
    <ol aria-label="Langkah membuat video" className="mt-8 grid grid-cols-4 gap-2 sm:gap-3">
      {WIZARD_STEPS.map((st) => {
        const active = wizardStep === st.num;
        const done = wizardStep > st.num;
        const jumpable = canJumpToStep(st.num) && !active;
        return (
          <li key={st.num} className="min-w-0">
            <button
              type="button"
              onClick={() => jumpable && setWizardStep(st.num)}
              disabled={!jumpable && !active}
              aria-current={active ? 'step' : undefined}
              className={cx(
                'w-full text-left pt-2.5 border-t-[3px] transition-colors',
                active ? 'border-brand' : done ? 'border-brand/45' : 'border-line',
                jumpable ? 'cursor-pointer hover:border-brand/70' : 'cursor-default'
              )}
            >
              <span className="flex items-center gap-1 sm:gap-1.5 min-w-0">
                <span
                  className={cx(
                    'font-display font-bold text-lg leading-none num',
                    active ? 'text-brand' : done ? 'text-muted' : 'text-muted/60'
                  )}
                >
                  {done ? <Check className="w-4 h-4" aria-label="selesai" /> : st.num}
                </span>
                <span
                  className={cx(
                    'text-[13px] sm:text-sm truncate',
                    active ? 'font-semibold text-ink' : done ? 'text-muted' : 'text-muted/70'
                  )}
                >
                  {st.label}
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}

export default function CreatePage() {
  const { wizardStep, currentJob } = useStudio();
  return (
    <div>
      <PageHeader title="Buat video" description={STEP_COPY[wizardStep]}>
        <Stepper />
      </PageHeader>
      {wizardStep === 1 && <StepFootage />}
      {wizardStep === 2 && <StepSettings />}
      {wizardStep === 3 && <StepProcess />}
      {wizardStep === 4 && currentJob && <ResultView />}
    </div>
  );
}
