import Foundation
import Observation

/// Manages folder CRUD operations and state.
@Observable
@MainActor
final class FolderViewModel {

    var folders: [Folder] = []
    var isLoading = false
    var errorMessage: String?

    private let api = APIService.shared

    // MARK: - Actions

    /// Fetch all folders from the server.
    func loadFolders() async {
        isLoading = true
        errorMessage = nil

        do {
            folders = try await api.getFolders()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    /// Create a new folder with the given name.
    func createFolder(name: String, styleId: String? = nil) async {
        do {
            let folder = try await api.createFolder(name: name, styleId: styleId)
            folders.insert(folder, at: 0)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Delete a folder by ID.
    func deleteFolder(id: String) async {
        do {
            try await api.deleteFolder(id: id)
            folders.removeAll { $0.id == id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Add a video to a folder.
    func addVideo(folderId: String, videoId: String) async {
        do {
            let updated = try await api.addVideoToFolder(folderId: folderId, videoId: videoId)
            if let index = folders.firstIndex(where: { $0.id == folderId }) {
                folders[index] = updated
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
