import Foundation

enum ServerService {

    /// GET /servers (no auth required)
    static func listServers() async throws -> [MCPServer] {
        let endpoint = APIEndpoint(
            method: .get,
            path: "/servers",
            requiresAuth: false
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// POST /connect/{server_id} (no auth required)
    static func connect(serverId: String) async throws -> ServerConnectResponse {
        let endpoint = APIEndpoint(
            method: .post,
            path: "/connect/\(serverId)",
            requiresAuth: false
        )
        // POST with empty body
        let emptyBody: [String: String] = [:]
        return try await APIClient.shared.request(endpoint, body: emptyBody)
    }

    /// GET /status (no auth required)
    static func getStatus() async throws -> ServerStatus {
        let endpoint = APIEndpoint(
            method: .get,
            path: "/status",
            requiresAuth: false
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// POST /disconnect (no auth required)
    static func disconnect() async throws -> SuccessResponse {
        let endpoint = APIEndpoint(
            method: .post,
            path: "/disconnect",
            requiresAuth: false
        )
        let emptyBody: [String: String] = [:]
        return try await APIClient.shared.request(endpoint, body: emptyBody)
    }

    /// GET /health (no auth required)
    static func healthCheck() async throws -> HealthResponse {
        let endpoint = APIEndpoint(
            method: .get,
            path: "/health",
            requiresAuth: false
        )
        return try await APIClient.shared.request(endpoint)
    }
}
