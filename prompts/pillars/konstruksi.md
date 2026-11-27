## Pilar: Konstruksi & Arsitektur
Audiens: instansi pemerintah/desa, pemilik proyek swasta. Tujuan: kredibilitas & portofolio.
Alur: hook before–after singkat → proses kronologis (speed-up 4–8×) → hasil akhir → kredibilitas → CTA konsultasi.

Aturan khusus pilar ini:
- **Hook before–after**: bila ada adegan `tahap=awal` DAN `tahap=hasil`, segmen 0 memakai adegan `hasil`
  (`role`="hook", durasi 2,0–3,0 dtk) dengan `compare` = adegan `awal` (start/end di dalam rentang adegan itu).
  `hook.type` = "before_after". Teks hook contoh: "Dari lahan kosong jadi…", "Lihat bedanya".
  Bila salah satu tahap tidak ada, pakai hook biasa (adegan dengan hook tertinggi) dan `compare` = null.
- **Kronologis**: urutkan segmen isi awal → proses → hasil.
- **Speed-up (WAJIB bila `style_preset.default_speed_progress` ada)**: SETIAP segmen isi dengan adegan
  `tahap=proses` yang geraknya "pelan"/"diam" (drone, crane, alat berat, pekerja dari jauh) diberi `speed` =
  `default_speed_progress` (dalam `speed_range`) — biasanya lebih dari separuh segmen isi. Ambil rentang sumber yang
  lebih panjang agar durasi tampil = (end − start) / speed tetap sesuai tempo. Adegan "dinamis" (percikan gerinda,
  close-up tangan) dan hasil akhir: `speed` 1.0. Kode akan menambahkan speed-up yang terlewat.
Nada profesional; jangan menyebut nama klien/proyek kecuali ada di instruksi.
