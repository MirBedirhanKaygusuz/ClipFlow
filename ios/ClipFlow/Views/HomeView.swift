import SwiftUI

/// Main screen — pick a video and start processing.
struct HomeView: View {
    @StateObject private var viewModel = MainViewModel()

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Spacer()

                switch viewModel.state {
                case .idle:
                    idleView
                case .uploading(let progress):
                    uploadingView(progress: progress)
                case .processing(let progress, let step):
                    processingView(progress: progress, step: step)
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
                VideoPicker { url in
                    viewModel.handleSelectedVideo(url: url)
                }
            }
        }
    }

    // MARK: - Subviews

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

    private func uploadingView(progress: Double) -> some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)
            Text("Yükleniyor...")
                .font(.headline)
        }
    }

    private func processingView(progress: Int, step: String) -> some View {
        VStack(spacing: 16) {
            ProgressView(value: Double(progress), total: 100)
                .progressViewStyle(.linear)
                .padding(.horizontal, 40)

            Text("%\(progress)")
                .font(.largeTitle.bold().monospacedDigit())

            Text(localizedStep(step))
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }

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
