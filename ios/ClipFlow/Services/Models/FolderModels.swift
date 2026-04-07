import Foundation

// MARK: - Folder Models

/// A project folder that groups related videos
struct Folder: Codable, Identifiable, Sendable, Hashable {
    let id: String
    var name: String
    let createdAt: Date
    var videoIds: [String]
    var styleId: String?

    enum CodingKeys: String, CodingKey {
        case id, name, videoIds = "video_ids"
        case createdAt = "created_at"
        case styleId = "style_id"
    }
}

/// Request body for creating a folder
struct CreateFolderRequest: Codable, Sendable {
    let name: String
}

/// Request body for renaming a folder
struct RenameFolderRequest: Codable, Sendable {
    let name: String
}

/// Request body for adding a video to a folder
struct AddVideoRequest: Codable, Sendable {
    let videoId: String

    enum CodingKeys: String, CodingKey {
        case videoId = "video_id"
    }
}
