import SwiftUI

/// View for selecting a music track and starting a musical edit.
/// Shows the user's uploaded music library and allows uploading new tracks.
struct MusicPickerView: View {
    let videoFileId: String
    let quality: QualityMode
    let onStart: (String, String, Double) -> Void // musicId, transition, duration
    let onCancel: () -> Void

    @State private var tracks: [MusicTrack] = []
    @State private var selectedTrackId: String?
    @State private var isLoading = false
    @State private var isUploading = false
    @State private var transition = "fade"
    @State private var transitionDuration = 0.5
    @State private var showFilePicker = false
    @State private var errorMessage: String?

    private let api = APIService.shared
    private let transitions = ["fade", "wipeleft", "wiperight", "slideup", "slidedown"]

    var body: some View {
        NavigationStack {
            List {
                // MARK: - Music Library
                Section("Müzik Kütüphanesi") {
                    if isLoading {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                    } else if tracks.isEmpty {
                        Text("Henüz müzik yüklenmemiş")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(tracks, id: \.id) { track in
                            trackRow(track)
                        }
                    }

                    Button {
                        showFilePicker = true
                    } label: {
                        Label(
                            isUploading ? "Yükleniyor..." : "Müzik Yükle",
                            systemImage: "plus.circle"
                        )
                    }
                    .disabled(isUploading)
                }

                // MARK: - Transition Settings
                Section("Geçiş Efekti") {
                    Picker("Geçiş Tipi", selection: $transition) {
                        ForEach(transitions, id: \.self) { t in
                            Text(localizedTransition(t)).tag(t)
                        }
                    }

                    HStack {
                        Text("Süre")
                        Slider(value: $transitionDuration, in: 0.2...2.0, step: 0.1)
                        Text("\(transitionDuration, specifier: "%.1f")s")
                            .monospacedDigit()
                            .frame(width: 40)
                    }
                }

                // MARK: - Error
                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("Müzikli Edit")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Vazgeç", action: onCancel)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Başla") {
                        if let id = selectedTrackId {
                            onStart(id, transition, transitionDuration)
                        }
                    }
                    .disabled(selectedTrackId == nil)
                    .bold()
                }
            }
            .task {
                await loadTracks()
            }
        }
    }

    // MARK: - Track Row

    private func trackRow(_ track: MusicTrack) -> some View {
        Button {
            selectedTrackId = track.id
        } label: {
            HStack {
                Image(systemName: selectedTrackId == track.id ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selectedTrackId == track.id ? .blue : .secondary)

                VStack(alignment: .leading, spacing: 2) {
                    Text(track.filename)
                        .font(.body)
                        .foregroundStyle(.primary)

                    HStack(spacing: 8) {
                        if let tempo = track.tempo {
                            Text("\(Int(tempo)) BPM")
                        }
                        if let duration = track.duration {
                            Text(formatDuration(duration))
                        }
                        if let size = track.sizeMb {
                            Text("\(size, specifier: "%.1f") MB")
                        }
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }

                Spacer()
            }
        }
        .buttonStyle(.plain)
    }

    // MARK: - Network

    private func loadTracks() async {
        isLoading = true
        defer { isLoading = false }

        do {
            tracks = try await api.getMusicTracks()
        } catch {
            errorMessage = "Müzik listesi yüklenemedi: \(error.localizedDescription)"
        }
    }

    // MARK: - Helpers

    private func localizedTransition(_ t: String) -> String {
        switch t {
        case "fade": return "Fade"
        case "wipeleft": return "Sola Kaydır"
        case "wiperight": return "Sağa Kaydır"
        case "slideup": return "Yukarı Kaydır"
        case "slidedown": return "Aşağı Kaydır"
        default: return t
        }
    }

    private func formatDuration(_ seconds: Double) -> String {
        let mins = Int(seconds) / 60
        let secs = Int(seconds) % 60
        return "\(mins):\(String(format: "%02d", secs))"
    }
}
