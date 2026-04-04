import Foundation

/// Processing mode — which pipeline to use
enum ProcessingMode: String, Sendable {
    case talkingReels = "talking_reels"
    case musicalEdit = "musical_edit"
}

/// Quality mode — mirrors backend QualityMode enum
enum QualityMode: String, Sendable {
    case reels = "reels"
    case highQuality = "high_quality"
}

/// Music track metadata
struct MusicTrack: Codable, Sendable {
    let id: String
    let filename: String
    let sizeMb: Double?
    let tempo: Double?
    let beatCount: Int?
    let duration: Double?

    enum CodingKeys: String, CodingKey {
        case id, filename, tempo, duration
        case sizeMb = "size_mb"
        case beatCount = "beat_count"
    }
}

/// Upload response from POST /upload
struct UploadResponse: Codable, Sendable {
    let fileId: String
    let sizeMb: Double

    enum CodingKeys: String, CodingKey {
        case fileId = "file_id"
        case sizeMb = "size_mb"
    }
}

/// Process response from POST /process
struct ProcessResponse: Codable, Sendable {
    let jobId: String
    let estimatedSeconds: Int

    enum CodingKeys: String, CodingKey {
        case jobId = "job_id"
        case estimatedSeconds = "estimated_seconds"
    }
}

/// Status response from GET /process/{job_id}
struct StatusResponse: Codable, Sendable {
    let status: String
    let progress: Int
    let step: String
    let outputUrl: String?
    let question: String?
    let options: [String]?
    let stats: ProcessingStats?
    let etaSeconds: Double?

    enum CodingKeys: String, CodingKey {
        case status, progress, step, question, options, stats
        case outputUrl = "output_url"
        case etaSeconds = "eta_seconds"
    }
}

/// Project folder containing videos
struct Folder: Codable, Sendable {
    let id: String
    let name: String
    let createdAt: String
    let videoIds: [String]
    let styleId: String?

    enum CodingKeys: String, CodingKey {
        case id, name
        case createdAt = "created_at"
        case videoIds = "video_ids"
        case styleId = "style_id"
    }
}

/// Processing statistics
struct ProcessingStats: Codable, Equatable, Sendable {
    let originalDuration: Double?
    let newDuration: Double?
    let silenceRemovedPct: Double?
    let segments: Int?

    enum CodingKeys: String, CodingKey {
        case originalDuration = "original_duration"
        case newDuration = "new_duration"
        case silenceRemovedPct = "silence_removed_pct"
        case segments
    }
}
