import Foundation

public enum ExpenseService {

    /// GET /expenses?year=&month=&category=
    public static func getExpenses(
        year: Int? = nil,
        month: Int? = nil,
        category: String? = nil
    ) async throws -> ExpensesResponse {
        var queryItems: [URLQueryItem] = []
        if let year { queryItems.append(.init(name: "year", value: "\(year)")) }
        if let month { queryItems.append(.init(name: "month", value: "\(month)")) }
        if let category { queryItems.append(.init(name: "category", value: category)) }

        let endpoint = APIEndpoint(
            method: .get,
            path: "/expenses",
            queryItems: queryItems.isEmpty ? nil : queryItems
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// PUT /expenses/{id}
    public static func updateExpense(
        id: String,
        update: ExpenseUpdateRequest
    ) async throws -> ExpenseUpdateResponse {
        let endpoint = APIEndpoint(
            method: .put,
            path: "/expenses/\(id)"
        )
        return try await APIClient.shared.request(endpoint, body: update)
    }

    /// DELETE /expenses/{id}
    public static func deleteExpense(id: String) async throws -> ExpenseDeleteResponse {
        let endpoint = APIEndpoint(
            method: .delete,
            path: "/expenses/\(id)"
        )
        return try await APIClient.shared.request(endpoint)
    }
}
