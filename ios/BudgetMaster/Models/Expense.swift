import Foundation

// MARK: - ExpenseDate

struct ExpenseDate: Codable, Sendable {
    let day: Int
    let month: Int
    let year: Int
}

// MARK: - Expense

struct Expense: Codable, Sendable, Identifiable {
    let id: String
    let expenseName: String
    let amount: Double
    let date: ExpenseDate
    let category: String
    let timestamp: String?
    let inputType: String?

    enum CodingKeys: String, CodingKey {
        case id = "expense_id"
        case expenseName = "expense_name"
        case amount, date, category, timestamp
        case inputType = "input_type"
    }
}

// MARK: - ExpensesResponse

struct ExpensesResponse: Codable, Sendable {
    let year: Int
    let month: Int
    let category: String?
    let count: Int
    let expenses: [Expense]
}

// MARK: - ExpenseUpdateRequest

struct ExpenseUpdateRequest: Codable, Sendable {
    var expenseName: String?
    var amount: Double?
    var category: String?

    enum CodingKeys: String, CodingKey {
        case expenseName = "expense_name"
        case amount, category
    }
}

// MARK: - ExpenseUpdateResponse

struct ExpenseUpdateResponse: Codable, Sendable {
    let success: Bool
    let expenseId: String
    let updatedFields: [String: AnyCodable]

    enum CodingKeys: String, CodingKey {
        case success
        case expenseId = "expense_id"
        case updatedFields = "updated_fields"
    }
}

// MARK: - ExpenseDeleteResponse

struct ExpenseDeleteResponse: Codable, Sendable {
    let success: Bool
    let expenseId: String

    enum CodingKeys: String, CodingKey {
        case success
        case expenseId = "expense_id"
    }
}

// MARK: - ExpenseResponse (from /mcp/process_expense)

struct ExpenseProcessResponse: Codable, Sendable {
    let success: Bool
    let message: String
    let expenseId: String?
    let expenseName: String?
    let amount: Double?
    let category: String?
    let budgetWarning: String?
    let conversationId: String?

    enum CodingKeys: String, CodingKey {
        case success, message, amount, category
        case expenseId = "expense_id"
        case expenseName = "expense_name"
        case budgetWarning = "budget_warning"
        case conversationId = "conversation_id"
    }
}
