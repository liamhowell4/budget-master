import Foundation

public enum ServerService {

    /// GET /servers
    public static func listServers() async throws -> [MCPServer] {
        let endpoint = APIEndpoint(
            method: .get,
            path: "/servers",
            requiresAuth: true
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// POST /connect/{server_id}
    public static func connect(serverId: String) async throws -> ServerConnectResponse {
        let endpoint = APIEndpoint(
            method: .post,
            path: "/connect/\(serverId)",
            requiresAuth: true
        )
        // POST with empty body
        let emptyBody: [String: String] = [:]
        return try await APIClient.shared.request(endpoint, body: emptyBody)
    }

    /// GET /status
    public static func getStatus() async throws -> ServerStatus {
        let endpoint = APIEndpoint(
            method: .get,
            path: "/status",
            requiresAuth: true
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// POST /disconnect
    public static func disconnect() async throws -> SuccessResponse {
        let endpoint = APIEndpoint(
            method: .post,
            path: "/disconnect",
            requiresAuth: true
        )
        let emptyBody: [String: String] = [:]
        return try await APIClient.shared.request(endpoint, body: emptyBody)
    }

    /// GET /health (no auth required)
    public static func healthCheck() async throws -> HealthResponse {
        let endpoint = APIEndpoint(
            method: .get,
            path: "/health",
            requiresAuth: false
        )
        return try await APIClient.shared.request(endpoint)
    }
}
