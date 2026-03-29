# API Integration — iOS ↔ Backend Kontratı

Bu skill, iOS ve Backend arasındaki tüm iletişimi tanımlar.
Herhangi bir tarafta değişiklik yaparken bu kontratı referans al.

## Base URL
- Development: `http://<mac-ip>:8000/api/v1`
- Production: `https://api.clipflow.app/api/v1`

## Endpoint'ler

### 1. POST /upload
**iOS tarafı:**
```swift
// multipart/form-data ile video gönder
// boundary: UUID().uuidString
// field name: "file"
// Content-Type: video/mp4 veya video/quicktime
```

**Backend tarafı:**
```python
@router.post("/upload")
async def upload_file(file: UploadFile):
    # Allowed: .mp4, .mov, .m4v
    # Max size: settings.max_upload_size_mb (default 500)
    # Returns: {"file_id": "uuid", "size_mb": 12.5}
```

**Response mapping:**
```
Backend JSON          →  iOS Codable
─────────────────────────────────────
file_id               →  fileId (String)
size_mb               →  sizeMb (Double)
```

### 2. POST /process
**iOS tarafı:**
```swift
let body: [String: Any] = [
    "clip_ids": [fileId],           // upload'dan dönen file_id
    "mode": "talking_reels",        // V1'de tek mod
    "settings": [
        "output_format": "9:16",
        "add_captions": true
    ],
    "device_token": apnsToken       // opsiyonel, push için
]
```

**Backend tarafı:**
```python
class ProcessRequest(BaseModel):
    clip_ids: list[str]
    mode: str = "talking_reels"
    settings: dict = {"output_format": "9:16", "add_captions": True}
    device_token: str | None = None
```

**Response mapping:**
```
Backend JSON          →  iOS Codable
─────────────────────────────────────
job_id                →  jobId (String)
estimated_seconds     →  estimatedSeconds (Int)
```

### 3. GET /process/{job_id} — Polling
**iOS tarafı:** 2sn aralıklarla çağır, switch on status:

```swift
switch status.status {
case "queued":              // Kuyrukta, bekle
case "processing":          // İşleniyor, progress göster
case "awaiting_decision":   // Karar gerekli, options göster
case "done":                // Bitti, output_url'den indir
case "failed":              // Hata
}
```

**Backend tarafı:**
```python
class StatusResponse(BaseModel):
    status: JobStatus           # queued|processing|awaiting_decision|done|failed
    progress: int = 0           # 0-100
    step: str = ""              # silence_detection|cutting|format_conversion|completed
    output_url: str | None      # done olunca: "/download/{file_id}"
    question: str | None        # awaiting_decision olunca
    options: list[str] | None   # awaiting_decision olunca: ["Seçenek A", "Seçenek B"]
    stats: dict | None          # done olunca: istatistikler
```

**Stats mapping (done durumunda):**
```
Backend JSON              →  iOS Codable
─────────────────────────────────────────
original_duration         →  originalDuration (Double?)
new_duration              →  newDuration (Double?)
silence_removed_pct       →  silenceRemovedPct (Double?)
segments                  →  segments (Int?)
```

### 4. POST /process/{job_id}/decision
**iOS tarafı:**
```swift
// awaiting_decision durumunda, kullanıcı seçim yaptığında
// choice: 0 veya 1 (options array'indeki index)
```

### 5. GET /download/{file_id}
**iOS tarafı:**
```swift
// URLSession.shared.download(from:) kullan
// Response: raw video/mp4 binary
// Temp file'a kaydet, sonra AVPlayer'a ver
```

## JSON Decoding Stratejisi
Backend snake_case, iOS camelCase kullanır. Tek bir decoder yeterli:

```swift
extension JSONDecoder {
    static let snakeCase: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()
}
```

## Error Handling Kontratı
Backend hata döndüğünde:
```json
{"error": "Türkçe hata mesajı"}
```

iOS'ta:
```swift
enum APIError: LocalizedError {
    case invalidResponse
    case serverError(Int)           // HTTP status code
    case decodingFailed

    var errorDescription: String? {
        switch self {
        case .invalidResponse: return "Sunucu yanıt vermedi"
        case .serverError(let code): return "Sunucu hatası: \(code)"
        case .decodingFailed: return "Yanıt okunamadı"
        }
    }
}
```

## Processing Pipeline Steps (sırayla)
```
1. queued              → "Kuyrukta..."
2. silence_detection   → "Sessizlikler tespit ediliyor..."
3. cutting             → "Video kesiliyor..."
4. format_conversion   → "Format dönüştürülüyor..."
5. completed           → "Tamamlandı!"
```

## Dikkat Edilecekler
- Upload'da timeout yüksek tut (büyük videolar): 300sn
- Polling'de Task.sleep kullan, Timer DEĞİL
- Download edilen dosyayı temp directory'de tut, kullanıcı kaydedince Photos'a taşı
- output_url relative path döner ("/download/xxx"), baseURL ile birleştir
- Backend Türkçe hata mesajları döner, direkt UI'da gösterilebilir
