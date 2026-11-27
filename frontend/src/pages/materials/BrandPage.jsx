import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { useStudio } from '../../state/studio.jsx';
import { PageHeader, Section, Button, Field, IconButton } from '../../components/ui.jsx';
import { SaveActions } from './common.jsx';

export default function BrandPage() {
  const {
    options,
    brandConfig,
    setBrandConfig,
    saveBrandConfig,
    captionGuideConfig,
    setCaptionGuideConfig,
    saveCaptionGuideConfig,
    markDirty
  } = useStudio();

  const setBrand = (updater) => {
    setBrandConfig(updater);
    markDirty();
  };
  const setGuide = (updater) => {
    setCaptionGuideConfig(updater);
    markDirty();
  };
  const examples = captionGuideConfig.examples || [];
  const placeholderPrice = (brandConfig.price_per_day || '').includes('[');

  return (
    <div>
      <PageHeader
        title="Brand & caption"
        description="Data usaha yang boleh disebut AI, ajakan default di akhir video, dan gaya bahasa caption."
      />

      <Section id="brand-contact" title="Kontak resmi" description="Diubah lewat config/brand.yaml.">
        <dl className="grid sm:grid-cols-2 gap-x-8 gap-y-3">
          <div>
            <dt className="text-[13px] text-muted">WhatsApp</dt>
            <dd className="font-display font-bold text-2xl text-ink num" translate="no">
              {brandConfig.whatsapp}
            </dd>
          </div>
          <div>
            <dt className="text-[13px] text-muted">Instagram</dt>
            <dd className="font-display font-bold text-2xl text-ink" translate="no">
              {brandConfig.instagram}
            </dd>
          </div>
        </dl>
      </Section>

      <Section
        id="brand-offer"
        title="Penawaran"
        description="AI tidak mengarang harga. Biarkan [HARGA] bila belum pasti, dan harga tidak akan disebut di video maupun caption."
        aside={<SaveActions onSave={saveBrandConfig} label="Simpan brand" />}
      >
        <div className="space-y-5 max-w-2xl">
          <Field
            label="Harga sewa motor per hari"
            htmlFor="brand-price"
            hint={placeholderPrice ? 'Masih placeholder: harga tidak akan ditampilkan.' : 'Harga ini boleh disebut di video dan caption rental.'}
          >
            <input
              id="brand-price"
              type="text"
              value={brandConfig.price_per_day}
              onChange={(e) => setBrand((prev) => ({ ...prev, price_per_day: e.target.value }))}
              autoComplete="off"
              className="field"
            />
          </Field>
          <fieldset className="space-y-4">
            <legend className="text-sm font-semibold text-ink mb-1">CTA default per pilar</legend>
            {options.pillars.map((p) => (
              <Field key={p.id} label={p.label} htmlFor={`cta-default-${p.id}`}>
                <input
                  id={`cta-default-${p.id}`}
                  type="text"
                  value={brandConfig.default_cta?.[p.id] || ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setBrand((prev) => ({ ...prev, default_cta: { ...prev.default_cta, [p.id]: val } }));
                  }}
                  className="field"
                />
              </Field>
            ))}
          </fieldset>
        </div>
      </Section>

      <Section
        id="caption-guide"
        title="Gaya caption"
        description="Aturan yang diikuti AI saat menulis caption."
        aside={<SaveActions onSave={saveCaptionGuideConfig} label="Simpan panduan" dirtyAware={false} />}
      >
        <div className="space-y-5 max-w-2xl">
          {Object.keys(captionGuideConfig.fields || {}).map((key) => (
            <Field key={key} label={key} htmlFor={`cg-${key}`}>
              <input
                id={`cg-${key}`}
                type="text"
                value={captionGuideConfig.fields[key] || ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setGuide((prev) => ({ ...prev, fields: { ...prev.fields, [key]: val } }));
                }}
                className="field"
              />
            </Field>
          ))}

          <fieldset>
            <div className="flex items-baseline justify-between gap-3 mb-2">
              <legend className="text-sm font-semibold text-ink">Contoh caption (maksimal 3)</legend>
              {examples.length < 3 && (
                <Button
                  variant="ghost"
                  size="sm"
                  icon={Plus}
                  onClick={() => setGuide((prev) => ({ ...prev, examples: [...(prev.examples || []), ''] }))}
                >
                  Tambah contoh
                </Button>
              )}
            </div>
            {examples.length === 0 ? (
              <p className="text-sm text-muted">Belum ada contoh. Tambahkan caption yang gayanya Anda suka agar AI menirunya.</p>
            ) : (
              <ol className="space-y-4">
                {examples.map((ex, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="mt-2 w-5 shrink-0 font-display font-bold text-lg text-muted num">{idx + 1}</span>
                    <textarea
                      rows={4}
                      value={ex}
                      onChange={(e) => {
                        const val = e.target.value;
                        setGuide((prev) => {
                          const updated = [...prev.examples];
                          updated[idx] = val;
                          return { ...prev, examples: updated };
                        });
                      }}
                      aria-label={`Contoh caption ${idx + 1}`}
                      placeholder="Tulis caption dengan gaya bahasa yang diinginkan…"
                      className="field flex-1 min-w-0 resize-y"
                    />
                    <IconButton
                      label={`Hapus contoh ${idx + 1}`}
                      icon={Trash2}
                      className="hover:text-stop-text"
                      onClick={() =>
                        setGuide((prev) => {
                          const updated = [...prev.examples];
                          updated.splice(idx, 1);
                          return { ...prev, examples: updated };
                        })
                      }
                    />
                  </li>
                ))}
              </ol>
            )}
          </fieldset>
        </div>
      </Section>
    </div>
  );
}
