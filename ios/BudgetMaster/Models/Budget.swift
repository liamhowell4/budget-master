import Foundation

// MARK: - BudgetCategory

struct BudgetCategory: Codable, Sendable, Identifiable {
    var id: String { category }

    let category: String
    let spending: Double
    let cap: Double
    let percentage: Double
    let remaining: Double
    let emoji: String
}

// MARK: - BudgetStatus

struct BudgetStatus: Codable, Sendable {
    let year: Int
    let month: Int
    let monthName: String
    let categories: [BudgetCategory]
    let totalSpending: Double
    let totalCap: Double
    let totalPercentage: Double
    let totalRemaining: Double
    let excludedCategories: [String]
}

// MARK: - BulkBudgetUpdateRequest

struct BulkBudgetUpdateRequest: Codable, Sendable {
    let totalBudget: Double
    let categoryBudgets: [String: Double]
}

// MARK: - BulkBudgetUpdateResponse

struct BulkBudgetUpdateResponse: Codable, Sendable {
    let success: Bool
    let message: String
    let updatedCaps: [String: Double]
}

// MARK: - TotalBudgetResponse

struct TotalBudgetResponse: Codable, Sendable {
    let totalMonthlyBudget: Double
    let allocated: Double
    let available: Double
}

// MARK: - TotalBudgetUpdateRequest

struct TotalBudgetUpdateRequest: Codable, Sendable {
    let totalMonthlyBudget: Double
}

// MARK: - TotalBudgetUpdateResponse

struct TotalBudgetUpdateResponse: Codable, Sendable {
    let success: Bool
    let totalMonthlyBudget: Double
    let otherCap: Double
    let message: String
}
