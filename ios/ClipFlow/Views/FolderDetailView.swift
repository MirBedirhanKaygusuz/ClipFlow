import SwiftUI

struct FolderDetailView: View {
    let folder: Folder

    var body: some View {
        Group {
            if folder.videoIds.isEmpty {
                emptyView
            } else {
                videoList
            }
        }
        .navigationTitle(folder.name)
    }

    private var emptyView: some View {
        VStack(spacing: 16) {
            Image(systemName: "film.stack")
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text("Bu klas\u00f6rde hen\u00fcz video yok")
                .font(.headline)
                .foregroundStyle(.secondary)

            Text("Bir video i\u015fledikten sonra bu klas\u00f6re ekleyebilirsiniz.")
                .font(.subheadline)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)
        }
    }

    private var videoList: some View {
        List {
            if let styleId = folder.styleId {
                Section("Stil Profili") {
                    HStack {
                        Image(systemName: "paintpalette")
                            .foregroundStyle(.purple)
                        Text(styleId)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section("Videolar (\(folder.videoIds.count))") {
                ForEach(folder.videoIds, id: \.self) { videoId in
                    HStack {
                        Image(systemName: "play.rectangle.fill")
                            .foregroundStyle(.blue)
                        Text(videoId)
                            .font(.subheadline)
                            .lineLimit(1)
                    }
                }
            }
        }
    }
}
