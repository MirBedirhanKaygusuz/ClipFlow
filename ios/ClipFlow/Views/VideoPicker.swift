import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

/// PHPicker wrapper for selecting a single video from Camera Roll.
struct VideoPicker: UIViewControllerRepresentable {
    let onPreparing: () -> Void   // Called immediately on selection (before copy)
    let onSelect: (URL) -> Void   // Called when file URL is ready
    let onError: (String) -> Void // Called if preparation fails

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration()
        config.selectionLimit = 1
        config.filter = .videos
        // Don't transcode — return original file directly (much faster for large/4K videos)
        config.preferredAssetRepresentationMode = .current
        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onPreparing: onPreparing, onSelect: onSelect, onError: onError)
    }

    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let onPreparing: () -> Void
        let onSelect: (URL) -> Void
        let onError: (String) -> Void

        init(onPreparing: @escaping () -> Void,
             onSelect: @escaping (URL) -> Void,
             onError: @escaping (String) -> Void) {
            self.onPreparing = onPreparing
            self.onSelect = onSelect
            self.onError = onError
        }

        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            picker.dismiss(animated: true)

            guard let provider = results.first?.itemProvider,
                  provider.hasItemConformingToTypeIdentifier(UTType.movie.identifier) else {
                return
            }

            // Signal immediately so UI can show "preparing" state
            DispatchQueue.main.async { self.onPreparing() }

            provider.loadFileRepresentation(forTypeIdentifier: UTType.movie.identifier) { [weak self] url, error in
                guard let self else { return }

                if let error {
                    DispatchQueue.main.async {
                        self.onError("Video hazırlanamadı: \(error.localizedDescription)")
                    }
                    return
                }

                guard let url else {
                    DispatchQueue.main.async { self.onError("Video dosyası alınamadı.") }
                    return
                }

                // Copy to a permanent temp location before PHPicker cleans up
                let ext = url.pathExtension.isEmpty ? "mp4" : url.pathExtension
                let destination = FileManager.default.temporaryDirectory
                    .appendingPathComponent(UUID().uuidString + "." + ext)
                do {
                    try FileManager.default.copyItem(at: url, to: destination)
                    DispatchQueue.main.async { self.onSelect(destination) }
                } catch {
                    DispatchQueue.main.async {
                        self.onError("Video kopyalanamadı: \(error.localizedDescription)")
                    }
                }
            }
        }
    }
}
