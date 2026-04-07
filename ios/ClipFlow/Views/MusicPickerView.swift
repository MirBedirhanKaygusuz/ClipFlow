import SwiftUI

struct MusicPickerView: View {
    let videoFileId: String
    let onStart: (String, String, Double, Bool, Double) -> Void
    let onCancel: () -> Void

    @State private var tracks: [MusicTrack] = []
    @State private var selectedTrackId: String?
    @State private var isLoading = false
    @State private var transition = "fade"
    @State private var transitionDuration = 0.5
    @State private var enableZoom = false
    @State private var zoomIntensity = 0.5
    @State private var errorMessage: String?

    private let transitions = ["fade", "wipeleft", "wiperight", "slideup", "slidedown"]

    var body: some View {
        NavigationStack {
            List {
                Section("M\u00fczik K\u00fct\u00fcphanesi") {
                    if isLoading {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                    } else if tracks.isEmpty {
                        Text("Hen\u00fcz m\u00fczik y\u00fcklenmemi\u015f")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(tracks, id: \.id) { track in
                            trackRow(track)
                        }
                    }
                }

                Section("Ge\u00e7i\u015f Efekti") {
                    Picker("Ge\u00e7i\u015f Tipi", selection: $transition) {
                        ForEach(transitions, id: \.self) { t in
                            Text(localizedTransition(t)).tag(t)
                        }
                    }

                    HStack {
                        Text("S\u00fcre")
                        Slider(value: $transitionDuration, in: 0.2...2.0, step: 0.1)
                        Text("\(transitionDuration, specifier: "%.1f")s")
                            .monospacedDigit()
                            .frame(width: 40)
                    }
                }

                Section("Ak\u0131ll\u0131 Zoom") {
                    Toggle("Beat'lere senkronize zoom", isOn: $enableZoom)

                    if enableZoom {
                        HStack {
                            Text("Yo\u011funluk")
                            Slider(value: $zoomIntensity, in: 0.1...1.0, step: 0.1)
                            Text("%\(Int(zoomIntensity * 100))")
                                .monospacedDigit()
                                .frame(width: 36)
                        }
                        Text("Beat vuru\u015flar\u0131nda zoom in, aralar\u0131nda zoom out")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                if let errorMessage {
                    Section {
                        Text(errorMessage)
                            .foregroundStyle(.red)
                            .font(.caption)
                    }
                }
            }
            .navigationTitle("M\u00fczikli Edit")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Vazge\u00e7", action: onCancel)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Ba\u015fla") {
                        if let id = selectedTrackId {
                            onStart(id, transition, transitionDuration, enableZoom, zoomIntensity)
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
                            let mins = Int(duration) / 60
                            let secs = Int(duration) % 60
                            Text("\(mins):\(String(format: "%02d", secs))")
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

    private func loadTracks() async {
        isLoading = true
        defer { isLoading = false }

        do {
            let url = URL(string: "http://localhost:8000/api/v1/music")!
            let (data, _) = try await URLSession.shared.data(from: url)
            tracks = try JSONDecoder().decode([MusicTrack].self, from: data)
        } catch {
            errorMessage = "M\u00fczik listesi y\u00fcklenemedi: \(error.localizedDescription)"
        }
    }

    private func localizedTransition(_ t: String) -> String {
        switch t {
        case "fade": return "Fade"
        case "wipeleft": return "Sola Kayd\u0131r"
        case "wiperight": return "Sa\u011fa Kayd\u0131r"
        case "slideup": return "Yukar\u0131 Kayd\u0131r"
        case "slidedown": return "A\u015fa\u011f\u0131 Kayd\u0131r"
        default: return t
        }
    }
}
