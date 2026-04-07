import Foundation

struct Folder: Codable, Identifiable, Sendable, Hashable {
    let id: String
    var name: String
    let createdAt: Date
    var videoIds: [String]
    var styleId: String?

    enum CodingKeys: String, CodingKey {
        case id, name, styleId = "style_id"
        case videoIds = "video_ids"
        case createdAt = "created_at"
    }
}

struct CreateFolderRequest: Codable, Sendable {
    let name: String
}

struct RenameFolderRequest: Codable, Sendable {
    let name: String
}

struct AddVideoRequest: Codable, Sendable {
    let videoId: String

    enum CodingKeys: String, CodingKey {
        case videoId = "video_id"
    }
}
