import Foundation
import Observation

/// Manages folder/project list — CRUD operations backed by APIService.
@Observable
@MainActor
final class FolderViewModel {


    var folders: [Folder] = []
    var isLoading = false
    var error: String? = nil

    /// Controls the "Yeni Klasör" alert
    var showingCreateAlert = false
    var newFolderName = ""

    /// Controls the rename alert
    var folderToRename: Folder? = nil
    var renamedFolderName = ""

    private let api = APIService.shared


    /// Fetch all folders from the server.
    func loadFolders() async {
        isLoading = true
        error = nil
        do {
            folders = try await api.listFolders()
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }

    /// Create a new folder with the current `newFolderName`.
    func createFolder() async {
        let name = newFolderName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        do {
            let folder = try await api.createFolder(name: name)
            folders.insert(folder, at: 0)
            newFolderName = ""
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Rename a folder.
    func renameFolder(_ folder: Folder) async {
        let name = renamedFolderName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        do {
            let updated = try await api.renameFolder(id: folder.id, name: name)
            if let idx = folders.firstIndex(where: { $0.id == folder.id }) {
                folders[idx] = updated
            }
            folderToRename = nil
            renamedFolderName = ""
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Delete a folder.
    func deleteFolder(_ folder: Folder) async {
        do {
            try await api.deleteFolder(id: folder.id)
            folders.removeAll { $0.id == folder.id }
        } catch {
            self.error = error.localizedDescription
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
            self.error = error.localizedDescription
        }
    }
}
