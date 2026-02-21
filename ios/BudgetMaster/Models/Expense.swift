import Foundation

// MARK: - ExpenseDate

public struct ExpenseDate: Codable, Sendable {
    public let day: Int
    public let month: Int
    public let year: Int
}

// MARK: - Expense

public struct Expense: Codable, Sendable, Identifiable {
    public let id: String
    public let expenseName: String
    public let amount: Double
    public let date: ExpenseDate
    public let category: String
    public let timestamp: String?
    public let inputType: String?

    enum CodingKeys: String, CodingKey {
        case id = "expense_id"
        case expenseName = "expense_name"
        case amount, date, category, timestamp
        case inputType = "input_type"
    }
}

// MARK: - ExpensesResponse

public struct ExpensesResponse: Codable, Sendable {
    public let year: Int
    public let month: Int
    public let category: String?
    public let count: Int
    public let expenses: [Expense]
}

// MARK: - ExpenseUpdateRequest

public struct ExpenseUpdateRequest: Codable, Sendable {
    public var expenseName: String?
    public var amount: Double?
    public var category: String?

    public init(expenseName: String? = nil, amount: Double? = nil, category: String? = nil) {
        self.expenseName = expenseName
        self.amount = amount
        self.category = category
    }

    enum CodingKeys: String, CodingKey {
        case expenseName = "expense_name"
        case amount, category
    }
}

// MARK: - ExpenseUpdateResponse

public struct ExpenseUpdateResponse: Codable, Sendable {
    public let success: Bool
    public let expenseId: String
    public let updatedFields: [String: AnyCodable]

    enum CodingKeys: String, CodingKey {
        case success
        case expenseId = "expense_id"
        case updatedFields = "updated_fields"
    }
}

// MARK: - ExpenseDeleteResponse

public struct ExpenseDeleteResponse: Codable, Sendable {
    public let success: Bool
    public let expenseId: String

    enum CodingKeys: String, CodingKey {
        case success
        case expenseId = "expense_id"
    }
}

// MARK: - ExpenseResponse (from /mcp/process_expense)

public struct ExpenseProcessResponse: Codable, Sendable {
    public let success: Bool
    public let message: String
    public let expenseId: String?
    public let expenseName: String?
    public let amount: Double?
    public let category: String?
    public let budgetWarning: String?
    public let conversationId: String?

    enum CodingKeys: String, CodingKey {
        case success, message, amount, category
        case expenseId = "expense_id"
        case expenseName = "expense_name"
        case budgetWarning = "budget_warning"
        case conversationId = "conversation_id"
    }
}
