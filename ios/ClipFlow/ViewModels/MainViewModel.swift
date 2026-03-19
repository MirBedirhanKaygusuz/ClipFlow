import Foundation
import SwiftUI

/// Main view model — manages the entire V1 flow:
/// video select → upload → process → poll → preview
@MainActor
final class MainViewModel: ObservableObject {

    enum AppState: Equatable {
        case idle
        case uploading(progress: Double)
        case processing(progress: Int, step: String)
        case done(localURL: URL, stats: ProcessingStats?)
        case error(message: String)
    }

    @Published var state: AppState = .idle
    @Published var showPicker = false

    private let api = APIService.shared
    private var currentJobId: String?

    // MARK: - Actions

    /// Called when user picks a video from PHPicker.
    func handleSelectedVideo(url: URL) {
        Task {
            await processVideo(url: url)
        }
    }

    /// Reset to initial state.
    func reset() {
        state = .idle
        currentJobId = nil
    }

    // MARK: - Pipeline

    private func processVideo(url: URL) async {
        do {
            // Step 1: Upload
            state = .uploading(progress: 0)
            let uploadResult = try await api.upload(videoURL: url)
            state = .uploading(progress: 1.0)

            // Step 2: Start processing
            state = .processing(progress: 0, step: "Kuyrukta...")
            let processResult = try await api.startProcessing(clipIds: [uploadResult.fileId])
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
                // Extract file_id from URL path: /api/v1/download/{file_id}
                let fileId = outputUrl.replacingOccurrences(of: "/api/v1/download/", with: "")
                let localURL = try await api.downloadVideo(fileId: fileId)
                state = .done(localURL: localURL, stats: status.stats)
                return

            case "failed":
                state = .error(message: "İşlem başarısız: \(status.step)")
                return

            default:
                state = .processing(progress: status.progress, step: status.step)
                try await Task.sleep(nanoseconds: 2_000_000_000) // 2 saniye
            }
        }
    }
}
