import Foundation

public enum RecurringService {

    /// GET /recurring
    public static func getRecurringExpenses() async throws -> RecurringListResponse {
        let endpoint = APIEndpoint(method: .get, path: "/recurring")
        return try await APIClient.shared.request(endpoint)
    }

    /// DELETE /recurring/{id}
    public static func deleteRecurringExpense(
        id: String
    ) async throws -> SuccessResponse {
        let endpoint = APIEndpoint(method: .delete, path: "/recurring/\(id)")
        return try await APIClient.shared.request(endpoint)
    }
}
