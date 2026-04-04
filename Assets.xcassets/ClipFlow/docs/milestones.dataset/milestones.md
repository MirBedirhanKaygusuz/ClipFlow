# ClipFlow Milestones

## Milestone 1 — Teknik Doğrulama ✅
**Hedef:** Sessizlik kesimi çalışıyor, end-to-end pipeline var.

- [x] silence_detector.py — FFmpeg ile sessizlik tespiti
- [x] video_cutter.py — Sessiz kısımları çıkararak birleştirme
- [x] format_converter.py — 9:16 dönüşüm
- [x] FastAPI app skeleton (main.py, config, routes)
- [x] POST /upload endpoint (multipart + raw binary)
- [x] POST /process endpoint (background task)
- [x] GET /process/{id} endpoint (polling + ETA)
- [x] GET /download/{id} endpoint
- [x] iOS: PHPicker ile video seçimi
- [x] iOS: URLSession upload (streaming)
- [x] iOS: Polling + sonuç gösterme
- [x] Docker deployment setup
- [x] Quality mode (reels / high_quality)
- [x] Pydantic v2 ConfigDict
- [x] CI/CD (GitHub Actions)

---

## Milestone 2 — Beta Ready ✅
- [x] Async FFmpeg runner (retry + timeout)
- [x] Error handling (processing timeout, cleanup)
- [x] R2 storage entegrasyonu (abstraction layer)
- [x] Push notification (APNs)
- [x] Progress reporting (detaylı step + ETA)

---

## Milestone 3 — Proje Klasörü ✅
- [x] Stil analizi engine (FFmpeg scene detection + librosa)
- [x] Stil profili kaydetme/yükleme (JSON CRUD)
- [x] Klasör CRUD API
- [x] iOS: klasör yönetimi UI
- [x] Stil CRUD endpoint'leri

---

## Milestone 4 — Müzikli Edit ✅
- [x] Beat detection (librosa beat_track + onset detection)
- [x] Highlight detection (motion + audio energy)
- [x] Müziğe senkronize kesim (beat alignment)
- [x] Geçiş efektleri (xfade + acrossfade)
- [x] Müzik kütüphanesi (upload, analyze, list, delete)
- [x] Musical edit worker pipeline
- [x] Audio mixing (video + music)
- [x] iOS entegrasyonu (ProcessingMode, MusicTrack model)
