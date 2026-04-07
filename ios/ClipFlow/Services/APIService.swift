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

    /// Shared decoder with ISO8601 date support (needed for folder dates).
    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
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
    /// Supports both simple calls (clipIds + quality) and advanced calls with music/zoom/transition settings.
    func startProcessing(
        clipIds: [String],
        mode: ProcessingMode = .talkingReels,
        quality: QualityMode = .reels,
        musicFileId: String? = nil,
        transition: String = "fade",
        transitionDuration: Double = 0.5,
        enableZoom: Bool = false,
        zoomIntensity: Double = 0.5
    ) async throws -> ProcessResponse {
        let url = URL(string: "\(baseURL)/process")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var settings: [String: Any] = [
            "enable_zoom": enableZoom,
            "zoom_intensity": zoomIntensity,
        ]

        var body: [String: Any] = [
            "clip_ids": clipIds,
            "mode": mode.rawValue,
            "quality": quality.rawValue,
        ]

        if mode == .musicalEdit {
            settings["transition"] = transition
            settings["transition_duration"] = transitionDuration
            if let musicFileId {
                settings["music_file_id"] = musicFileId
            }
        }

        body["settings"] = settings

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: request)
        try validateResponse(response)

        return try JSONDecoder().decode(ProcessResponse.self, from: data)
    }

    // MARK: - Music

    /// Upload a music track.
    func uploadMusic(fileURL: URL) async throws -> MusicTrack {
        let url = URL(string: "\(baseURL)/music/upload")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        request.setValue(fileURL.lastPathComponent, forHTTPHeaderField: "X-Filename")

        let (data, response) = try await session.upload(for: request, fromFile: fileURL)
        try validateResponse(response)
        return try JSONDecoder().decode(MusicTrack.self, from: data)
    }

    /// List all music tracks.
    func getMusicTracks() async throws -> [MusicTrack] {
        let url = URL(string: "\(baseURL)/music")!
        let (data, response) = try await session.data(from: url)
        try validateResponse(response)
        return try JSONDecoder().decode([MusicTrack].self, from: data)
    }

    /// Analyze beats in a music track.
    func analyzeMusic(musicId: String) async throws -> [String: Any] {
        let url = URL(string: "\(baseURL)/music/\(musicId)/analyze")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let (data, response) = try await session.data(for: request)
        try validateResponse(response)

        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw APIError.invalidResponse
        }
        return json
    }

    // MARK: - Thumbnails

    /// Get thumbnail URL for a video. Returns the full URL to fetch the image.
    func thumbnailURL(fileId: String) -> URL {
        URL(string: "\(baseURL)/thumbnails/\(fileId)")!
    }

    // MARK: - Export Presets

    /// Get all available export presets.
    func getExportPresets() async throws -> [ExportPreset] {
        let url = URL(string: "\(baseURL)/presets")!
        let (data, response) = try await session.data(from: url)
        try validateResponse(response)

        struct PresetsResponse: Codable {
            let presets: [ExportPreset]
        }
        return try JSONDecoder().decode(PresetsResponse.self, from: data).presets
    }

    // MARK: - Validation

    /// Validate an uploaded video and get metadata.
    func validateVideo(fileId: String) async throws -> VideoValidation {
        let url = URL(string: "\(baseURL)/validate/\(fileId)")!
        let (data, response) = try await session.data(from: url)
        try validateResponse(response)
        return try JSONDecoder().decode(VideoValidation.self, from: data)
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

    // MARK: - Folders

    /// List all folders.
    func listFolders() async throws -> [Folder] {
        let url = URL(string: "\(baseURL)/folders")!
        let (data, response) = try await session.data(from: url)
        try validateResponse(response)
        return try decoder.decode([Folder].self, from: data)
    }

    /// Create a new folder.
    func createFolder(name: String) async throws -> Folder {
        let url = URL(string: "\(baseURL)/folders")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(CreateFolderRequest(name: name))
        let (data, response) = try await session.data(for: request)
        try validateResponse(response)
        return try decoder.decode(Folder.self, from: data)
    }

    /// Rename a folder.
    func renameFolder(id: String, name: String) async throws -> Folder {
        let url = URL(string: "\(baseURL)/folders/\(id)")!
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(RenameFolderRequest(name: name))
        let (data, response) = try await session.data(for: request)
        try validateResponse(response)
        return try decoder.decode(Folder.self, from: data)
    }

    /// Delete a folder.
    func deleteFolder(id: String) async throws {
        let url = URL(string: "\(baseURL)/folders/\(id)")!
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        let (_, response) = try await session.data(for: request)
        try validateResponse(response)
    }

    /// Add a video to a folder.
    func addVideoToFolder(folderId: String, videoId: String) async throws -> Folder {
        let url = URL(string: "\(baseURL)/folders/\(folderId)/videos")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(AddVideoRequest(videoId: videoId))
        let (data, response) = try await session.data(for: request)
        try validateResponse(response)
        return try decoder.decode(Folder.self, from: data)
    }

    /// Remove a video from a folder.
    func removeVideoFromFolder(folderId: String, videoId: String) async throws -> Folder {
        let url = URL(string: "\(baseURL)/folders/\(folderId)/videos/\(videoId)")!
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        let (data, response) = try await session.data(for: request)
        try validateResponse(response)
        return try decoder.decode(Folder.self, from: data)
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
