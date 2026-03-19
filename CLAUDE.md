# ClipFlow — AI Destekli iOS Video Editörü

## Proje Nedir?
ClipFlow, kullanıcının "editing DNA"sını öğrenen bir AI video editörüdür.
Kullanıcı örnek videolar yükler → AI stil öğrenir → her yeni videoya aynı stili uygular.
Solo developer projesi. Hız ve basitlik her şeyden önemli.

## Tech Stack
- **Backend:** Python 3.12 + FastAPI (async)
- **Video İşleme:** FFmpeg (subprocess, ffmpeg-python DEĞİL)
- **Ses Analizi:** librosa (beat detection, tempo), pydub
- **Transkript:** OpenAI Whisper API
- **Sahne Tespiti:** PySceneDetect
- **Depolama:** Cloudflare R2 (S3 uyumlu, $0 egress)
- **Job Queue:** V1'de BackgroundTasks, V2+'da Redis + Celery
- **iOS:** Swift + SwiftUI (MVVM pattern)
- **Hosting:** Hetzner VPS (~€4/ay)
- **Push:** APNs (Apple Push Notification)

## Mimari Kural — MUTLAKA UYULMALI
- iOS = thin client. ASLA iOS'ta video işleme yapma.
- Tüm heavy lifting Python backend'de olacak.
- FFmpeg doğrudan subprocess ile çağrılacak. ffmpeg-python wrapper KULLANMA.
- Her endpoint async olacak.
- File upload: multipart/form-data → R2'ye kaydet.
- Video işleme: background task → polling ile status kontrolü.
- Type hints zorunlu, her fonksiyona docstring yaz.
- Pydantic v2 model kullan input/output validation için.

## Proje Yapısı
```
clipflow/
├── CLAUDE.md              ← Bu dosya (her session okur)
├── backend/
│   ├── app/
│   │   ├── main.py        ← FastAPI app
│   │   ├── config.py      ← Settings (env vars)
│   │   ├── api/routes/    ← Endpoint'ler
│   │   ├── services/      ← İş mantığı
│   │   ├── models/        ← Pydantic modeller
│   │   └── workers/       ← Video işleme pipeline'ları
│   ├── tests/
│   └── requirements.txt
├── ios/ClipFlow/          ← Xcode projesi
├── docs/                  ← Mimari kararlar, API spec
└── memory/                ← Öğrenilen dersler, kararlar
```

## Aktif Milestone
**Milestone 1 — Teknik Doğrulama**
- [ ] Python + FFmpeg: sessizlik tespiti terminalde çalışıyor
- [ ] FastAPI: /upload, /process, /status endpoint'leri
- [ ] iOS: PHPicker ile video seç, server'a upload et
- [ ] End-to-end: iPhone → server → sessizlik kes → geri gönder

## Yapılmaması Gerekenler — DOKUNMA
- Timeline editörü (V4, şimdi değil)
- Müzikli edit (V3, şimdi değil)
- Ekip paylaşımı (V4, şimdi değil)
- Karmaşık UI elementleri (slider, timeline bar vs.)
- ffmpeg-python kütüphanesi (doğrudan subprocess kullan)

## Kodlama Standartları
### Python
- Python 3.12+
- Formatter: black
- Linter: ruff
- Type hints: her fonksiyona
- Docstrings: Google style
- Async/await: her I/O işlemi
- Error handling: custom exception class'ları app/exceptions.py'de
- Logging: structlog, JSON format

### Swift
- SwiftUI only (UIKit yok, gerekmedikçe)
- MVVM pattern
- async/await (Combine DEĞİL)
- PHPickerViewController: video seçimi
- URLSession: network (Alamofire vs. KULLANMA)

## API Endpoint Özeti (V1)
```
POST /upload          → Dosya yükleme (multipart)
POST /process         → İşleme başlat (job_id döner)
GET  /process/{id}    → Status polling (progress %)
GET  /download/{id}   → İşlenmiş video indir
```

## Sık Yapılan Hatalar
- FFmpeg komutlarında path'leri tırnak içine al (boşluk sorunu)
- Video codec: her zaman libx264 + aac çıktı ver
- 9:16 format: -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
- Whisper API çağrısında timeout 300sn olmalı (uzun videolar)
- iOS'ta Background URLSession kullan (app kapansa da upload devam etsin)
