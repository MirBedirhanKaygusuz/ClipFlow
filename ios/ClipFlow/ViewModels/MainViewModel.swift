import Foundation
import Observation

/// Main view model — manages the entire V1 flow:
/// video select → quality pick → upload → process → poll → preview
@Observable
@MainActor
final class MainViewModel {

    enum AppState {
        case idle
        case preparing                                  // Video seçildi, kopyalanıyor
        case qualitySelect(videoURL: URL)               // Kalite seçimi bekliyor
        case uploading(progress: Double)
        case processing(progress: Int, step: String, eta: Int?)  // eta = kalan saniye
        case done(localURL: URL, stats: ProcessingStats?)
        case error(message: String)
    }

    var state: AppState = .idle
    var showPicker = false

    // Zoom settings (user-configurable)
    var enableZoom = false
    var zoomIntensity = 0.5

    private let api = APIService.shared
    private var currentJobId: String?
    private var selectedQuality: QualityMode = .reels

    // MARK: - Actions

    /// Called immediately when user picks a video (before URL is ready).
    func videoSelectionStarted() {
        showPicker = false
        state = .preparing
    }

    /// Called when the video URL is ready — show quality selection.
    func handleSelectedVideo(url: URL) {
        state = .qualitySelect(videoURL: url)
    }

    /// Called if video preparation fails.
    func handlePickerError(_ message: String) {
        state = .error(message: message)
    }

    /// User picked a quality mode — start processing pipeline.
    func startWithQuality(_ quality: QualityMode, videoURL: URL) {
        selectedQuality = quality
        Task {
            await processVideo(url: videoURL, quality: quality)
        }
    }

    /// Reset to initial state.
    func reset() {
        state = .idle
        currentJobId = nil
        selectedQuality = .reels
        enableZoom = false
        zoomIntensity = 0.5
    }

    // MARK: - Pipeline

    private func processVideo(url: URL, quality: QualityMode) async {
        do {
            // Step 1: Upload
            state = .uploading(progress: 0)
            let uploadResult = try await api.upload(videoURL: url)
            state = .uploading(progress: 1.0)

            // Step 2: Start processing with quality
            state = .processing(progress: 0, step: "queued", eta: nil)
            let processResult = try await api.startProcessing(
                clipIds: [uploadResult.fileId],
                quality: quality,
                enableZoom: enableZoom,
                zoomIntensity: zoomIntensity
            )
            currentJobId = processResult.jobId

            // Step 3: Poll until done
            try await pollUntilDone(jobId: processResult.jobId)

        } catch {
            state = .error(message: error.localizedDescription)
        }
    }

    private func pollUntilDone(jobId: String) async throws {
        while true {
            let status = try await api.getStatus(jobId: jobId)

            switch status.status {
            case "done":
                guard let outputUrl = status.outputUrl else {
                    throw APIError.invalidResponse
                }
                let fileId = outputUrl.replacingOccurrences(of: "/api/v1/download/", with: "")
                let localURL = try await api.downloadVideo(fileId: fileId)
                state = .done(localURL: localURL, stats: status.stats)
                return

            case "failed":
                state = .error(message: "İşlem başarısız: \(status.step)")
                return

            default:
                state = .processing(progress: status.progress, step: status.step, eta: status.etaSeconds)
                try await Task.sleep(nanoseconds: 2_000_000_000) // 2 saniye
            }
        }
    }
}
