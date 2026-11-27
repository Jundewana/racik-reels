# ADR-006: Mesin AI ganda — API default, Ollama lokal opsional

## Status
Diterima sebagai uji coba (keputusan pemilik 2026-11-20)

## Konteks
API (Gemini untuk vision, Groq untuk teks) murah dan pintar tetapi kadang terkena batas kuota. Pemilik kini punya
laptop dengan RTX 4050 6 GB dan ingin meneliti performa model lokal. Prinsip awal proyek melarang model lokal agar
sistem tetap jalan di laptop tanpa GPU.

## Keputusan
- Mesin dipilih **per job** (`engine`: `api` | `local`) dari web atau CLI `--engine`. `api` tetap default.
- Model lokal (`LOCAL_LLM_MODEL`, `LOCAL_VISION_MODEL`) dipanggil `llm.py` langsung ke API HTTP Ollama (bukan lewat
  litellm) agar bisa mengatur `think`, skema JSON (`format`), dan `num_ctx`.
- **Tanpa cadangan diam-diam** dari lokal ke API: kegagalan model lokal dilaporkan, supaya hasil riset murni.
- Vision lokal memakai varian `-instruct` (tag polos `qwen3-vl:4b` adalah varian "thinking" yang lambat dan
  menghasilkan jawaban kosong saat mode berpikir dimatikan — teruji 2026-11-20).
- Tidak ada dependensi Python yang butuh GPU; Ollama adalah aplikasi terpisah.
- Default model teks lokal **`qwen3:4b`** (muat penuh di GPU 6 GB, ±35 token/dtk). `qwen3:8b` gagal di riset
  2026-11-20 (Director > 15 mnt) — lihat `eval/riset_mesin_lokal_2026-11-20.md`.

## Konsekuensi
### Positif
- Tetap bisa bekerja saat kuota API habis; tanpa biaya per video.
- Arsitektur tetap jalan di laptop tanpa GPU (mesin lokal tinggal tidak dipilih).
### Negatif
- Lebih lambat (±6 mnt vs ±2 mnt per video di riset); model 8B tidak muat penuh di VRAM 6 GB (±9 token/dtk).
- Kualitas Director model kecil lebih rendah → lebih sering direvisi validator (ADR-003).
- Dua jalur pemanggilan LLM yang harus dirawat.

## Alternatif yang dipertimbangkan
- **Hanya API**: paling sederhana, tetapi rentan limit kuota.
- **Hanya lokal**: tanpa biaya, tetapi memaksa GPU dan menurunkan kualitas.
- **litellm untuk Ollama**: satu jalur kode, tetapi opsi khusus (`think`, skema, konteks) tidak bisa diatur dengan andal.
