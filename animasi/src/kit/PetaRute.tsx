// Peta skematis (bukan peta presisi): titik asal + tujuan yang muncul satu per satu, garis rute tergambar putus-putus.
// Posisi titik hanya arah kira-kira (utara = atas); jangan dipakai untuk jarak/rute sebenarnya.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useDetik} from './data';
import {masuk, pop} from './gerak';
import {Ikon} from './Ikon';
import {FONT_JUDUL, TINTA, WARNA, bayang, sudut, tepi, warna} from './tema';

export type Titik = {nama: string; x: number; y: number; mulai: number; warna?: string};

export const PetaRute: React.FC<{asal: Titik; tujuan: Titik[]; mulai: number}> = ({asal, tujuan, mulai}) => {
  const t = useDetik();
  const buka = pop(t, mulai, 160, 14);
  const pin = (p: Titik, utama = false) => {
    const s = pop(t, p.mulai, 260, 10);
    if (s <= 0) return null;
    return (
      <div key={p.nama} style={{position: 'absolute', left: p.x, top: p.y, transform: `translate(-50%, -100%) scale(${s})`, transformOrigin: '50% 100%'}}>
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
          <div
            style={{
              fontFamily: FONT_JUDUL,
              fontWeight: 800,
              fontSize: utama ? 46 : 50,
              background: utama ? WARNA.tinta : WARNA.putih,
              color: utama ? WARNA.kuning : WARNA.tinta,
              border: tepi(6),
              borderRadius: sudut(18),
              padding: '6px 20px',
              boxShadow: bayang(8),
              whiteSpace: 'nowrap',
              textTransform: 'uppercase',
              marginBottom: 8,
            }}
          >
            {p.nama}
          </div>
          <Ikon nama="pin" ukuran={utama ? 110 : 130} warna={p.warna ?? (utama ? 'hijau' : 'merah')} />
        </div>
      </div>
    );
  };
  return (
    <AbsoluteFill>
      <div
        style={{
          position: 'absolute',
          left: 50,
          top: 330,
          width: 980,
          height: 1180,
          background: WARNA.krem,
          border: tepi(9),
          borderRadius: sudut(48),
          boxShadow: bayang(16),
          overflow: 'hidden',
          transform: `scale(${buka}) rotate(${(1 - buka) * -8}deg)`,
        }}
      >
        <svg width={980} height={1180} style={{position: 'absolute', left: 0, top: 0}}>
          {/* kisi */}
          {Array.from({length: 12}, (_, i) => (
            <line key={`v${i}`} x1={i * 90} y1={0} x2={i * 90} y2={1180} stroke={TINTA} strokeOpacity={0.07} strokeWidth={3} />
          ))}
          {Array.from({length: 14}, (_, i) => (
            <line key={`h${i}`} x1={0} y1={i * 90} x2={980} y2={i * 90} stroke={TINTA} strokeOpacity={0.07} strokeWidth={3} />
          ))}
          {/* daratan & laut */}
          <path d="M0 0 L980 0 L980 980 C820 1010 700 960 560 1010 C420 1060 260 1000 0 1040 Z" fill={WARNA.hijauMuda} opacity={0.45} />
          <path d="M0 1040 C260 1000 420 1060 560 1010 C700 960 820 1010 980 980 L980 1180 L0 1180 Z" fill={WARNA.langit} stroke={TINTA} strokeWidth={6} />
          <path d="M110 230 L190 120 L270 230 Z M700 160 L780 60 L860 160 Z M170 690 L250 580 L330 690 Z" fill={WARNA.unguMuda} stroke={TINTA} strokeWidth={6} strokeLinejoin="round" opacity={0.8} />
          {/* rute */}
          {tujuan.map((d) => {
            const p = masuk(t, d.mulai - 0.35, 0.5);
            const ax = asal.x - 50;
            const ay = asal.y - 330;
            const bx = d.x - 50;
            const by = d.y - 330;
            const mx = (ax + bx) / 2 + (by - ay) * 0.25;
            const my = (ay + by) / 2 - (bx - ax) * 0.25;
            const pj = 2000;
            return (
              <path
                key={d.nama}
                d={`M${ax} ${ay} Q${mx} ${my} ${bx} ${by}`}
                fill="none"
                stroke={warna(d.warna ?? 'merah')}
                strokeWidth={14}
                strokeLinecap="round"
                strokeDasharray={`${pj * p} ${pj}`}
              />
            );
          })}
        </svg>
      </div>
      {pin(asal, true)}
      {tujuan.map((d) => pin(d))}
    </AbsoluteFill>
  );
};
