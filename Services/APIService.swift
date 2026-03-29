import Foundation

/// Handles all network communication with ClipFlow backend.
actor APIService {
    static let shared = APIService()

    #if DEBUG
    private let baseURL = "http://192.168.1.101:8000/api/v1"
    #else
    private let baseURL = "https://api.clipflow.app/api/v1"
    #endif

    /// URLSession with extended timeout for large file uploads/downloads.
    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 300   // 5 min per request
        config.timeoutIntervalForResource = 600  // 10 min total
        return URLSession(configuration: config)
    }()

    // MARK: - Upload

    /// Upload a video file to the server.
    /// Sends raw binary directly from disk — no temp files, no RAM spike.
    func upload(videoURL: URL) async throws -> UploadResponse {
        let url = URL(string: "\(baseURL)/upload")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        request.setValue(videoURL.lastPathComponent, forHTTPHeaderField: "X-Filename")

        // Streams the file directly from disk — O(1) memory regardless of file size
        let (responseData, response) = try await session.upload(for: request, fromFile: videoURL)
        try validateResponse(response)

        return try JSONDecoder().decode(UploadResponse.self, from: responseData)
    }

    // MARK: - Process

    /// Start video processing with quality mode.
    func startProcessing(clipIds: [String], quality: QualityMode = .reels) async throws -> ProcessResponse {
        let url = URL(string: "\(baseURL)/process")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "clip_ids": clipIds,
            "mode": "talking_reels",
            "quality": quality.rawValue,
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)
        try validateResponse(response)

        return try JSONDecoder().decode(ProcessResponse.self, from: data)
    }

    // MARK: - Status Polling

    /// Get current job status.
    func getStatus(jobId: String) async throws -> StatusResponse {
        let url = URL(string: "\(baseURL)/process/\(jobId)")!
        let (data, response) = try await session.data(from: url)
        try validateResponse(response)

        return try JSONDecoder().decode(StatusResponse.self, from: data)
    }

    // MARK: - Download

    /// Download processed video to a local temp file.
    func downloadVideo(fileId: String) async throws -> URL {
        let url = URL(string: "\(baseURL)/download/\(fileId)")!
        let (tempURL, response) = try await session.download(from: url)
        try validateResponse(response)

        // Move to a permanent temp location (download temp files get deleted)
        let destination = FileManager.default.temporaryDirectory
            .appendingPathComponent("\(fileId).mp4")
        if FileManager.default.fileExists(atPath: destination.path) {
            try FileManager.default.removeItem(at: destination)
        }
        try FileManager.default.moveItem(at: tempURL, to: destination)

        return destination
    }

    // MARK: - Helpers

    private func validateResponse(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        guard (200...299).contains(http.statusCode) else {
            throw APIError.serverError(http.statusCode)
        }
    }
}

/// API error types
enum APIError: LocalizedError {
    case invalidResponse
    case serverError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Geçersiz sunucu yanıtı"
        case .serverError(let code):
            return "Sunucu hatası: \(code)"
        }
    }
}
