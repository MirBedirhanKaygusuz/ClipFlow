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
    let thumbnailUrl: String?

    enum CodingKeys: String, CodingKey {
        case fileId = "file_id"
        case sizeMb = "size_mb"
        case thumbnailUrl = "thumbnail_url"
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

/// Video validation result from GET /validate/{id}
struct VideoValidation: Codable, Sendable {
    let valid: Bool
    let errors: [String]
    let warnings: [String]
    let info: VideoMetadata?
}

/// Video metadata from validation
struct VideoMetadata: Codable, Sendable {
    let duration: Double
    let width: Int
    let height: Int
    let videoCodec: String
    let audioCodec: String?
    let fps: Double
    let bitrateKbps: Int
    let fileSizeMb: Double
    let hasAudio: Bool
    let rotation: Int

    enum CodingKeys: String, CodingKey {
        case duration, width, height, fps, rotation
        case videoCodec = "video_codec"
        case audioCodec = "audio_codec"
        case bitrateKbps = "bitrate_kbps"
        case fileSizeMb = "file_size_mb"
        case hasAudio = "has_audio"
    }
}

/// Export preset for a specific platform
struct ExportPreset: Codable, Sendable, Identifiable {
    let id: String
    let name: String
    let platform: String
    let width: Int
    let height: Int
    let fps: Int
    let videoBitrateKbps: Int
    let audioBitrateKbps: Int
    let maxDuration: Double
    let aspectRatio: String
    let codec: String
    let preset: String
    let description: String

    enum CodingKeys: String, CodingKey {
        case id, name, platform, width, height, fps, codec, preset, description
        case videoBitrateKbps = "video_bitrate_kbps"
        case audioBitrateKbps = "audio_bitrate_kbps"
        case maxDuration = "max_duration"
        case aspectRatio = "aspect_ratio"
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
