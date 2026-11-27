Bentuk JSON (ikuti persis nama field; nilai enum hanya dari pilihan dalam kurung):
{
  "version": "1.0",
  "pillar": "rental",                      // (rental|konstruksi|profil|lowongan|umum)
  "target_duration_sec": 20,
  "aspect": "9:16",
  "style_preset": "rental_energik",
  "hook": {"type": "visual_wow", "overlay_text": "Garut seindah ini kalau naik motor", "source_segment_index": 0},
                                           // type: (visual_wow|pertanyaan|harga|before_after|angka|kontras)
  "segments": [
    {"index": 0, "scene_id": "K4-1", "source_file": "K4", "start": 0.40, "end": 2.40,
     "role": "hook", "reason": "pengendara menyalakan motor, dinamis",
     "reframe": "subject_track", "speed": 1.0, "transition_in": "cut",
     "overlay_text": null, "keep_original_audio": false, "compare": null}
                                           // role: (hook|isi|bukti|suasana|cta)
                                           // reframe: (subject_track|center|blur_pad)
                                           // transition_in: (cut|fade|slide_left|zoom_punch|whip)
                                           // source_file: kode klip (mis. "K4") = awalan scene_id
                                           // compare (before–after, opsional): {"source_file": "K2", "scene_id": "K2-1", "start": 0.0, "end": 1.5}
  ],
  "subtitles": {"enabled": false, "style": "bold_putih_outline", "language": "id"},
  "music": {"mood": "upbeat", "volume_db": -14, "duck_under_speech": true, "cut_on_beat": true},
                                           // mood: (upbeat|santai|inspiratif|dramatis|none)
  "branding": {"logo": true, "position": "top_right"},
  "privacy": {"blur_faces": false, "blur_plates": false},
  "purpose": "promosi",                    // (promosi|informasi) — informasi: cta = null
  "cta": {"text": "Booking sekarang via WhatsApp!", "at_sec": 17.0},
  "caption_suggestion": "…",
  "hashtags": ["#rentalmotorgarut", "#wisatagarut"],
  "notes_for_human": "…"
}
JSON keluaran TIDAK boleh berisi komentar (//).
