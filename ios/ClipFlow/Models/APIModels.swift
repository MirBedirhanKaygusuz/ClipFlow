import Foundation

/// Upload response from POST /upload
struct UploadResponse: Codable {
    let fileId: String
    let sizeMb: Double

    enum CodingKeys: String, CodingKey {
        case fileId = "file_id"
        case sizeMb = "size_mb"
    }
}

/// Process response from POST /process
struct ProcessResponse: Codable {
    let jobId: String
    let estimatedSeconds: Int

    enum CodingKeys: String, CodingKey {
        case jobId = "job_id"
        case estimatedSeconds = "estimated_seconds"
    }
}

/// Status response from GET /process/{job_id}
struct StatusResponse: Codable {
    let status: String
    let progress: Int
    let step: String
    let outputUrl: String?
    let question: String?
    let options: [String]?
    let stats: ProcessingStats?

    enum CodingKeys: String, CodingKey {
        case status, progress, step, question, options, stats
        case outputUrl = "output_url"
    }
}

/// Processing statistics
struct ProcessingStats: Codable {
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
