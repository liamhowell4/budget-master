import Foundation

enum CategoryService {

    /// GET /categories
    static func getCategories() async throws -> CategoriesResponse {
        let endpoint = APIEndpoint(method: .get, path: "/categories")
        return try await APIClient.shared.request(endpoint)
    }

    /// POST /categories
    static func createCategory(
        _ request: CategoryCreateRequest
    ) async throws -> CategoryCreateResponse {
        let endpoint = APIEndpoint(method: .post, path: "/categories")
        return try await APIClient.shared.request(endpoint, body: request)
    }

    /// PUT /categories/{id}
    static func updateCategory(
        id: String,
        update: CategoryUpdateRequest
    ) async throws -> CategoryUpdateResponse {
        let endpoint = APIEndpoint(method: .put, path: "/categories/\(id)")
        return try await APIClient.shared.request(endpoint, body: update)
    }

    /// DELETE /categories/{id}?reassign_to=
    static func deleteCategory(
        id: String,
        reassignTo: String = "OTHER"
    ) async throws -> CategoryDeleteResponse {
        let endpoint = APIEndpoint(
            method: .delete,
            path: "/categories/\(id)",
            queryItems: [.init(name: "reassign_to", value: reassignTo)]
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// PUT /categories/reorder
    static func reorderCategories(
        _ categoryIds: [String]
    ) async throws -> SuccessResponse {
        let endpoint = APIEndpoint(method: .put, path: "/categories/reorder")
        let body = CategoryReorderRequest(categoryIds: categoryIds)
        return try await APIClient.shared.request(endpoint, body: body)
    }

    /// GET /categories/defaults (no auth required)
    static func getDefaults() async throws -> CategoryDefaultsResponse {
        let endpoint = APIEndpoint(
            method: .get,
            path: "/categories/defaults",
            requiresAuth: false
        )
        return try await APIClient.shared.request(endpoint)
    }

    /// POST /onboarding/complete
    static func completeOnboarding(
        _ request: OnboardingCompleteRequest
    ) async throws -> OnboardingCompleteResponse {
        let endpoint = APIEndpoint(method: .post, path: "/onboarding/complete")
        return try await APIClient.shared.request(endpoint, body: request)
    }
}
