// Kartu CTA: ajakan + nomor WhatsApp dari brand.yaml (tidak pernah dikarang) + akun IG. Tombol berdenyut.
import React from 'react';
import {Img, staticFile} from 'remotion';
import {useData, useDetik} from './data';
import {goyang, pop} from './gerak';
import {Ikon} from './Ikon';
import {FONT_ISI, FONT_JUDUL, GAYA, TINTA, WARNA, bayang, sudut, tepi} from './tema';

export const CtaWA: React.FC<{mulai: number; judul?: string; y?: number; logo?: boolean}> = ({mulai, judul = 'Booking sekarang!', y = 900, logo = false}) => {
  const {brand} = useData();
  const t = useDetik();
  const p = pop(t, mulai, 170, 12);
  if (p <= 0) return null;
  const denyut = 1 + 0.045 * Math.max(0, goyang(t, 1, 1.4));
  const tombol = pop(t, mulai + 0.35, 220, 11);
  return (
    <div
      style={{
        position: 'absolute',
        left: 540,
        top: y,
        width: 920,
        transform: `translate(-50%, -50%) scale(${p}) rotate(${(1 - p) * 10 - 2}deg)`,
        background: WARNA.putih,
        border: tepi(9),
        borderRadius: sudut(56),
        boxShadow: bayang(20),
        padding: '56px 48px 64px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 30,
        boxSizing: 'border-box',
      }}
    >
      {logo && brand.logo ? (
        <Img src={staticFile(brand.logo)} style={{height: 150, borderRadius: 24, border: tepi(5)}} />
      ) : null}
      <div
        style={{
          fontFamily: FONT_JUDUL,
          fontWeight: 800,
          fontSize: 92,
          lineHeight: 1,
          textAlign: 'center',
          color: WARNA.ungu,
          textTransform: 'uppercase',
        }}
      >
        {judul}
      </div>
      <div
        style={{
          transform: `scale(${tombol * denyut})`,
          display: 'flex',
          alignItems: 'center',
          gap: 22,
          background: WARNA.hijau,
          border: tepi(7),
          borderRadius: 999,
          boxShadow: bayang(12, WARNA.hijau),
          padding: '18px 44px 18px 22px',
        }}
      >
        <Ikon nama="chat" ukuran={120} warna="putih" />
        <div style={{display: 'flex', flexDirection: 'column'}}>
          <span style={{fontFamily: FONT_ISI, fontWeight: 600, fontSize: 40, color: WARNA.putih}}>WhatsApp</span>
          <span
            style={{
              fontFamily: FONT_JUDUL,
              fontWeight: 800,
              fontSize: 74,
              color: WARNA.putih,
              WebkitTextStroke: GAYA.teks === 'garis' ? `8px ${TINTA}` : undefined,
              paintOrder: 'stroke fill',
              whiteSpace: 'nowrap',
            }}
          >
            {brand.whatsapp}
          </span>
        </div>
      </div>
      {brand.instagram ? (
        <div style={{fontFamily: FONT_ISI, fontWeight: 600, fontSize: 44, color: TINTA, opacity: pop(t, mulai + 0.6)}}>{brand.instagram}</div>
      ) : null}
    </div>
  );
};
