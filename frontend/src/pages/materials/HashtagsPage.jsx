import React, { useState } from 'react';
import { useStudio } from '../../state/studio.jsx';
import { PageHeader, Section } from '../../components/ui.jsx';
import { SaveActions, PillarSwitch, Chip, AddRow } from './common.jsx';

function ChipList({ items, kind, emptyText }) {
  const { removeSeoChip } = useStudio();
  if (!items.length) return <p className="text-sm text-muted">{emptyText}</p>;
  return (
    <ul className="flex flex-wrap gap-2">
      {items.map((item, idx) => (
        <Chip key={item} onRemove={() => removeSeoChip(kind, idx)} removeLabel={`Hapus ${item}`}>
          {item}
        </Chip>
      ))}
    </ul>
  );
}

export default function HashtagsPage() {
  const { activeSeoPillar, switchSeoPillar, pillarSeoConfig, addSeoChip, savePillarSeoConfig, getPillarLabel } = useStudio();
  const [tag, setTag] = useState('');
  const [keyword, setKeyword] = useState('');
  const cfg = pillarSeoConfig[activeSeoPillar] || { hashtags: [], keywords: [] };

  return (
    <div>
      <PageHeader
        title="Hashtag & keyword"
        description="Ditempel AI ke caption tiap video, sesuai pilar kontennya."
        actions={<SaveActions onSave={savePillarSeoConfig} label={`Simpan ${getPillarLabel(activeSeoPillar)}`} />}
      />
      <div className="mb-6">
        <PillarSwitch value={activeSeoPillar} onChange={(id) => switchSeoPillar(id).catch(() => {})} />
      </div>

      <Section
        id="seo-hashtags"
        title="Hashtag"
        description="Otomatis huruf kecil, tanpa spasi, diawali #. Tekan Enter atau koma untuk menambah."
      >
        <AddRow
          id="hashtag-input"
          value={tag}
          onChange={setTag}
          splitOnComma
          onAdd={() => {
            if (addSeoChip('hashtags', tag)) setTag('');
          }}
          label="Hashtag baru"
          placeholder="Mis. wisatagarut"
        />
        <div className="mt-4">
          <ChipList items={cfg.hashtags || []} kind="hashtags" emptyText="Belum ada hashtag untuk pilar ini." />
        </div>
      </Section>

      <Section
        id="seo-keywords"
        title="Keyword pencarian"
        description="Frasa yang sering dicari calon pelanggan. AI menyelipkannya secara wajar di caption."
      >
        <AddRow
          id="keyword-input"
          value={keyword}
          onChange={setKeyword}
          onAdd={() => {
            if (addSeoChip('keywords', keyword)) setKeyword('');
          }}
          label="Keyword baru"
          placeholder="Mis. sewa motor garut"
        />
        <div className="mt-4">
          <ChipList items={cfg.keywords || []} kind="keywords" emptyText="Belum ada keyword untuk pilar ini." />
        </div>
      </Section>
    </div>
  );
}
