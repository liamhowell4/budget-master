import Foundation

public enum BudgetService {

    /// GET /budget?year=&month=
    public static func getBudgetStatus(
        year: Int? = nil,
        month: Int? = nil
    ) async throws -> BudgetStatus {
        var queryItems: [URLQueryItem] = []
        if let year { queryItems.append(.init(name: "year", value: "\(year)")) }
        if let month { queryItems.append(.init(name: "month", value: "\(month)")) }

        let endpoint = APIEndpoint(
            method: .get,
            path: "/budget",
            queryItems: queryItems.isEmpty ? nil : queryItems
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// PUT /budget-caps/bulk-update
    public static func bulkUpdateBudgetCaps(
        _ request: BulkBudgetUpdateRequest
    ) async throws -> BulkBudgetUpdateResponse {
        let endpoint = APIEndpoint(
            method: .put,
            path: "/budget-caps/bulk-update"
        )
        return try await APIClient.shared.request(endpoint, body: request)
    }

    /// GET /budget/total
    public static func getTotalBudget() async throws -> TotalBudgetResponse {
        let endpoint = APIEndpoint(method: .get, path: "/budget/total")
        return try await APIClient.shared.request(endpoint)
    }

    /// PUT /budget/total
    public static func updateTotalBudget(
        _ amount: Double
    ) async throws -> TotalBudgetUpdateResponse {
        let endpoint = APIEndpoint(method: .put, path: "/budget/total")
        let body = TotalBudgetUpdateRequest(totalMonthlyBudget: amount)
        return try await APIClient.shared.request(endpoint, body: body)
    }
}
