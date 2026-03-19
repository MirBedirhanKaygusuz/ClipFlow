# ClipFlow Milestones

## Milestone 1 — Teknik Doğrulama ← AKTİF
**Hedef:** Sessizlik kesimi çalışıyor, end-to-end pipeline var.

- [ ] silence_detector.py — FFmpeg ile sessizlik tespiti
- [ ] video_cutter.py — Sessiz kısımları çıkararak birleştirme
- [ ] format_converter.py — 9:16 dönüşüm
- [ ] FastAPI app skeleton (main.py, config, routes)
- [ ] POST /upload endpoint
- [ ] POST /process endpoint (background task)
- [ ] GET /process/{id} endpoint (polling)
- [ ] iOS: PHPicker ile video seçimi
- [ ] iOS: URLSession upload
- [ ] iOS: Polling + sonuç gösterme
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
