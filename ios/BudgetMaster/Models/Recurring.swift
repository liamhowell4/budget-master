import Foundation

// MARK: - Frequency

public enum Frequency: String, Codable, Sendable {
    case monthly
    case weekly
    case biweekly
    case yearly
}

// MARK: - RecurringExpense

public struct RecurringExpense: Codable, Sendable, Identifiable {
    public var id: String { templateId }

    public let templateId: String
    public let expenseName: String
    public let amount: Double
    public let category: String
    public let frequency: Frequency
    public let dayOfMonth: Int?
    public let dayOfWeek: Int?
    public let monthOfYear: Int?
    public let lastOfMonth: Bool
    public let lastReminded: ExpenseDate?
    public let lastUserAction: ExpenseDate?
    public let active: Bool
}

// MARK: - RecurringListResponse

public struct RecurringListResponse: Codable, Sendable {
    public let recurringExpenses: [RecurringExpense]
}

// MARK: - PendingExpense

public struct PendingExpense: Codable, Sendable, Identifiable {
    public var id: String { pendingId }

    public let pendingId: String
    public let templateId: String
    public let expenseName: String
    public let amount: Double
    public let date: ExpenseDate
    public let category: String
    public let awaitingConfirmation: Bool
    public let createdAt: String?
}

// MARK: - PendingListResponse

public struct PendingListResponse: Codable, Sendable {
    public let pendingExpenses: [PendingExpense]
}

// MARK: - PendingConfirmResponse

public struct PendingConfirmResponse: Codable, Sendable {
    public let success: Bool
    public let expenseId: String
    public let message: String
}
