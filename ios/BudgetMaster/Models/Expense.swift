import Foundation

// MARK: - ExpenseDate

public struct ExpenseDate: Codable, Sendable {
    public let day: Int
    public let month: Int
    public let year: Int
}

// MARK: - Expense

/// `/expenses` responses have historically used `id`, while some mutation responses
/// use `expense_id`. Decode both so shared callers like the watch app can consume
/// either shape safely.
public struct Expense: Codable, Sendable, Identifiable {
    public let id: String
    public let expenseName: String
    public let amount: Double
    public let date: ExpenseDate
    public let category: String
    public let timestamp: String?
    public let inputType: String?
    public let notes: String?

    enum CodingKeys: String, CodingKey {
        case id
        case expenseId = "expenseId"
        case expenseName
        case amount, date, category, timestamp, notes
        case inputType
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        if let explicitId = try container.decodeIfPresent(String.self, forKey: .id) {
            id = explicitId
        } else if let expenseId = try container.decodeIfPresent(String.self, forKey: .expenseId) {
            id = expenseId
        } else {
            throw DecodingError.keyNotFound(
                CodingKeys.id,
                DecodingError.Context(codingPath: decoder.codingPath, debugDescription: "Expected id or expense_id")
            )
        }

        expenseName = try container.decode(String.self, forKey: .expenseName)
        amount = try container.decode(Double.self, forKey: .amount)
        date = try container.decode(ExpenseDate.self, forKey: .date)
        category = try container.decode(String.self, forKey: .category)
        timestamp = try container.decodeIfPresent(String.self, forKey: .timestamp)
        inputType = try container.decodeIfPresent(String.self, forKey: .inputType)
        notes = try container.decodeIfPresent(String.self, forKey: .notes)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(expenseName, forKey: .expenseName)
        try container.encode(amount, forKey: .amount)
        try container.encode(date, forKey: .date)
        try container.encode(category, forKey: .category)
        try container.encodeIfPresent(timestamp, forKey: .timestamp)
        try container.encodeIfPresent(inputType, forKey: .inputType)
        try container.encodeIfPresent(notes, forKey: .notes)
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
