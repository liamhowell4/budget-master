import Foundation

/// Thread-safe API client for the BudgetMaster backend.
actor APIClient {
    static let shared = APIClient()

    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    private var tokenProvider: TokenProvider

    init(
        baseURL: URL = URL(string: "https://budget-master-backend-857587891388.us-central1.run.app")!,
        session: URLSession = .shared,
        tokenProvider: TokenProvider = StubTokenProvider()
    ) {
        self.baseURL = baseURL
        self.session = session
        self.tokenProvider = tokenProvider

        self.decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase

        self.encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
    }

    /// Update the token provider (e.g. after sign-in).
    func setTokenProvider(_ provider: TokenProvider) {
        self.tokenProvider = provider
    }

    // MARK: - Request Building

    private func buildRequest(endpoint: APIEndpoint) async throws -> URLRequest {
        var components = URLComponents(url: baseURL.appendingPathComponent(endpoint.path), resolvingAgainstBaseURL: false)
        components?.queryItems = endpoint.queryItems

        guard let url = components?.url else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue

        if endpoint.requiresAuth {
            let token = try await tokenProvider.getToken()
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        return request
    }

    // MARK: - Public API

    /// Perform a request with no body, decoding the response into `T`.
    func request<T: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        as type: T.Type = T.self
    ) async throws -> T {
        let request = try await buildRequest(endpoint: endpoint)
        return try await execute(request, as: type)
    }

    /// Perform a request with a JSON body, decoding the response into `T`.
    func request<Body: Encodable & Sendable, T: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        body: Body,
        as type: T.Type = T.self
    ) async throws -> T {
        var request = try await buildRequest(endpoint: endpoint)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(body)
        return try await execute(request, as: type)
    }

    /// Perform a multipart form-data upload, decoding the response into `T`.
    func upload<T: Decodable & Sendable>(
        _ endpoint: APIEndpoint,
        multipart: MultipartFormData,
        as type: T.Type = T.self
    ) async throws -> T {
        var request = try await buildRequest(endpoint: endpoint)
        request.setValue(multipart.contentType, forHTTPHeaderField: "Content-Type")
        request.httpBody = multipart.finalize()
        return try await execute(request, as: type)
    }

    /// Open an SSE connection and return the raw `URLSession.AsyncBytes` stream.
    /// The caller (SSEClient) handles line parsing.
    func streamRequest(
        _ endpoint: APIEndpoint,
        body: some Encodable & Sendable
    ) async throws -> (URLSession.AsyncBytes, URLResponse) {
        var request = try await buildRequest(endpoint: endpoint)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(body)
        return try await session.bytes(for: request)
    }

    // MARK: - Execution

    private func execute<T: Decodable>(
        _ request: URLRequest,
        as type: T.Type
    ) async throws -> T {
        let data: Data
        let response: URLResponse

        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }

        try validateResponse(response, data: data)

        do {
            return try decoder.decode(type, from: data)
        } catch {
            throw APIError.decodingFailed(error)
        }
    }

    private func validateResponse(_ response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else { return }

        switch http.statusCode {
        case 200..<300:
            return
        case 401:
            throw APIError.unauthorized
        case 404:
            throw APIError.notFound
        case 400:
            let detail = parseDetail(from: data)
            throw APIError.badRequest(detail ?? "Bad request")
        default:
            let detail = parseDetail(from: data)
            throw APIError.serverError(statusCode: http.statusCode, message: detail)
        }
    }

    /// Extract the `detail` field from FastAPI error responses.
    private func parseDetail(from data: Data) -> String? {
        if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            return json["detail"] as? String
        }
        return nil
    }
}
