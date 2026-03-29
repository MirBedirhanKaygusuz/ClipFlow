# ClipFlow — Xcode Agent Tam Proje Briefing'i

> Bu dosya, Xcode agent'ın projeyi tam olarak anlaması için yazılmıştır.
> Her şeyi kapsar: vizyon, mimari, API kontratı, iOS kodu, backend yapısı, kurallar, milestone'lar.

---

## 1. PROJE NEDİR?

ClipFlow, kullanıcının **"editing DNA"sını öğrenen** bir AI video editörüdür.

**Akış:**
1. Kullanıcı iPhone'dan video seçer
2. Video backend'e upload edilir
3. AI sessizlikleri tespit eder, keser, 9:16 formata çevirir
4. Sonuç iPhone'a geri gelir, kullanıcı izler ve Camera Roll'a kaydeder

**Solo developer projesi.** Hız ve basitlik her şeyden önemli.

---

## 2. TEKNİK MİMARİ

```
┌─────────────┐     HTTP/REST      ┌──────────────────┐
│   iOS App   │ ◄────────────────► │  Python Backend   │
│  (SwiftUI)  │    multipart       │   (FastAPI)       │
│  thin client│    polling         │                   │
└─────────────┘                    │  ┌─────────────┐  │
                                   │  │   FFmpeg     │  │
                                   │  │   Whisper    │  │
                                   │  │   librosa    │  │
                                   │  └─────────────┘  │
                                   │         │         │
                                   │    ┌────▼────┐    │
                                   │    │ Storage  │    │
                                   │    │ (V1:disk)│    │
                                   │    │ (V2:R2)  │    │
                                   │    └─────────┘    │
                                   └──────────────────┘
```

### Kritik Kural: iOS = Thin Client
- **ASLA** iOS'ta video işleme yapma
- **ASLA** iOS'ta FFmpeg/librosa/Whisper çalıştırma
- iOS sadece: video seç → upload → polling → preview → kaydet
- Tüm heavy lifting Python backend'de olacak

---

## 3. TECH STACK

### Backend (Python 3.12)
| Teknoloji | Amaç | Not |
|-----------|-------|-----|
| FastAPI | Web framework | Async native, Pydantic entegre |
| FFmpeg | Video işleme | subprocess ile çağır, ffmpeg-python KULLANMA |
| librosa | Ses analizi | Beat detection, tempo |
| Whisper API | Transkript | OpenAI API, timeout 300sn |
| PySceneDetect | Sahne tespiti | ContentDetector |
| Cloudflare R2 | Storage (V2) | S3 uyumlu, V1'de local disk |
| structlog | Logging | JSON format |
| Pydantic v2 | Validation | Input/output modeller |

### iOS (Swift + SwiftUI)
| Teknoloji | Amaç | Not |
|-----------|-------|-----|
| SwiftUI | UI framework | UIKit yok (gerekmedikçe) |
| MVVM | Mimari pattern | Views → ViewModels → Services |
| async/await | Concurrency | Combine DEĞİL |
| PHPicker | Video seçimi | PhotosUI framework |
| URLSession | Network | Alamofire KULLANMA |
| AVKit | Video oynatma | AVPlayer |
| Photos | Camera Roll | PHPhotoLibrary |

### Hosting & Deploy
| Teknoloji | Amaç |
|-----------|-------|
| Hetzner VPS | ~€4/ay, backend hosting |
| Docker | Containerized deployment |
| APNs | Push notification |

---

## 4. API KONTRATI — Eksiksiz Referans

**Base URL:** `http://<server-ip>:8000/api/v1`

### POST /upload
Video dosyası yükler.

```
Request: multipart/form-data
  field: "file" (binary) — MP4, MOV, M4V

Response 200:
  { "file_id": "uuid-string", "size_mb": 12.5 }

Errors:
  400 → Geçersiz format
  413 → Dosya çok büyük (>500MB)
```

### POST /process
Video işleme başlatır. Job ID döner.

```
Request: application/json
{
  "clip_ids": ["file_id_1", "file_id_2"],
  "mode": "talking_reels",
  "settings": {
    "output_format": "9:16",
    "add_captions": true,
    "silence_threshold_db": -30,
    "min_silence_duration": 0.3
  },
  "device_token": "apns-token-string"  // opsiyonel
}

Response 202:
  { "job_id": "uuid", "estimated_seconds": 90 }

Errors:
  400 → Bilinmeyen mod
```

