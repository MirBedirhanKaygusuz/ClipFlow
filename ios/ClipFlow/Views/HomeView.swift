import SwiftUI

/// Main screen — pick a video, choose quality, start processing.
struct HomeView: View {
    @State private var viewModel = MainViewModel()

    var body: some View {
        NavigationStack {
            ZStack {
                Theme.background.ignoresSafeArea()

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
            }
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
        VStack(spacing: 24) {
            Image(systemName: "video.badge.waveform")
                .font(.system(size: 80))
                .foregroundStyle(Theme.primaryGradient)
                .shadow(color: Theme.neonTeal.opacity(0.3), radius: 20)

            VStack(spacing: 8) {
                Text("ClipFlow'a Hoş Geldin")
                    .font(.title.bold())
                    .foregroundStyle(.white)

                Text("Videolarını yapay zeka ile otomatik kırp\nve hemen paylaşmaya hazır hale getir.")
                    .font(.body)
                    .foregroundStyle(Theme.textSecondary)
                    .multilineTextAlignment(.center)
            }

            Button {
                viewModel.showPicker = true
            } label: {
                Label("Video Seç", systemImage: "plus.circle.fill")
            }
            .buttonStyle(NeonButtonStyle())
            .padding(.horizontal, 40)
            .padding(.top, 16)
        }
    }

    // MARK: - Quality Selection (Binary UX)

    private func qualitySelectView(videoURL: URL) -> some View {
        VStack(spacing: 24) {
            Text("Proje Formatı")
                .font(.title2.bold())
                .foregroundStyle(.white)

            // Option A: Reels / Story
            Button {
                viewModel.startWithQuality(.reels, videoURL: videoURL)
            } label: {
                HStack(spacing: 16) {
                    ZStack {
                        Circle()
                            .fill(Theme.neonPurple.opacity(0.15))
                            .frame(width: 48, height: 48)
                        Image(systemName: "iphone")
                            .font(.system(size: 24))
                            .foregroundStyle(Theme.neonPurple)
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Reels / Story (Dikey)")
                            .font(.headline)
                        Text("1080×1920 · 9:16 · Sosyal Medya")
                            .font(.caption)
                            .foregroundStyle(Theme.textSecondary)
                    }

                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(.secondary)
                }
            }
            .buttonStyle(NeonBorderButtonStyle())
            .padding(.horizontal)

            // Option B: High Quality
            Button {
                viewModel.startWithQuality(.highQuality, videoURL: videoURL)
            } label: {
                HStack(spacing: 16) {
                    ZStack {
                        Circle()
                            .fill(Theme.neonTeal.opacity(0.15))
                            .frame(width: 48, height: 48)
                        Image(systemName: "film.fill")
                            .font(.system(size: 24))
                            .foregroundStyle(Theme.neonTeal)
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Orijinal Kalite")
                            .font(.headline)
                        Text("Orijinal çözünürlük · Kayıpsız · Yatay/Dikey")
                            .font(.caption)
                            .foregroundStyle(Theme.textSecondary)
                    }

                    Spacer()
                    Image(systemName: "chevron.right")
                        .foregroundStyle(.secondary)
                }
            }
            .buttonStyle(NeonBorderButtonStyle())
            .padding(.horizontal)

            // Zoom settings
            VStack(spacing: 8) {
                Toggle(isOn: $viewModel.enableZoom) {
                    HStack(spacing: 8) {
                        Image(systemName: "viewfinder")
                            .foregroundStyle(Theme.neonPurple)
                        Text("Akıllı Zoom")
                            .font(.subheadline)
                            .foregroundStyle(.white)
                    }
                }

                if viewModel.enableZoom {
                    HStack {
                        Text("Yoğunluk")
                            .font(.caption)
                            .foregroundStyle(Theme.textSecondary)
                        Slider(value: $viewModel.zoomIntensity, in: 0.1...1.0, step: 0.1)
                        Text("%\(Int(viewModel.zoomIntensity * 100))")
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(Theme.textSecondary)
                            .frame(width: 36)
                    }
                    Text("Video'daki harekete göre otomatik zoom ve kadraj kırma")
                        .font(.caption2)
                        .foregroundStyle(Theme.textSecondary)
                }
            }
            .padding()
            .background(Theme.surface)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .padding(.horizontal)

            Button("İptal") {
                viewModel.reset()
            }
            .font(.subheadline.bold())
            .foregroundStyle(Theme.textSecondary)
            .padding(.top, 16)
        }
    }

    // MARK: - Progress States

    private var preparingView: some View {
        GlassyCard {
            VStack(spacing: 20) {
                ProgressView()
                    .controlSize(.large)
                    .tint(Theme.neonTeal)
                Text("Video sıkıştırılıyor...")
                    .font(.headline)
                    .foregroundStyle(.white)
            }
            .frame(maxWidth: .infinity)
            .padding(24)
        }
    }

    private func uploadingView(progress: Double) -> some View {
        GlassyCard {
            VStack(spacing: 20) {
                NeonProgressView(progress: progress)
                    .padding(.horizontal)

                HStack {
                    Text("Buluta Yükleniyor...")
                        .font(.headline)
                    Spacer()
                    Text("\(Int(progress * 100))%")
                        .monospacedDigit()
                }
                .foregroundStyle(.white)
                .padding(.horizontal)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 24)
        }
    }

    private func processingView(progress: Int, step: String, eta: Int?) -> some View {
        GlassyCard {
            VStack(spacing: 24) {
                ZStack {
                    Circle()
                        .stroke(Theme.surface, lineWidth: 8)
                        .frame(width: 120, height: 120)

                    Circle()
                        .trim(from: 0, to: CGFloat(progress) / 100.0)
                        .stroke(Theme.primaryGradient, style: StrokeStyle(lineWidth: 8, lineCap: .round))
                        .frame(width: 120, height: 120)
                        .rotationEffect(.degrees(-90))
                        .animation(.easeInOut, value: progress)
                        .shadow(color: Theme.neonPurple.opacity(0.8), radius: 10)

                    Text("%\(progress)")
                        .font(.largeTitle.bold().monospacedDigit())
                        .foregroundStyle(.white)
                }

                VStack(spacing: 6) {
                    Text(localizedStep(step))
                        .font(.headline)
                        .foregroundStyle(.white)

                    if let eta, eta > 0 {
                        Text("~\(etaLabel(eta)) kaldı")
                            .font(.subheadline)
                            .foregroundStyle(Theme.neonTeal)
                    }
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 32)
        }
    }

    private func etaLabel(_ seconds: Int) -> String {
        if seconds >= 60 {
            let m = seconds / 60
            let s = seconds % 60
            return s == 0 ? "\(m)dk" : "\(m)dk \(s)sn"
        }
        return "\(seconds)sn"
    }

    // MARK: - Error

    private func errorView(message: String) -> some View {
        GlassyCard {
            VStack(spacing: 20) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 64))
                    .foregroundStyle(.red)
                    .shadow(color: .red.opacity(0.4), radius: 10)

                Text("Bir Hata Oluştu")
                    .font(.title3.bold())
                    .foregroundStyle(.white)

                Text(message)
                    .font(.subheadline)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(Theme.textSecondary)

                Button("Tekrar Dene") {
                    viewModel.reset()
                }
                .buttonStyle(NeonBorderButtonStyle())
                .padding(.top, 8)
            }
            .frame(maxWidth: .infinity)
            .padding(24)
        }
    }

    // MARK: - Helpers

    private func localizedStep(_ step: String) -> String {
        switch step {
        case "silence_detection": return "Sessizlikler tespit ediliyor..."
        case "cutting": return "Sessizlikler kesiliyor..."
        case "zoom_analysis": return "Akıllı kadraj hesaplanıyor..."
        case "format_conversion": return "9:16 formatına dönüştürülüyor..."
        case "beat_detection": return "Beat'ler tespit ediliyor..."
        case "highlight_detection": return "En iyi anlar bulunuyor..."
        case "beat_sync": return "Beat'lere senkronize ediliyor..."
        case "rendering": return "Video oluşturuluyor..."
        case "music_mixing": return "Müzik ekleniyor..."
        case "finalizing": return "Tamamlanıyor..."
        case "queued": return "Kuyrukta..."
        default: return step
        }
    }
}

#Preview {
    HomeView()
}
