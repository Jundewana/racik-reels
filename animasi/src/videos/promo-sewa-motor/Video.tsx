import React from 'react';
import { AbsoluteFill } from 'remotion';
import { Adegan, Judul, CtaWA, WARNA } from '../../kit';

// Komponen SVG Khas: Motor Ikonik
const MotorIkon = () => (
  <svg viewBox="0 0 200 100" style={{ width: '100%', height: '100%' }}>
    <path d="M20 80 L180 80 L160 50 L120 50 L100 20 L60 20 L40 50 Z" fill={WARNA.merah} stroke={WARNA.tinta} strokeWidth="4" />
    <circle cx="50" cy="80" r="15" fill={WARNA.tinta} />
    <circle cx="150" cy="80" r="15" fill={WARNA.tinta} />
  </svg>
);

export const Video: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: WARNA.putih }}>
      {/* === ADEGAN 1: Hook === */}
      <Adegan dari={0} sampai={2}>
        <div style={{ backgroundColor: WARNA.hijau, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Judul baris={['Liburan ke Garut', 'Naik Kereta?']} />
        </div>
      </Adegan>

      {/* === ADEGAN 2: Masalah === */}
      <Adegan dari={2} sampai={4}>
        <div style={{ backgroundColor: WARNA.ungu, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Judul baris={['Bingung', 'Keliling Garut?']} />
        </div>
      </Adegan>

      {/* === ADEGAN 3: Solusi === */}
      <Adegan dari={4} sampai={6}>
        <div style={{ backgroundColor: WARNA.merah, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Judul baris={['Sewa Motor', 'Aja!']} />
          <MotorIkon />
        </div>
      </Adegan>

      {/* === ADEGAN 4: Keunggulan === */}
      <Adegan dari={6} sampai={10}>
        <div style={{ backgroundColor: WARNA.hijau, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Judul baris={['Fleksibel &', 'Praktis']} />
        </div>
      </Adegan>

      {/* === ADEGAN 5: Rental === */}
      <Adegan dari={10} sampai={20}>
        <div style={{ backgroundColor: WARNA.ungu, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Judul baris={['Rental Motor', 'Garut No. 1']} />
        </div>
      </Adegan>

      {/* === ADEGAN 6: Harga === */}
      <Adegan dari={20} sampai={25}>
        <div style={{ backgroundColor: WARNA.merah, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Judul baris={['Mulai dari', '100 Ribuan!']} />
        </div>
      </Adegan>

      {/* === ADEGAN 7: CTA === */}
      <Adegan dari={25} sampai={41}>
        <div style={{ backgroundColor: WARNA.hijau, width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column' }}>
          <Judul baris={['Booking', 'Sekarang!']} />
          <CtaWA mulai={25} />
        </div>
      </Adegan>
    </AbsoluteFill>
  );
};