### GET /process/{job_id}
İşleme durumunu sorgular (polling).

```
Response — İşleniyor:
{
  "status": "processing",
  "progress": 65,
  "step": "silence_detection"
}

Response — Karar bekliyor:
{
  "status": "awaiting_decision",
  "question": "Hangi tempo?",
  "options": ["Hızlı (28 kesim/dk)", "Sakin (12 kesim/dk)"]
}

Response — Tamamlandı:
{
  "status": "done",
  "progress": 100,
  "step": "completed",
  "output_url": "/download/result-file-id",
  "stats": {
    "original_duration": 120.5,
    "new_duration": 78.3,
    "silence_removed_pct": 35.0,
    "segments": 23
  }
}

Response — Hata:
{
  "status": "failed",
  "step": "error",
  "progress": 0
}

Job Status Enum: queued | processing | awaiting_decision | done | failed
Processing Steps: silence_detection → cutting → format_conversion → completed
```

### POST /process/{job_id}/decision
Binary karar gönderir (awaiting_decision durumunda).

```
Request: query param choice=0 veya choice=1

Response 200:
  { "status": "ok" }
```

### GET /download/{file_id}
İşlenmiş videoyu indirir.

```
Response: video/mp4 binary stream
Headers: Content-Disposition: attachment; filename="<file_id>.mp4"

Errors:
  404 → Dosya bulunamadı
```

### GET /health
Sağlık kontrolü.

```
Response 200:
  { "status": "ok", "version": "0.1.0" }
```

---

## 5. iOS PROJE YAPISI — Mevcut Kod

```
ios/ClipFlow/
├── ClipFlowApp.swift           → @main entry point, WindowGroup → HomeView
├── Info.plist                   → Photo Library izinleri
├── Models/
│   └── APIModels.swift          → Codable struct'lar (server response'ları)
├── Services/
│   └── APIService.swift         → actor, URLSession, multipart upload, polling
├── ViewModels/
│   └── MainViewModel.swift      → AppState enum, iş akışı yönetimi
└── Views/
    ├── HomeView.swift           → Ana ekran (state-driven rendering)
    ├── VideoPicker.swift        → PHPickerViewController wrapper
    └── PreviewView.swift        → AVPlayer preview + stats + kaydet
```

> **NOT:** Xcode projesi (.xcodeproj) henüz oluşturulmadı. Source dosyalar hazır.
> Xcode'da File > New > Project > App ile oluşturup bu dosyaları eklemen gerekiyor.

