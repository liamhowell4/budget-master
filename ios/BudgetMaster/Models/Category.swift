import Foundation

// MARK: - Category

struct Category: Codable, Sendable, Identifiable {
    var id: String { categoryId }

    let categoryId: String
    let displayName: String
    let icon: String
    let color: String
    let monthlyCap: Double
    let isSystem: Bool
    let createdAt: String?
    let sortOrder: Int
    let excludeFromTotal: Bool
}

// MARK: - CategoriesResponse

struct CategoriesResponse: Codable, Sendable {
    let categories: [Category]
    let totalMonthlyBudget: Double
    let maxCategories: Int
}

// MARK: - CategoryCreateRequest

struct CategoryCreateRequest: Codable, Sendable {
    let displayName: String
    let icon: String
    let color: String
    let monthlyCap: Double
}

// MARK: - CategoryCreateResponse

struct CategoryCreateResponse: Codable, Sendable {
    let success: Bool
    let categoryId: String
    let message: String
}

// MARK: - CategoryUpdateRequest

struct CategoryUpdateRequest: Codable, Sendable {
    var displayName: String?
    var icon: String?
    var color: String?
    var monthlyCap: Double?
    var sortOrder: Int?
    var excludeFromTotal: Bool?
}

// MARK: - CategoryUpdateResponse

struct CategoryUpdateResponse: Codable, Sendable {
    let success: Bool
    let categoryId: String
    let message: String
}

// MARK: - CategoryDeleteResponse

struct CategoryDeleteResponse: Codable, Sendable {
    let success: Bool
    let categoryId: String
    let reassignedCount: Int
    let reassignedTo: String
    let message: String
}

// MARK: - CategoryReorderRequest

struct CategoryReorderRequest: Codable, Sendable {
    let categoryIds: [String]
}

// MARK: - DefaultCategory

struct DefaultCategory: Codable, Sendable, Identifiable {
    var id: String { categoryId }

    let categoryId: String
    let displayName: String
    let icon: String
    let color: String
    let description: String
    let isSystem: Bool
}

// MARK: - CategoryDefaultsResponse

struct CategoryDefaultsResponse: Codable, Sendable {
    let defaults: [DefaultCategory]
    let maxCategories: Int
}

// MARK: - Onboarding

struct CustomCategoryInput: Codable, Sendable {
    let displayName: String
    let icon: String
    let color: String
    let monthlyCap: Double
}

struct OnboardingCompleteRequest: Codable, Sendable {
    let totalBudget: Double
    let selectedCategoryIds: [String]
    let categoryCaps: [String: Double]
    let customCategories: [CustomCategoryInput]?
}

struct OnboardingCompleteResponse: Codable, Sendable {
    let success: Bool
    let totalBudget: Double
    let categoriesCreated: Int
    let otherCap: Double
    let message: String
}
