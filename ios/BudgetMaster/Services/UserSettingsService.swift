import Foundation

public enum UserSettingsService {

    /// GET /user/settings
    public static func getSettings() async throws -> UserSettings {
        let endpoint = APIEndpoint(method: .get, path: "/user/settings")
        return try await APIClient.shared.request(endpoint)
    }

    /// PUT /user/settings
    public static func updateModel(_ model: String) async throws -> UserSettings {
        let endpoint = APIEndpoint(method: .put, path: "/user/settings")
        let body = UserSettingsUpdateRequest(selectedModel: model)
        return try await APIClient.shared.request(endpoint, body: body)
    }
}
