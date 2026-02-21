import Foundation

public enum APIError: LocalizedError, Sendable {
    case invalidURL
    case unauthorized
    case notFound
    case badRequest(String)
    case serverError(statusCode: Int, message: String?)
    case decodingFailed(Error)
    case networkError(Error)
    case noToken
    case sseParsingError(String)

    public var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .unauthorized:
            return "Authentication required. Please sign in again."
        case .notFound:
            return "The requested resource was not found."
        case .badRequest(let message):
            return message
        case .serverError(let code, let message):
            return message ?? "Server error (\(code))"
        case .decodingFailed(let error):
            return "Failed to parse response: \(error.localizedDescription)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .noToken:
            return "No authentication token available."
        case .sseParsingError(let message):
            return "SSE parsing error: \(message)"
        }
    }
}
