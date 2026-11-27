# Laporan Evaluasi AutoReels — set uji

Dibuat 2026-11-24 15:01. 9 job selesai, 3 job gagal. Metrik otomatis; rubrik manusia & metrik lapangan dicatat terpisah (lihat eval/rubric.md).

## Ringkasan
| Kelompok | Job | Siap unggah | Waktu proses | Biaya (USD) | Durasi ±10% | Hook ≤ 3 dtk | Ketepatan beat | Revisi validasi | Skor Critic | Skor hook |
|---|---|---|---|---|---|---|---|---|---|---|
| **Semua** | 9 | 56% (5/9) | 222 dtk | 0.0351 | 89% (8/9) | 100% (9/9) | 1.00 | 0.22 | 4.18 | 3.88 |

## Per pilar & alur
| Kelompok | Job | Siap unggah | Waktu proses | Biaya (USD) | Durasi ±10% | Hook ≤ 3 dtk | Ketepatan beat | Revisi validasi | Skor Critic | Skor hook |
|---|---|---|---|---|---|---|---|---|---|---|
| rental (narasi) | 4 | 100% (4/4) | 196 dtk | 0.0310 | 100% (4/4) | 100% (4/4) | - | 0.00 | 3.96 | 4.25 |
| rental (video) | 2 | 50% (1/2) | 250 dtk | 0.0334 | 50% (1/2) | 100% (2/2) | 1.00 | 1.00 | 4.57 | 5.00 |
| umum (bicara) | 3 | 0% (0/3) | 237 dtk | 0.0416 | 100% (3/3) | 100% (3/3) | - | 0.00 | 4.34 | 3.00 |

## Perbandingan model Director

Penilai (Critic): cohere_chat/command-a-03-2025 — sama untuk semua model, jadi skor bisa dibandingkan.

| Kelompok | Job | Siap unggah | Waktu proses | Biaya (USD) | Durasi ±10% | Hook ≤ 3 dtk | Ketepatan beat | Revisi validasi | Skor Critic | Skor hook |
|---|---|---|---|---|---|---|---|---|---|---|
| cohere_chat/command-a-plus-05-2026 | 2 | 50% (1/2) | 294 dtk | 0.0312 | 100% (2/2) | 100% (2/2) | - | 0.00 | 4.14 | 3.50 |
| gemini/gemini-3.5-flash-lite | 3 | 67% (2/3) | 115 dtk | 0.0492 | 100% (3/3) | 100% (3/3) | 1.00 | 0.00 | 4.29 | 4.33 |
| runcrate/openai/gpt-oss-120b | 3 | 33% (1/3) | 292 dtk | 0.0305 | 67% (2/3) | 100% (3/3) | 1.00 | 0.67 | 4.14 | 3.50 |
| runcrate/zai-org/GLM-5.3-Flash | 1 | 100% (1/1) | 186 dtk | 0.0143 | 100% (1/1) | 100% (1/1) | - | 0.00 | 4.00 | 4.00 |

## Skor rubrik Critic per aspek (rata-rata, 1–5)
| Aspek | Rata-rata | Terendah | < 4 |
|---|---|---|---|
| Kekuatan hook | 3.88 | 3 | 3 |
| Kesesuaian instruksi & pilar | 4.50 | 4 | 0 |
| Alur / koherensi | 3.50 | 3 | 4 |
| Tempo sesuai style | 4.38 | 4 | 0 |
| Keterbacaan teks | 3.88 | 3 | 2 |
| Kejelasan CTA | 4.62 | 4 | 0 |
| Konsistensi brand | 4.50 | 4 | 0 |

Revisi atas catatan Critic: 6 dari 8 job (rata-rata 1.38 putaran).

## Butir checklist wajib yang paling sering gagal
| Butir | Jumlah job |
|---|---|
| Hook benar — Skor hook dari Critic ≥ 4 | 3 |
| Video jadi — Durasi target ±10% | 1 |
| Siap posting — Validasi EDL tanpa error | 1 |

## Job gagal (error)
| Job | Alasan |
|---|---|
| 20261124-142858-rental | ValueError: Output LLM tetap tidak valid setelah 3 percobaan: |
| 20261124-143041-rental | RuntimeError: Panggilan LLM ke 'cohere_chat/command-a-plus-05-2026' gagal: litellm.Timeout: CohereException - litellm.Timeout: Read timed out. Timeout passed=12 |
| 20261124-145219-umum | ValueError: Output LLM tetap tidak valid setelah 3 percobaan: |

## Per job
| Job | Set | Pilar | Mesin | Critic | Status | Durasi/target | Hook | Beat | Biaya | Waktu | Skor Critic |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261124-142039-rental | rental-energik | rental | api | revisi | ✅ siap_unggah | 21.7/20 | 1.57 | 1.00 | 0.0669 | 100 | 4.57 |
| 20261124-142219-rental | rental-energik | rental | api | revisi | ⚠️ perlu_tinjau | 16.4/20 | 1.87 | 1.00 | 0.0000 | 399 | - |
| 20261124-143243-rental | narasi-rental | rental | api | revisi | ✅ siap_unggah | 43.7/44 | 2.07 | - | 0.0249 | 110 | 4.00 |
| 20261124-143432-rental | narasi-rental | rental | api | revisi | ✅ siap_unggah | 43.7/44 | 2.07 | - | 0.0563 | 223 | 3.86 |
| 20261124-143815-rental | narasi-rental | rental | api | revisi | ✅ siap_unggah | 43.7/44 | 2.07 | - | 0.0143 | 186 | 4.00 |
| 20261124-144120-rental | narasi-rental | rental | api | revisi | ✅ siap_unggah | 43.7/44 | 2.07 | - | 0.0285 | 267 | 4.00 |
| 20261124-144547-umum | bicara-podcast | umum | api | revisi | ⚠️ perlu_tinjau | 26.4/26 | 2.87 | - | 0.0559 | 136 | 4.29 |
| 20261124-144804-umum | bicara-podcast | umum | api | revisi | ⚠️ perlu_tinjau | 44.1/44 | 1.57 | - | 0.0351 | 255 | 4.43 |
| 20261124-145627-umum | bicara-podcast | umum | api | revisi | ⚠️ perlu_tinjau | 39.8/40 | 1.57 | - | 0.0339 | 321 | 4.29 |
