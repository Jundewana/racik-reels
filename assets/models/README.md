# Model deteksi (CPU, OpenCV)

Dipakai `autoreels/render/privacy.py` untuk **blur privasi** (pilihan per video, default mati) dan `autoreels/analyze/objects.py` untuk **crop pengikut subjek**. Dijalankan dengan
OpenCV (`cv2.FaceDetectorYN` dan `cv2.dnn`) — tanpa GPU, tanpa paket Python tambahan.

| File | Kegunaan | Sumber | Lisensi |
|---|---|---|---|
| `face_detection_yunet_2023mar.onnx` (0,2 MB) | deteksi wajah (YuNet) | [opencv_zoo/models/face_detection_yunet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | MIT |
| `license_plate_detection_lpd_yunet_2023mar.onnx` (4 MB) | deteksi pelat nomor (LPD-YuNet) | [opencv_zoo/models/license_plate_detection_yunet](https://github.com/opencv/opencv_zoo/tree/main/models/license_plate_detection_yunet) | Apache 2.0 |
| `object_detection_nanodet_2022nov.onnx` (3,8 MB) | deteksi objek COCO (motor, orang, mobil) untuk **crop pengikut subjek** (`autoreels/analyze/objects.py`, ±20 ms/frame proxy) | [opencv_zoo/models/object_detection_nanodet](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_nanodet) | Apache 2.0 |
| `human_segmentation_pphumanseg_2023mar.onnx` (6 MB) | segmentasi orang untuk **teks hook di belakang orang** (`autoreels/render/behind.py`, ±11 ms/frame, hanya selama hook) | [opencv_zoo/models/human_segmentation_pphumanseg](https://github.com/opencv/opencv_zoo/tree/main/models/human_segmentation_pphumanseg) | Apache 2.0 |

Catatan (uji 2026-11-20):
- Model pelat dilatih pada pelat Tiongkok; pada footage rental, pelat Indonesia "AB …" terdeteksi, tetapi pelat
  kecil/miring/buram bisa terlewat. Hasil blur selalu perlu ditinjau manusia (checklist mencatat jumlah frame terdeteksi).
- Ambang skor wajah 0,8: skor 0,6–0,76 terbukti salah deteksi (pengendara jauh terlihat dari belakang).
