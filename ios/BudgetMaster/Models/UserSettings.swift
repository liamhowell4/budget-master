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

    public init(selectedModel: String) {
        self.selectedModel = selectedModel
    }
}

// MARK: - UserSettingsUpdateRequest

/// Encoded via `APIClient`, which uses `keyEncodingStrategy = .convertToSnakeCase`.
/// Do NOT add custom `CodingKeys` here — the strategy converts the Swift property
/// name `selectedModel` → `"selected_model"` automatically.
public struct UserSettingsUpdateRequest: Codable, Sendable {
    public let selectedModel: String

    public init(selectedModel: String) {
        self.selectedModel = selectedModel
    }
}
