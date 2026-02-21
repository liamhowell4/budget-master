import Foundation

public enum PendingService {

    /// GET /pending
    public static func getPendingExpenses() async throws -> PendingListResponse {
        let endpoint = APIEndpoint(method: .get, path: "/pending")
        return try await APIClient.shared.request(endpoint)
    }

    /// POST /pending/{id}/confirm?adjusted_amount=
    public static func confirmPending(
        id: String,
        adjustedAmount: Double? = nil
    ) async throws -> PendingConfirmResponse {
        var queryItems: [URLQueryItem] = []
        if let amount = adjustedAmount {
            queryItems.append(.init(name: "adjusted_amount", value: "\(amount)"))
        }

        let endpoint = APIEndpoint(
            method: .post,
            path: "/pending/\(id)/confirm",
            queryItems: queryItems.isEmpty ? nil : queryItems
        )
        // POST with empty body
        let emptyBody: [String: String] = [:]
        return try await APIClient.shared.request(endpoint, body: emptyBody)
    }

    /// DELETE /pending/{id}
    public static func deletePending(id: String) async throws -> SuccessResponse {
        let endpoint = APIEndpoint(method: .delete, path: "/pending/\(id)")
        return try await APIClient.shared.request(endpoint)
    }
}
