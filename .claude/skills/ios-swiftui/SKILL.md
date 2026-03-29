# iOS — Swift + SwiftUI Patterns for ClipFlow

ClipFlow iOS tarafı thin client. Kompleks iş mantığı YAPMA, sadece:
video seç → upload → polling → preview → kaydet.

## Mimari: MVVM
```
Views/          → SwiftUI ekranlar (UI only, logic yok)
ViewModels/     → @MainActor ObservableObject class'ları (state + logic)
Services/       → actor class'lar (Network, storage, notification)
Models/         → Codable struct'lar (API response)
```

### Katman Kuralları
- View: sadece UI render, @StateObject veya @EnvironmentObject ile ViewModel bağla
- ViewModel: @Published state, business logic, Service çağırır
- Service: actor, URLSession, tek sorumluluk (APIService, StorageService vs.)
- Model: Codable, immutable struct

## Video Seçimi — PHPickerViewController
```swift
import PhotosUI
import SwiftUI

struct VideoPicker: UIViewControllerRepresentable {
    @Binding var selectedURL: URL?
    @Environment(\.dismiss) private var dismiss

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration()
        config.selectionLimit = 1
        config.filter = .videos
        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uvc: PHPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let parent: VideoPicker

        init(_ parent: VideoPicker) { self.parent = parent }

        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            parent.dismiss()
            guard let provider = results.first?.itemProvider,
                  provider.hasItemConformingToTypeIdentifier(UTType.movie.identifier) else { return }

            // ÖNEMLİ: PHPicker temp URL'leri expire olur — hemen kopyala!
            provider.loadFileRepresentation(forTypeIdentifier: UTType.movie.identifier) { url, error in
                guard let url else { return }
                let dest = FileManager.default.temporaryDirectory
                    .appendingPathComponent(UUID().uuidString + ".mov")
                try? FileManager.default.copyItem(at: url, to: dest)
                DispatchQueue.main.async {
                    self.parent.selectedURL = dest
                }
            }
        }
    }
}
```

## AppState Pattern — Tüm UI Bu Enum'a Bağlı
```swift
@MainActor
final class MainViewModel: ObservableObject {
    enum AppState {
        case idle
        case uploading(progress: Double)
        case processing(progress: Int, step: String)
        case done(videoURL: URL, stats: ProcessingStats)
        case error(String)
    }

    @Published var state: AppState = .idle
    @Published var showPicker = false

    private let api = APIService()

    func handleSelectedVideo(_ url: URL) {
        Task {
            do {
                state = .uploading(progress: 0)
                let uploadRes = try await api.upload(videoURL: url)

                state = .processing(progress: 0, step: "Kuyrukta...")
                let processRes = try await api.startProcessing(fileId: uploadRes.fileId)

                try await pollUntilDone(jobId: processRes.jobId)
            } catch {
                state = .error(error.localizedDescription)
            }
        }
    }

    private func pollUntilDone(jobId: String) async throws {
        while true {
            let status = try await api.getStatus(jobId: jobId)
            switch status.status {
            case "done":
                guard let outputUrl = status.outputUrl else { throw APIError.invalidResponse }
                let fileId = URL(string: outputUrl)!.lastPathComponent
                let localURL = try await api.downloadVideo(fileId: fileId)
                state = .done(videoURL: localURL, stats: status.stats ?? ProcessingStats())
                return
            case "failed":
                state = .error("İşleme başarısız oldu")
                return
            case "awaiting_decision":
                // UI'da binary seçenek göster
                return
            default:
                state = .processing(
                    progress: status.progress ?? 0,
                    step: localizedStep(status.step ?? "")
                )
                try await Task.sleep(nanoseconds: 2_000_000_000) // 2sn
            }
        }
    }

    func localizedStep(_ step: String) -> String {
        switch step {
        case "silence_detection": return "Sessizlikler tespit ediliyor..."
        case "cutting": return "Video kesiliyor..."
        case "format_conversion": return "Format dönüştürülüyor..."
        case "completed": return "Tamamlandı!"
        default: return step
        }
    }
}
```

