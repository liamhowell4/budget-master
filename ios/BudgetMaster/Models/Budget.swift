import Foundation

// MARK: - BudgetCategory

public struct BudgetCategory: Codable, Sendable, Identifiable {
    public var id: String { category }

    public let category: String
    public let spending: Double
    public let cap: Double
    public let percentage: Double
    public let remaining: Double
    public let emoji: String
}

// MARK: - BudgetStatus

public struct BudgetStatus: Codable, Sendable {
    public let year: Int
    public let month: Int
    public let monthName: String
    public let categories: [BudgetCategory]
    public let totalSpending: Double
    public let totalCap: Double
    public let totalPercentage: Double
    public let totalRemaining: Double
    public let excludedCategories: [String]
}

// MARK: - BulkBudgetUpdateRequest

public struct BulkBudgetUpdateRequest: Codable, Sendable {
    public let totalBudget: Double
    public let categoryBudgets: [String: Double]

    public init(totalBudget: Double, categoryBudgets: [String: Double]) {
        self.totalBudget = totalBudget
        self.categoryBudgets = categoryBudgets
    }
}

// MARK: - BulkBudgetUpdateResponse

public struct BulkBudgetUpdateResponse: Codable, Sendable {
    public let success: Bool
    public let message: String
    public let updatedCaps: [String: Double]
}

// MARK: - TotalBudgetResponse

public struct TotalBudgetResponse: Codable, Sendable {
    public let totalMonthlyBudget: Double
    public let allocated: Double
    public let available: Double
}

// MARK: - TotalBudgetUpdateRequest

public struct TotalBudgetUpdateRequest: Codable, Sendable {
    public let totalMonthlyBudget: Double

    public init(totalMonthlyBudget: Double) {
        self.totalMonthlyBudget = totalMonthlyBudget
    }
}

// MARK: - TotalBudgetUpdateResponse

public struct TotalBudgetUpdateResponse: Codable, Sendable {
    public let success: Bool
    public let totalMonthlyBudget: Double
    public let otherCap: Double
    public let message: String
}
