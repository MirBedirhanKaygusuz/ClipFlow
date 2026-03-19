# ClipFlow API Specification — V1

Base URL: `https://api.clipflow.app/api/v1`

## POST /upload
Dosya yükleme (video veya müzik).

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | binary | Yes | MP4, MOV, M4V dosyası |
| type | string | No | "clip" (default), "reference", "music" |

**Response:** `200 OK`
```json
{"file_id": "uuid-string"}
```

**Errors:**
- 400: Geçersiz format
- 413: Dosya çok büyük (>500MB)

---

## POST /process
Video işleme başlat.

**Request:**
```json
{
  "clip_ids": ["uuid1", "uuid2"],
  "mode": "talking_reels",
  "settings": {
    "output_format": "9:16",
    "add_captions": true,
    "silence_threshold_db": -30,
    "min_silence_duration": 0.3
  },
  "device_token": "apns-token-string"
}
```

**Response:** `202 Accepted`
```json
{"job_id": "uuid", "estimated_seconds": 90}
```

---

## GET /process/{job_id}
İşleme durumu sorgula.

**Response Variants:**

Processing:
```json
{"status": "processing", "progress": 65, "step": "silence_detection"}
```

Binary karar bekliyor:
```json
{
  "status": "awaiting_decision",
  "question": "Hangi tempo?",
  "options": ["Hızlı (28 kesim/dk)", "Sakin (12 kesim/dk)"]
}
```

Tamamlandı:
```json
{
  "status": "done",
  "output_url": "https://..../result.mp4",
  "stats": {"duration": 42, "cuts": 23, "silence_removed_pct": 38}
}
```

---

## POST /process/{job_id}/decision
Binary karar gönder.

**Request:**
```json
{"choice": 0}
```

---

## GET /download/{file_id}
İşlenmiş video indir.

**Response:** Video dosyası (binary stream)
