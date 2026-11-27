# Memakai video-use (mode chat) + impor ke AutoReels

**video-use** (github.com/browser-use/video-use, MIT) adalah skill Claude Code untuk mengedit video lewat
percakapan. Cocok untuk **video bicara** (testimoni, penjelasan layanan, info lowongan) dan video spesial,
selama Tahap 3 AutoReels belum selesai.

## Lokasi & instalasi (sudah dilakukan di laptop ini)

| Item | Lokasi |
|---|---|
| Repo video-use | `C:\Users\<user>\Developer\video-use` (di luar proyek AutoReels) |
| Skill Claude Code | `C:\Users\<user>\.claude\skills\video-use` → junction ke repo di atas |
| API key ElevenLabs | `C:\Users\<user>\Developer\video-use\.env` → `ELEVENLABS_API_KEY=...` |

Di komputer baru:
```powershell
git clone https://github.com/browser-use/video-use "$env:USERPROFILE\Developer\video-use"
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\video-use" -Target "$env:USERPROFILE\Developer\video-use"
copy "$env:USERPROFILE\Developer\video-use\.env.example" "$env:USERPROFILE\Developer\video-use\.env"   # lalu isi key
```
Helper video-use dipanggil dengan `python` sistem dan butuh `librosa`. **Pasang dengan versi terkunci**
agar paket lain di Python sistem tidak rusak:
```powershell
python -m pip install "numpy==1.26.4" "scipy==1.13.1" "librosa>=0.10.2,<0.11"
```

## Alur kerja

1. Taruh footage di folder, mis. `footage\profil\testimoni-pak-asep\`.
2. Buka terminal di folder itu, jalankan `claude`, lalu minta misalnya:
   > edit jadi Reels vertikal 1080×1920, 30–45 detik, untuk testimoni pelanggan rental motor Brand
3. video-use bertanya, mengusulkan strategi → setujui → hasil di `<folder>\edit\final.mp4`.
4. Impor ke AutoReels agar siap unggah (normalisasi, logo, CTA WhatsApp, caption + hashtag, checklist):
   - Menu: `python main.py` → **Impor video jadi** (video-use terbaru otomatis muncul di daftar), atau
   - CLI: `autoreels import --video "footage\profil\testimoni-pak-asep\edit\final.mp4" --pillar profil`
5. Hasil di `output\<job_id>\` (reel.mp4, caption.txt, cover.jpg, report.md) — sama seperti `autoreels run`.

Catatan: minta video-use membuat format **vertikal 9:16**. Bila hasilnya 16:9, AutoReels tetap
membuatnya 9:16 dengan latar blur, tetapi hasil vertikal asli lebih bagus.
