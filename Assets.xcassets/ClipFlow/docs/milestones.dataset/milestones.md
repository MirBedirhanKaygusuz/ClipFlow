# ClipFlow Milestones

## Milestone 1 — Teknik Doğrulama ← AKTİF
**Hedef:** Sessizlik kesimi çalışıyor, end-to-end pipeline var.

- [x] silence_detector.py — FFmpeg ile sessizlik tespiti
- [x] video_cutter.py — Sessiz kısımları çıkararak birleştirme
- [x] format_converter.py — 9:16 dönüşüm
- [x] FastAPI app skeleton (main.py, config, routes)
- [x] POST /upload endpoint
- [x] POST /process endpoint (background task)
- [x] GET /process/{id} endpoint (polling)
- [x] GET /download/{id} endpoint
- [x] iOS: PHPicker ile video seçimi
- [x] iOS: URLSession upload
- [x] iOS: Polling + sonuç gösterme
- [x] Docker deployment setup
- [ ] End-to-end test: gerçek telefon → server → geri

**Done Kriteri:** Gerçek iPhone'dan video gönder, sessizlikleri kesilmiş hali geri gelsin.

---

## Milestone 2 — Beta Ready
- [ ] Error handling (tüm edge case'ler)
- [ ] R2 storage entegrasyonu
- [ ] Push notification (APNs)
- [ ] Progress reporting (detaylı step bilgisi)
- [ ] Basit UI polish
- [ ] TestFlight dağıtım

---

## Milestone 3 — Proje Klasörü
- [ ] Stil analizi engine (PySceneDetect + librosa)
- [ ] Stil profili kaydetme/yükleme
- [ ] Klasör CRUD API
- [ ] iOS: klasör yönetimi UI
- [ ] Stil bazlı edit üretimi

---

## Milestone 4 — Müzikli Edit
- [ ] Beat detection (librosa)
- [ ] Highlight detection (CV2 + motion)
- [ ] Müziğe senkronize kesim
- [ ] Geçiş efektleri (xfade)
- [ ] Müzik kütüphanesi/seçimi
