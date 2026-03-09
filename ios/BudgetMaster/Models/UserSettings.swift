import Foundation

// MARK: - UserSettings

/// Decoded via `APIClient`, which uses `keyDecodingStrategy = .convertFromSnakeCase`.
/// Do NOT add custom `CodingKeys` here — the automatic strategy converts the JSON
/// key `"selected_model"` → `"selectedModel"` and matches the Swift property name
/// directly. An explicit `CodingKeys` with raw value `"selected_model"` would
/// override the strategy and cause a `keyNotFound` decoding error because the
/// strategy converts the incoming key first, then compares against raw values.
public struct UserSettings: Codable, Sendable {
    public let selectedModel: String
    public let budgetPeriodType: String
    public let budgetMonthStartDay: Int
    public let budgetWeekStartDay: String
    public let budgetBiweeklyAnchor: String

    public init(
        selectedModel: String,
        budgetPeriodType: String = "monthly",
        budgetMonthStartDay: Int = 1,
        budgetWeekStartDay: String = "Monday",
        budgetBiweeklyAnchor: String = "2024-01-01"
    ) {
        self.selectedModel = selectedModel
        self.budgetPeriodType = budgetPeriodType
        self.budgetMonthStartDay = budgetMonthStartDay
        self.budgetWeekStartDay = budgetWeekStartDay
        self.budgetBiweeklyAnchor = budgetBiweeklyAnchor
    }
}

// MARK: - UserSettingsUpdateRequest

/// Encoded via `APIClient`, which uses `keyEncodingStrategy = .convertToSnakeCase`.
/// Do NOT add custom `CodingKeys` here — the strategy converts the Swift property
/// name `selectedModel` → `"selected_model"` automatically.
public struct UserSettingsUpdateRequest: Codable, Sendable {
    public let selectedModel: String?
    public let budgetPeriodType: String?
    public let budgetMonthStartDay: Int?
    public let budgetWeekStartDay: String?
    public let budgetBiweeklyAnchor: String?

    public init(
        selectedModel: String? = nil,
        budgetPeriodType: String? = nil,
        budgetMonthStartDay: Int? = nil,
        budgetWeekStartDay: String? = nil,
        budgetBiweeklyAnchor: String? = nil
    ) {
        self.selectedModel = selectedModel
        self.budgetPeriodType = budgetPeriodType
        self.budgetMonthStartDay = budgetMonthStartDay
        self.budgetWeekStartDay = budgetWeekStartDay
        self.budgetBiweeklyAnchor = budgetBiweeklyAnchor
    }
}
