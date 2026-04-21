import Foundation

// MARK: - MonthStartDay

/// Represents the day on which the monthly budget period starts.
/// Serializes to either an Int (1–28) or the string "last" in JSON.
public enum MonthStartDay: Codable, Equatable, Hashable, Sendable {
    case day(Int)   // 1...28
    case last

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        // Try decoding as the string "last" first.
        if let str = try? container.decode(String.self) {
            guard str == "last" else {
                throw DecodingError.dataCorruptedError(
                    in: container,
                    debugDescription: "MonthStartDay string value must be \"last\", got \"\(str)\""
                )
            }
            self = .last
            return
        }
        // Otherwise expect an integer.
        let n = try container.decode(Int.self)
        guard (1...28).contains(n) else {
            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "MonthStartDay integer must be 1–28, got \(n)"
            )
        }
        self = .day(n)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .last:
            try container.encode("last")
        case .day(let n):
            try container.encode(n)
        }
    }
}

// MARK: - UserSettings

/// Decoded via `APIClient`, which uses `keyDecodingStrategy = .convertFromSnakeCase`.
/// Do NOT add custom `CodingKeys` here — the automatic strategy converts the JSON
/// key `"selected_model"` → `"selectedModel"` and matches the Swift property name
/// directly. An explicit `CodingKeys` with raw value `"selected_model"` would
/// override the strategy and cause a `keyNotFound` decoding error because the
/// strategy converts the incoming key first, then compares against raw values.
public struct UserSettings: Codable, Sendable {
    public let selectedModel: String
    public let budgetMonthStartDay: MonthStartDay

    public init(
        selectedModel: String,
        budgetMonthStartDay: MonthStartDay = .day(1)
    ) {
        self.selectedModel = selectedModel
        self.budgetMonthStartDay = budgetMonthStartDay
    }
}

// MARK: - UserSettingsUpdateRequest

/// Encoded via `APIClient`, which uses `keyEncodingStrategy = .convertToSnakeCase`.
/// Do NOT add custom `CodingKeys` here — the strategy converts the Swift property
/// name `selectedModel` → `"selected_model"` automatically.
public struct UserSettingsUpdateRequest: Codable, Sendable {
    public let selectedModel: String?
    public let budgetMonthStartDay: MonthStartDay?

    public init(
        selectedModel: String? = nil,
        budgetMonthStartDay: MonthStartDay? = nil
    ) {
        self.selectedModel = selectedModel
        self.budgetMonthStartDay = budgetMonthStartDay
    }
}