## Network — APIService (actor)
```swift
actor APIService {
    private let baseURL = "http://localhost:8000/api/v1"

    // Multipart upload
    func upload(videoURL: URL) async throws -> UploadResponse {
        let url = URL(string: "\(baseURL)/upload")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let data = try createMultipartBody(videoURL: videoURL, boundary: boundary)
        let (responseData, response) = try await URLSession.shared.upload(for: request, from: data)
        try validateResponse(response)
        return try JSONDecoder.snakeCase.decode(UploadResponse.self, from: responseData)
    }

    // JSON POST
    func startProcessing(fileId: String) async throws -> ProcessResponse {
        let url = URL(string: "\(baseURL)/process")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = [
            "clip_ids": [fileId],
            "mode": "talking_reels",
            "settings": ["output_format": "9:16", "add_captions": true]
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)
        return try JSONDecoder.snakeCase.decode(ProcessResponse.self, from: data)
    }

    // GET polling
    func getStatus(jobId: String) async throws -> StatusResponse {
        let url = URL(string: "\(baseURL)/process/\(jobId)")!
        let (data, response) = try await URLSession.shared.data(from: url)
        try validateResponse(response)
        return try JSONDecoder.snakeCase.decode(StatusResponse.self, from: data)
    }

    // Download
    func downloadVideo(fileId: String) async throws -> URL {
        let url = URL(string: "\(baseURL)/download/\(fileId)")!
        let (tempURL, response) = try await URLSession.shared.download(from: url)
        try validateResponse(response)
        let dest = FileManager.default.temporaryDirectory
            .appendingPathComponent("\(fileId).mp4")
        try? FileManager.default.removeItem(at: dest)
        try FileManager.default.moveItem(at: tempURL, to: dest)
        return dest
    }
}

// Helper: snake_case JSON decoder
extension JSONDecoder {
    static let snakeCase: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()
}
```

## Camera Roll'a Kaydetme
```swift
import Photos

func saveToPhotos(url: URL) async throws {
    let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
    guard status == .authorized else { throw ClipFlowError.permissionDenied }

    try await PHPhotoLibrary.shared().performChanges {
        PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: url)
    }
}
```

## Video Preview — AVPlayer
```swift
import AVKit
import SwiftUI

struct PreviewView: View {
    let videoURL: URL
    let stats: ProcessingStats
    let onSave: () -> Void
    let onNewVideo: () -> Void

    @State private var player: AVPlayer?

    var body: some View {
        VStack(spacing: 16) {
            if let player {
                VideoPlayer(player: player)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            }

            // Stats
            HStack {
                StatBadge(label: "Sessizlik", value: "\(Int(stats.silenceRemovedPct ?? 0))%")
                StatBadge(label: "Segment", value: "\(stats.segments ?? 0)")
                StatBadge(label: "Süre", value: "\(Int(stats.newDuration ?? 0))s")
            }

            HStack(spacing: 12) {
                Button("Kaydet") { onSave() }
                    .buttonStyle(.borderedProminent)
                Button("Yeni Video") { onNewVideo() }
                    .buttonStyle(.bordered)
            }
        }
        .onAppear {
            player = AVPlayer(url: videoURL)
            player?.play()
        }
    }
}
```

## Push Notification Setup (V2)
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
- Türkçe UI metinleri

## SwiftUI Ekran Listesi (V1)
1. **HomeView** — Video seç butonu (idle state)
2. **UploadingView** — Progress bar + yükleniyor text
3. **ProcessingView** — Progress bar + adım bilgisi
4. **PreviewView** — AVPlayer + stats + kaydet/yeni video butonları
5. **ErrorView** — Hata mesajı + tekrar dene butonu

## İzinler (Info.plist)
```xml
<key>NSPhotoLibraryUsageDescription</key>
<string>ClipFlow video seçmek ve kaydetmek için fotoğraf kütüphanenize erişir.</string>
<key>NSPhotoLibraryAddUsageDescription</key>
<string>ClipFlow işlenmiş videoları kamera rulonuza kaydetmek ister.</string>
```
