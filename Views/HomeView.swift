import SwiftUI

/// Main screen — pick a video, choose quality, start processing.
struct HomeView: View {
    @State private var viewModel = MainViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Spacer()

                switch viewModel.state {
                case .idle:
                    idleView
                case .preparing:
                    preparingView
                case .qualitySelect(let videoURL):
                    qualitySelectView(videoURL: videoURL)
                case .uploading(let progress):
                    uploadingView(progress: progress)
                case .processing(let progress, let step, let eta):
                    processingView(progress: progress, step: step, eta: eta)
                case .done(let localURL, let stats):
                    PreviewView(videoURL: localURL, stats: stats) {
                        viewModel.reset()
                    }
                case .error(let message):
                    errorView(message: message)
                }

                Spacer()
            }
            .padding()
            .navigationTitle("ClipFlow")
            .sheet(isPresented: $viewModel.showPicker) {
                VideoPicker(
                    onPreparing: { viewModel.videoSelectionStarted() },
                    onSelect:    { url in viewModel.handleSelectedVideo(url: url) },
                    onError:     { msg in viewModel.handlePickerError(msg) }
                )
            }
        }
    }

    // MARK: - Idle

    private var idleView: some View {
        VStack(spacing: 16) {
            Image(systemName: "video.badge.waveform")
                .font(.system(size: 64))
                .foregroundStyle(.blue)

            Text("Sessizlikleri otomatik kes")
                .font(.headline)
                .foregroundStyle(.secondary)

            Button {
                viewModel.showPicker = true
            } label: {
                Label("Video Seç", systemImage: "photo.on.rectangle")
                    .font(.title3.bold())
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(.blue)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
            }
            .padding(.horizontal, 40)
        }
    }

    // MARK: - Quality Selection (Binary UX)

    private func qualitySelectView(videoURL: URL) -> some View {
        VStack(spacing: 24) {
            Text("Ne için kullanacaksın?")
                .font(.title2.bold())

            // Option A: Reels / Story
            Button {
                viewModel.startWithQuality(.reels, videoURL: videoURL)
            } label: {
                HStack(spacing: 16) {
                    Image(systemName: "sparkles.rectangle.stack")
                        .font(.system(size: 32))
                        .frame(width: 48)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Reels / Story")
                            .font(.headline)
                        Text("1080×1920 · 9:16 · Instagram için optimize")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    Image(systemName: "chevron.right")
                        .foregroundStyle(.secondary)
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(.blue.opacity(0.1))
                .foregroundStyle(.primary)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }

            // Option B: High Quality
            Button {
                viewModel.startWithQuality(.highQuality, videoURL: videoURL)
            } label: {
                HStack(spacing: 16) {
                    Image(systemName: "film")
                        .font(.system(size: 32))
                        .frame(width: 48)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Yüksek Kalite")
                            .font(.headline)
                        Text("Orijinal çözünürlük · Kayıpsız · YouTube, arşiv")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    Image(systemName: "chevron.right")
                        .foregroundStyle(.secondary)
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(.orange.opacity(0.1))
                .foregroundStyle(.primary)
                .clipShape(RoundedRectangle(cornerRadius: 14))
            }

            Button("Vazgeç") {
                viewModel.reset()
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal)
    }

    // MARK: - Progress States

    private var preparingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)
            Text("Video hazırlanıyor...")
                .font(.headline)
                .foregroundStyle(.secondary)
        }
    }

    private func uploadingView(progress: Double) -> some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)
            Text("Yükleniyor...")
                .font(.headline)
        }
    }

    private func processingView(progress: Int, step: String, eta: Double?) -> some View {
        VStack(spacing: 16) {
            ProgressView(value: Double(progress), total: 100)
                .progressViewStyle(.linear)
                .padding(.horizontal, 40)

            Text("%\(progress)")
                .font(.largeTitle.bold().monospacedDigit())

            Text(localizedStep(step))
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if let eta, eta > 0 {
                Text("Tahmini süre: \(Int(eta)) saniye")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .monospacedDigit()
            }
        }
    }

    // MARK: - Error

    private func errorView(message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundStyle(.red)

            Text(message)
                .font(.subheadline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)

            Button("Tekrar Dene") {
                viewModel.reset()
            }
            .buttonStyle(.borderedProminent)
        }
    }

    // MARK: - Helpers

    private func localizedStep(_ step: String) -> String {
        switch step {
        case "silence_detection": return "Sessizlikler tespit ediliyor..."
        case "cutting": return "Sessizlikler kesiliyor..."
        case "format_conversion": return "9:16 formatına dönüştürülüyor..."
        case "queued": return "Kuyrukta..."
        default: return step
        }
    }
}

#Preview {
    HomeView()
}
