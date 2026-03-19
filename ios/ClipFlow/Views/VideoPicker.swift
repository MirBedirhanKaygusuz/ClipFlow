import PhotosUI
import SwiftUI

/// PHPicker wrapper for selecting a single video from Camera Roll.
struct VideoPicker: UIViewControllerRepresentable {
    let onSelect: (URL) -> Void

    func makeUIViewController(context: Context) -> PHPickerViewController {
        var config = PHPickerConfiguration()
        config.selectionLimit = 1
        config.filter = .videos
        let picker = PHPickerViewController(configuration: config)
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ uiViewController: PHPickerViewController, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(onSelect: onSelect)
    }

    final class Coordinator: NSObject, PHPickerViewControllerDelegate {
        let onSelect: (URL) -> Void

        init(onSelect: @escaping (URL) -> Void) {
            self.onSelect = onSelect
        }

        func picker(_ picker: PHPickerViewController, didFinishPicking results: [PHPickerResult]) {
            picker.dismiss(animated: true)

            guard let provider = results.first?.itemProvider,
                  provider.hasItemConformingToTypeIdentifier(UTType.movie.identifier) else {
                return
            }

            provider.loadFileRepresentation(forTypeIdentifier: UTType.movie.identifier) { [weak self] url, error in
                guard let url = url, error == nil else { return }

                // PHPicker gives a temp URL that gets deleted — copy it
                let destination = FileManager.default.temporaryDirectory
                    .appendingPathComponent(UUID().uuidString + ".mp4")
                do {
                    try FileManager.default.copyItem(at: url, to: destination)
                    DispatchQueue.main.async {
                        self?.onSelect(destination)
                    }
                } catch {
                    print("Video kopyalama hatası: \(error)")
                }
            }
        }
    }
}
