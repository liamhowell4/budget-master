import Foundation

// MARK: - ExpenseDate

public struct ExpenseDate: Codable, Sendable {
    public let day: Int
    public let month: Int
    public let year: Int
}

// MARK: - Expense

/// `APIClient` uses `keyDecodingStrategy = .convertFromSnakeCase`, which converts each
/// incoming JSON key to camelCase before matching against `CodingKeys` raw values.
///
/// The `id` property is a genuine rename: the JSON field `"expense_id"` converts to
/// `"expenseId"`, so we need `case id = "expenseId"` to redirect that into `id`.
/// All other properties whose Swift names match the camelCase form of their JSON keys
/// do not need explicit CodingKeys entries.
public struct Expense: Codable, Sendable, Identifiable {
    public let id: String
    public let expenseName: String
    public let amount: Double
    public let date: ExpenseDate
    public let category: String
    public let timestamp: String?
    public let inputType: String?

    enum CodingKeys: String, CodingKey {
        // Rename: JSON "expense_id" → strategy converts to "expenseId" → mapped to Swift `id`
        case id = "expenseId"
        case expenseName
        case amount, date, category, timestamp
        case inputType
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

/// Encoded via `APIClient` with `keyEncodingStrategy = .convertToSnakeCase`.
/// Property names are camelCase; the strategy converts them to snake_case automatically.
/// No custom CodingKeys needed.
public struct ExpenseUpdateRequest: Codable, Sendable {
    public var expenseName: String?
    public var amount: Double?
    public var category: String?

    public init(expenseName: String? = nil, amount: Double? = nil, category: String? = nil) {
        self.expenseName = expenseName
        self.amount = amount
        self.category = category
    }
}

// MARK: - ExpenseUpdateResponse

/// JSON keys: "success", "expense_id", "updated_fields"
/// convertFromSnakeCase: "expense_id" → "expenseId", "updated_fields" → "updatedFields"
/// Property names already match; no custom CodingKeys needed.
public struct ExpenseUpdateResponse: Codable, Sendable {
    public let success: Bool
    public let expenseId: String
    public let updatedFields: [String: AnyCodable]
}

// MARK: - ExpenseDeleteResponse

/// JSON keys: "success", "expense_id"
/// convertFromSnakeCase: "expense_id" → "expenseId"
public struct ExpenseDeleteResponse: Codable, Sendable {
    public let success: Bool
    public let expenseId: String
}

// MARK: - ExpenseProcessResponse (from /mcp/process_expense)

/// JSON keys: "success", "message", "expense_id", "expense_name",
///            "amount", "category", "budget_warning", "conversation_id"
/// convertFromSnakeCase handles all snake_case → camelCase conversions.
public struct ExpenseProcessResponse: Codable, Sendable {
    public let success: Bool
    public let message: String
    public let expenseId: String?
    public let expenseName: String?
    public let amount: Double?
    public let category: String?
    public let budgetWarning: String?
    public let conversationId: String?
}
