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
        ZStack {
            Theme.background.ignoresSafeArea()

            VStack(spacing: 24) {
                if let player = player {
                    VideoPlayer(player: player)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                        .overlay(
                            RoundedRectangle(cornerRadius: 16)
                                .stroke(Theme.surface, lineWidth: 2)
                        )
                        .shadow(color: .black.opacity(0.5), radius: 20, y: 10)
                        .frame(maxHeight: UIScreen.main.bounds.height * 0.5)
                }

                if let stats = stats {
                    GlassyCard {
                        statsView(stats)
                    }
                }

                Spacer()

                VStack(spacing: 16) {
                    Button {
                        saveToPhotos()
                    } label: {
                        Label(saved ? "Galeriye Kaydedildi" : "Galeriye Kaydet", systemImage: saved ? "checkmark.circle.fill" : "square.and.arrow.down")
                    }
                    .buttonStyle(NeonButtonStyle(isGlowing: !saved))
                    .disabled(saved)

                    Button {
                        onDismiss()
                    } label: {
                        Label("Yeni Video İşle", systemImage: "plus")
                    }
                    .buttonStyle(NeonBorderButtonStyle())
                }
                .padding(.horizontal)
                .padding(.bottom, 20)
            }
            .padding()
        }
        .onAppear {
            player = AVPlayer(url: videoURL)
            player?.play()
        }
        .alert("Kaydetme hatası", isPresented: $showError) {
            Button("Tamam", role: .cancel) {}
        }
    }

    private func statsView(_ stats: ProcessingStats) -> some View {
        HStack {
            Spacer()
            if let pct = stats.silenceRemovedPct {
                statBadge(value: "%\(Int(pct))", label: "Kısaltılma")
            }
            Spacer()
            if let segments = stats.segments {
                statBadge(value: "\(segments)", label: "Parça")
            }
            Spacer()
            if let newDuration = stats.newDuration {
                statBadge(value: "\(Int(newDuration))s", label: "Kalan Süre")
            }
            Spacer()
        }
        .padding(.vertical, 8)
    }

    private func statBadge(value: String, label: String) -> some View {
        VStack(spacing: 6) {
            Text(value)
                .font(.title2.bold().monospacedDigit())
                .foregroundStyle(Theme.neonTeal)
            Text(label)
                .font(.caption)
                .foregroundStyle(Theme.textSecondary)
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
