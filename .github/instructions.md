# ClipFlow — Xcode Coding Intelligence Instructions

## Proje Özeti
ClipFlow, AI destekli iOS video editörüdür. iOS tarafı **thin client** — tüm video işleme Python backend'de yapılır.

## Mimari Kurallar — MUTLAKA UY
- iOS = thin client. ASLA iOS'ta video işleme yapma
- MVVM pattern: View → ViewModel → Service → API
- SwiftUI only (UIKit sadece PHPicker wrapper için)
- async/await kullan, Combine KULLANMA
- URLSession kullan, Alamofire/3rd party KULLANMA
- @MainActor: tüm ViewModel'lerde

## API Base URL
Development: `http://<mac-ip>:8000/api/v1`

## API Endpoint'ler
```
POST /upload          → multipart/form-data, file field, returns {file_id, size_mb}
POST /process         → JSON {clip_ids, mode, settings}, returns {job_id, estimated_seconds}
GET  /process/{id}    → Polling, returns {status, progress, step, output_url, stats}
GET  /download/{id}   → Binary video stream
GET  /health          → {status: "ok"}
```

## Status Enum
queued → processing → done | failed | awaiting_decision

## Processing Steps
silence_detection → cutting → format_conversion → completed

## JSON Convention
Backend: snake_case → iOS: `JSONDecoder.keyDecodingStrategy = .convertFromSnakeCase`

## iOS Dosya Yapısı
```
Models/APIModels.swift       → Codable struct'lar
ViewModels/MainViewModel.swift → AppState enum, iş akışı
Views/HomeView.swift          → State-driven ana ekran
Views/VideoPicker.swift       → PHPicker wrapper
Views/PreviewView.swift       → AVPlayer + stats
Services/APIService.swift     → actor, network calls
```

## AppState Pattern
```swift
enum AppState {
    case idle
    case uploading(progress: Double)
    case processing(progress: Int, step: String)
    case done(videoURL: URL, stats: ProcessingStats)
    case error(String)
}
```

## Kodlama Standartları
- Türkçe UI metinleri
- Error handling: do-catch, kullanıcıya anlamlı mesaj
- PHPicker temp URL'leri expire olur → hemen kopyala
- Upload timeout: 300sn (büyük videolar)
- Polling: 2sn aralıkla Task.sleep

## YAPMA
- iOS'ta video işleme
- Combine/RxSwift
- 3rd party dependency
- Timeline/slider UI (V4'te)
- Müzikli edit (V3'te)
- Karmaşık UI elementleri

## Detaylı Bilgi
Tam proje briefing'i: `XCODE-AGENT-BRIEFING.md`
API kontratı detayı: `.claude/skills/api-integration/SKILL.md`
iOS pattern'leri: `.claude/skills/ios-swiftui/SKILL.md`