### Xcode Proje Ayarları
- **Bundle ID:** com.clipflow.app
- **Minimum iOS:** 17.0
- **Interface:** SwiftUI
- **Language:** Swift
- **Capabilities:** (V2'de) Push Notifications

---

## 6. iOS MEVCUT KOD DETAYLARI

### AppState Enum (MainViewModel.swift)
```swift
enum AppState {
    case idle
    case uploading(progress: Double)
    case processing(progress: Int, step: String)
    case done(videoURL: URL, stats: ProcessingStats)
    case error(String)
}
```

### API Models (APIModels.swift)
```swift
struct UploadResponse: Codable {
    let fileId: String      // snake_case → camelCase mapping
    let sizeMb: Double
}

struct ProcessResponse: Codable {
    let jobId: String
    let estimatedSeconds: Int
}

struct StatusResponse: Codable {
    let status: String
    let progress: Int?
    let step: String?
    let outputUrl: String?
    let question: String?
    let options: [String]?
    let stats: ProcessingStats?
}

struct ProcessingStats: Codable {
    let originalDuration: Double?
    let newDuration: Double?
    let silenceRemovedPct: Double?
    let segments: Int?
}
```

### Network Flow (APIService.swift)
```
1. upload(videoURL) → multipart/form-data POST → UploadResponse
2. startProcessing(fileId) → JSON POST → ProcessResponse
3. getStatus(jobId) → GET polling → StatusResponse
4. downloadVideo(fileId) → URLSession.download → local file URL
```

### UI Flow (HomeView.swift)
```
idle          → "Video Seç" butonu → PHPicker açılır
uploading     → Progress bar + "Yükleniyor..." texti
processing    → Progress bar + adım bilgisi (Türkçe)
done          → PreviewView (AVPlayer + stats + kaydet butonu)
error         → Hata mesajı + "Tekrar Dene" butonu
```

### Polling (MainViewModel.swift)
- 2 saniye aralıklarla `GET /process/{jobId}` çağrılır
- `done` → video indirilir, PreviewView gösterilir
- `awaiting_decision` → UI'da seçenekler gösterilir
- `failed` → error state'e geçilir

---

## 7. BACKEND PROJE YAPISI

```
backend/
├── Dockerfile                → Python 3.12 + FFmpeg
├── .dockerignore
├── .env.example              → Tüm env var'lar (R2, Whisper, APNs)
├── requirements.txt          → Tüm Python bağımlılıkları
├── pytest.ini
├── app/
│   ├── main.py               → FastAPI app + lifespan (FFmpeg check, storage dir)
│   ├── config.py             → Pydantic BaseSettings (.env okur)
│   ├── exceptions.py         → ClipFlowError, VideoTooLargeError, FFmpegError
│   ├── api/routes/
│   │   ├── upload.py         → POST /upload (multipart, chunk write, size check)
│   │   ├── process.py        → POST /process + GET /process/{id} + decision
│   │   └── download.py       → GET /download/{id} (FileResponse)
│   ├── models/
│   │   └── job.py            → JobStatus enum, ProcessRequest, StatusResponse
│   ├── services/
│   │   ├── job_manager.py    → V1: in-memory dict (V2: Redis)
│   │   ├── silence_detector.py → FFmpeg silencedetect + cut
│   │   └── format_converter.py → 9:16 dönüşüm
│   └── workers/
│       └── talking_reels.py  → Pipeline: detect → cut → convert → done
└── tests/
    ├── conftest.py           → TestClient fixture
    ├── test_upload.py        → 3 test (valid mp4, invalid ext, mov accepted)
    ├── test_process.py       → 4 test (start, invalid mode, not found, status)
    └── test_download.py      → 2 test (not found, valid file)
```

### Backend Config (.env)
```
STORAGE_PATH=/tmp/clipflow
R2_ENDPOINT=https://xxx.r2.cloudflarestorage.com
R2_ACCESS_KEY=...
R2_SECRET_KEY=...
R2_BUCKET=clipflow
WHISPER_API_KEY=sk-...
MAX_UPLOAD_SIZE_MB=500
FFMPEG_PRESET=fast
SILENCE_THRESHOLD_DB=-30
MIN_SILENCE_DURATION=0.3
MAX_CONCURRENT_JOBS=3
```

---

## 8. MİMARİ KARARLAR

| # | Karar | Neden | Alternatif |
|---|-------|-------|------------|
| AD-001 | FastAPI (Flask değil) | Async native, Pydantic entegre | Flask |
| AD-002 | FFmpeg subprocess (wrapper değil) | ffmpeg-python bug'lı, filter_complex'te sorun | ffmpeg-python |
| AD-003 | V1 local disk (R2 değil) | Complexity azalt, V1 tek sunucu | R2 |
| AD-004 | V1 BackgroundTasks (Celery değil) | Overhead ekleme, V1'de tek worker yeterli | Redis + Celery |

---

## 9. MILESTONE'LAR — YOL HARİTASI

### Milestone 1 — Teknik Doğrulama ← AKTİF (~90% tamamlandı)
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
- [ ] **End-to-end test: gerçek telefon → server → geri**

**Done Kriteri:** Gerçek iPhone'dan video gönder, sessizlikleri kesilmiş hali geri gelsin.

### Milestone 2 — Beta Ready
- Error handling (tüm edge case'ler)
- R2 storage entegrasyonu
- Push notification (APNs)
- Progress reporting (detaylı step bilgisi)
- Basit UI polish
- TestFlight dağıtım

### Milestone 3 — Proje Klasörü
- Stil analizi engine (PySceneDetect + librosa)
- Stil profili kaydetme/yükleme
- Klasör CRUD API
- iOS: klasör yönetimi UI
- Stil bazlı edit üretimi

### Milestone 4 — Müzikli Edit
- Beat detection (librosa)
- Highlight detection (CV2 + motion)
- Müziğe senkronize kesim
- Geçiş efektleri (xfade)
- Müzik kütüphanesi/seçimi

---

## 10. YAPILMAMASI GEREKENLER — DOKUNMA

- Timeline editörü (V4)
- Müzikli edit (V3)
- Ekip paylaşımı (V4)
- Karmaşık UI elementleri (slider, timeline bar)
- ffmpeg-python kütüphanesi
- UIKit (gerekmedikçe, sadece PHPicker wrapper)
- Alamofire, Combine, RxSwift
- iOS'ta video işleme

---

## 11. KODLAMA STANDARTLARI

### Swift / iOS
- SwiftUI only (UIKit yok, gerekmedikçe)
- MVVM pattern: View → ViewModel → Service
- async/await (Combine DEĞİL)
- PHPickerViewController: video seçimi
- URLSession: bare, 3rd party library yok
- @MainActor: ViewModel'lerde UI state güncellemeleri
- Codable: API response parsing, snake_case→camelCase dönüşüm
- Error handling: do-catch + kullanıcıya Türkçe mesaj

### Python / Backend
- Python 3.12+
- Formatter: black
- Linter: ruff
- Type hints: her fonksiyona
- Docstrings: Google style
- Async/await: her I/O işlemi
- Error handling: custom exception class'ları
- Logging: structlog, JSON format
- FFmpeg: subprocess.run(), path'leri tırnak içinde

---

## 12. SIK YAPILAN HATALAR

### iOS
- PHPicker geçici URL'ler expire olur → hemen kopyala
- Background URLSession kullan (app kapansa da upload devam etsin)
- `snake_case` JSON key'leri → Swift'te `CodingKeys` veya `keyDecodingStrategy`

### Backend
- FFmpeg path'lerinde boşluk → tırnak/shlex.quote()
- Video codec: her zaman `libx264 + aac` çıktı ver
- 9:16 format: `scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2`
- Whisper API timeout → 300sn
- Upload'da dosya uzantısı korunmalı (.mov vs .mp4 farkı)

---

## 13. DOCKER DEPLOYMENT

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - ./backend/.env
    volumes:
      - clipflow-storage:/tmp/clipflow
    restart: unless-stopped

volumes:
  clipflow-storage:
```

### Dockerfile (backend/)
- Base: `python:3.12-slim`
- FFmpeg: `apt-get install ffmpeg`
- Port: 8000
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

---

## 14. TEST DURUMU

9 test geçiyor:
- `test_upload.py`: valid mp4, invalid extension, mov accepted
- `test_process.py`: start process, invalid mode, not found, status after submit
- `test_download.py`: not found, valid file

### Bilinen Sorunlar (Yarın fixlenecek)
- Upload route `.mov` dosyasını `.mov` uzantısıyla kaydediyor ama worker `.mp4` bekliyor
- Pydantic v2 `class Config` deprecation warning'i → `model_config = ConfigDict(...)` olmalı

---

## 15. HIZLI BAŞLANGIÇ — Xcode Agent İçin

### Backend'i Çalıştır
```bash
cd backend
source .venv/bin/activate  # veya: python -m venv .venv && pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### iOS Projesini Kur (Xcode'da)
1. File > New > Project > App
2. Product Name: ClipFlow, Bundle ID: com.clipflow.app
3. Interface: SwiftUI, Language: Swift, minimum iOS 17
4. `ios/ClipFlow/` altındaki tüm .swift dosyalarını projeye sürükle
5. Info.plist'teki permission key'lerini projeye ekle
6. `APIService.swift`'te `baseURL`'i Mac'in IP'sine çevir:
   ```swift
   private let baseURL = "http://192.168.1.X:8000/api/v1"
   ```
7. Build & Run (gerçek cihaz veya simulator)

### Test Et
```bash
# Health check
curl http://localhost:8000/health

# Video upload
curl -X POST http://localhost:8000/api/v1/upload -F "file=@test.mp4"

# Process başlat
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"clip_ids": ["FILE_ID"], "mode": "talking_reels"}'

# Status kontrol
curl http://localhost:8000/api/v1/process/JOB_ID
```
