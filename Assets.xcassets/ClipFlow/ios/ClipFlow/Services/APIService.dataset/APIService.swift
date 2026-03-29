import Foundation

/// Handles all network communication with ClipFlow backend.
actor APIService {
    static let shared = APIService()

    // TODO: Production'da gerçek URL'ye çevir
    private let baseURL = "http://localhost:8000/api/v1"

    // MARK: - Upload

    /// Upload a video file to the server.
    func upload(videoURL: URL) async throws -> UploadResponse {
        let url = URL(string: "\(baseURL)/upload")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        let data = try createMultipartBody(fileURL: videoURL, boundary: boundary)
        request.httpBody = data

        let (responseData, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)

        return try JSONDecoder().decode(UploadResponse.self, from: responseData)
    }

    // MARK: - Process

    /// Start video processing.
    func startProcessing(clipIds: [String], mode: String = "talking_reels") async throws -> ProcessResponse {
        let url = URL(string: "\(baseURL)/process")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let body: [String: Any] = [
            "clip_ids": clipIds,
            "mode": mode,
            "settings": ["output_format": "9:16", "add_captions": true]
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try validateResponse(response)

        return try JSONDecoder().decode(ProcessResponse.self, from: data)
    }

    // MARK: - Status Polling

    /// Get current job status.
    func getStatus(jobId: String) async throws -> StatusResponse {
        let url = URL(string: "\(baseURL)/process/\(jobId)")!
        let (data, response) = try await URLSession.shared.data(from: url)
        try validateResponse(response)

        return try JSONDecoder().decode(StatusResponse.self, from: data)
    }

    // MARK: - Download

    /// Download processed video to a local temp file.
    func downloadVideo(fileId: String) async throws -> URL {
        let url = URL(string: "\(baseURL)/download/\(fileId)")!
        let (tempURL, response) = try await URLSession.shared.download(from: url)
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

    private func createMultipartBody(fileURL: URL, boundary: String) throws -> Data {
        var body = Data()
        let filename = fileURL.lastPathComponent
        let mimeType = "video/mp4"

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(try Data(contentsOf: fileURL))
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        return body
    }

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
