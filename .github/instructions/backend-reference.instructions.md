# Backend API Referansı (iOS Geliştirici İçin)

iOS kodu yazarken backend'in ne döndüğünü bilmen gerekir.

## Endpoint Dosyaları (oku, anlam çıkar)
- `backend/app/api/routes/upload.py` → Upload endpoint implementasyonu
- `backend/app/api/routes/process.py` → Process + status endpoint'leri
- `backend/app/api/routes/download.py` → Download endpoint
- `backend/app/models/job.py` → JobStatus enum, ProcessRequest, StatusResponse tanımları
- `backend/app/config.py` → Backend ayarları (max upload size, preset vs.)

## Response Format Örnekleri

Upload başarılı: `{"file_id": "abc-123", "size_mb": 15.2}`
Process başlatıldı: `{"job_id": "xyz-789", "estimated_seconds": 90}`
Status (işleniyor): `{"status": "processing", "progress": 45, "step": "cutting"}`
Status (bitti): `{"status": "done", "progress": 100, "output_url": "/download/result-id", "stats": {...}}`

## iOS'ta Karşılığı
Her backend response'un iOS'ta bir Codable struct'ı var → `Models/APIModels.swift`
Her endpoint'in iOS'ta bir fonksiyonu var → `Services/APIService.swift`
