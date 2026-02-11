import Foundation

enum ConversationService {

    /// GET /conversations?limit=
    static func listConversations(
        limit: Int = 20
    ) async throws -> ConversationListResponse {
        let endpoint = APIEndpoint(
            method: .get,
            path: "/conversations",
            queryItems: [.init(name: "limit", value: "\(limit)")]
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// GET /conversations/{id}
    static func getConversation(
        id: String
    ) async throws -> Conversation {
        let endpoint = APIEndpoint(method: .get, path: "/conversations/\(id)")
        return try await APIClient.shared.request(endpoint)
    }

    /// POST /conversations
    static func createConversation() async throws -> ConversationCreateResponse {
        let endpoint = APIEndpoint(method: .post, path: "/conversations")
        // POST with empty body
        let emptyBody: [String: String] = [:]
        return try await APIClient.shared.request(endpoint, body: emptyBody)
    }

    /// DELETE /conversations/{id}
    static func deleteConversation(
        id: String
    ) async throws -> SuccessResponse {
        let endpoint = APIEndpoint(method: .delete, path: "/conversations/\(id)")
        return try await APIClient.shared.request(endpoint)
    }
}
