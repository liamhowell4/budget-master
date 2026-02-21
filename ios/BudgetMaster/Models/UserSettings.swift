import Foundation

// MARK: - UserSettings

public struct UserSettings: Codable, Sendable {
    public let selectedModel: String

    public init(selectedModel: String) {
        self.selectedModel = selectedModel
    }

    enum CodingKeys: String, CodingKey {
        case selectedModel = "selected_model"
    }
}

// MARK: - UserSettingsUpdateRequest

public struct UserSettingsUpdateRequest: Codable, Sendable {
    public let selectedModel: String

    public init(selectedModel: String) {
        self.selectedModel = selectedModel
    }

    enum CodingKeys: String, CodingKey {
        case selectedModel = "selected_model"
    }
}
