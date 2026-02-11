import Foundation

// MARK: - Frequency

enum Frequency: String, Codable, Sendable {
    case monthly
    case weekly
    case biweekly
    case yearly
}

// MARK: - RecurringExpense

struct RecurringExpense: Codable, Sendable, Identifiable {
    var id: String { templateId }

    let templateId: String
    let expenseName: String
    let amount: Double
    let category: String
    let frequency: Frequency
    let dayOfMonth: Int?
    let dayOfWeek: Int?
    let monthOfYear: Int?
    let lastOfMonth: Bool
    let lastReminded: ExpenseDate?
    let lastUserAction: ExpenseDate?
    let active: Bool
}

// MARK: - RecurringListResponse

struct RecurringListResponse: Codable, Sendable {
    let recurringExpenses: [RecurringExpense]
}

// MARK: - PendingExpense

struct PendingExpense: Codable, Sendable, Identifiable {
    var id: String { pendingId }

    let pendingId: String
    let templateId: String
    let expenseName: String
    let amount: Double
    let date: ExpenseDate
    let category: String
    let awaitingConfirmation: Bool
    let createdAt: String?
}

// MARK: - PendingListResponse

struct PendingListResponse: Codable, Sendable {
    let pendingExpenses: [PendingExpense]
}

// MARK: - PendingConfirmResponse

struct PendingConfirmResponse: Codable, Sendable {
    let success: Bool
    let expenseId: String
    let message: String
}
