# ADR-008: Akses dari HP lewat LAN + PIN, tanpa cloud

## Status
Diterima — R4 ditangani 2026-11-20 (5 PIN salah → kunci 60 dtk per perangkat)

## Konteks
Footage sering direkam di HP. Pengguna ingin mengunggah dan meninjau dari HP tanpa memindahkan file ke laptop
secara manual, tetapi tanpa membuka aplikasi ke internet.

## Keputusan
Default server hanya mendengarkan `127.0.0.1`. Dengan `python main.py --hp`, server mendengarkan `0.0.0.0` dan
membuat **PIN 6 digit acak** per sesi (ditampilkan di terminal laptop). Akses dari IP non-lokal wajib PIN; PIN yang
benar disimpan sebagai cookie `httponly`, `samesite=strict`, berlaku 12 jam. Semua `/api/*` dan `/media/*`
(termasuk `/media/footage`) dijaga aturan yang sama.

## Konsekuensi
### Positif
- Tanpa akun, cloud, atau aplikasi tambahan di HP.
- Footage tetap di jaringan lokal.
### Negatif
- Hanya di Wi-Fi yang sama; laptop harus menyala.
- Tanpa HTTPS: perekam suara di browser HP tidak tersedia (butuh *secure context*), jadi rekaman diunggah sebagai file.
- PIN 6 digit tanpa pembatas percobaan bisa ditebak oleh perangkat lain di jaringan yang sama (R4).

## Alternatif yang dipertimbangkan
- **Tunnel publik (ngrok/Cloudflare Tunnel)**: akses dari mana saja, tetapi membuka aplikasi ke internet.
- **Akun & kata sandi**: lebih kuat, tetapi berlebihan untuk 1–2 pengguna di satu kantor.

## Usulan lanjutan
Batasi percobaan PIN (mis. 5 salah → jeda 1 menit per IP).
