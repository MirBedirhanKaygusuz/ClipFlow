import AVKit
import Photos
import SwiftUI

/// Full-screen video preview with save-to-camera-roll action.
struct PreviewView: View {
    let videoURL: URL
    let stats: ProcessingStats?
    let onDismiss: () -> Void

    @State private var player: AVPlayer?
    @State private var saved = false
    @State private var showError = false

    var body: some View {
        VStack(spacing: 20) {
            if let player {
                VideoPlayer(player: player)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .frame(maxHeight: 400)
            }

            if let stats {
                statsView(stats)
            }

            HStack(spacing: 16) {
                Button {
                    saveToPhotos()
                } label: {
                    Label(saved ? "Kaydedildi" : "Kaydet", systemImage: saved ? "checkmark.circle.fill" : "square.and.arrow.down")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(saved ? .green : .blue)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(saved)

                Button {
                    onDismiss()
                } label: {
                    Label("Yeni Video", systemImage: "plus")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(.secondary.opacity(0.2))
                        .foregroundStyle(.primary)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
            .padding(.horizontal)
        }
        .onAppear {
            player = AVPlayer(url: videoURL)
            player?.play()
        }
        .alert("Kaydetme hatası", isPresented: $showError) {
            Button("Tamam") {}
        }
    }

    private func statsView(_ stats: ProcessingStats) -> some View {
        HStack(spacing: 24) {
            if let pct = stats.silenceRemovedPct {
                statBadge(value: "%\(Int(pct))", label: "Sessizlik kesildi")
            }
            if let segments = stats.segments {
                statBadge(value: "\(segments)", label: "Konuşma parçası")
            }
            if let newDuration = stats.newDuration {
                statBadge(value: "\(Int(newDuration))s", label: "Yeni süre")
            }
        }
        .font(.caption)
    }

    private func statBadge(value: String, label: String) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.title3.bold().monospacedDigit())
            Text(label)
                .foregroundStyle(.secondary)
        }
    }

    private func saveToPhotos() {
        PHPhotoLibrary.requestAuthorization(for: .addOnly) { status in
            guard status == .authorized else {
                DispatchQueue.main.async { showError = true }
                return
            }
            PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: videoURL)
            } completionHandler: { success, _ in
                DispatchQueue.main.async {
                    if success {
                        saved = true
                    } else {
                        showError = true
                    }
                }
            }
        }
    }
}
