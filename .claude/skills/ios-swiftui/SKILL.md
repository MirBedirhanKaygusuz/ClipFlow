# iOS — Swift + SwiftUI Patterns for ClipFlow

ClipFlow iOS tarafı thin client. Kompleks iş mantığı YAPMA, sadece:
video seç → upload → polling → preview → kaydet.

## Mimari: MVVM
```
Views/          → SwiftUI ekranlar (UI only, logic yok)
ViewModels/     → ObservableObject class'ları (state + logic)
Services/       → Network, storage, notification
Models/         → Codable struct'lar (API response)
```

## Video Seçimi — PHPickerViewController
```swift
import PhotosUI
import SwiftUI

struct VideoPicker: UIViewControllerRepresentable {
    @Binding var selectedURLs: [URL]

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration()
        config.selectionLimit = 10
        config.filter = .videos
        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }

    // Coordinator'da:
    // result.itemProvider.loadFileRepresentation(forTypeIdentifier: UTType.movie.identifier)
    // → geçici URL al, kopyala, selectedURLs'e ekle
}
```

## Network — URLSession (Background Upload)
```swift
class UploadService {
    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.background(withIdentifier: "com.clipflow.upload")
        config.isDiscretionary = false
        config.sessionSendsLaunchEvents = true
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }()

    func upload(videoURL: URL) async throws -> String {
        var request = URLRequest(url: URL(string: "\(baseURL)/upload")!)
        request.httpMethod = "POST"
        // multipart/form-data body oluştur
        let task = session.uploadTask(with: request, fromFile: videoURL)
        task.resume()
        // delegate ile progress ve completion takip et
    }
}
```

## Polling Pattern
```swift
func pollStatus(jobId: String) async throws -> JobStatus {
    while true {
        let status = try await api.getStatus(jobId: jobId)
        switch status.status {
        case "done":
            return status
        case "awaiting_decision":
            return status  // UI'da binary seçenek göster
        case "failed":
            throw ClipFlowError.processingFailed(status.error ?? "")
        default:
            try await Task.sleep(nanoseconds: 2_000_000_000) // 2sn
        }
    }
}
```

## Camera Roll'a Kaydetme
```swift
import Photos

func saveToPhotos(url: URL) async throws {
    try await PHPhotoLibrary.shared().performChanges {
        PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: url)
    }
}
```

## Push Notification Setup
```swift
// AppDelegate'de:
UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { granted, _ in }
UIApplication.shared.registerForRemoteNotifications()

// Token'ı backend'e gönder:
func application(_ app: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken token: Data) {
    let tokenString = token.map { String(format: "%02x", $0) }.joined()
    // POST /register-device { "token": tokenString }
}
```

## UI Kuralları — Binary UX
- Her karar noktasında MAKSIMUM 2 seçenek sun
- Slider, timeline, karmaşık ayar menüsü YOK
- AI önerir, kullanıcı onaylar veya alternatifi seçer
- Boş ekran ASLA gösterme — her zaman bir öneri olsun

## SwiftUI Ekran Listesi (V1)
1. **HomeView** — Proje klasörleri listesi + son editler
2. **ProjectFolderView** — Klasör içeriği + yeni edit başlat
3. **ModeSelectView** — "Konuşmalı Reels" veya "Müzikli Edit" (V1'de sadece konuşmalı)
4. **VideoPickerView** — Camera Roll'dan seç
5. **ProcessingView** — Progress bar + tahmini süre
6. **PreviewView** — AVPlayer ile full-screen preview
7. **ShareView** — Camera Roll kaydet / paylaş
