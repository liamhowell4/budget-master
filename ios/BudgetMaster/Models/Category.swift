import Foundation

// MARK: - ExpenseCategory

public struct ExpenseCategory: Codable, Sendable, Identifiable {
    public var id: String { categoryId }

    public let categoryId: String
    public let displayName: String
    public let icon: String
    public let color: String
    public let monthlyCap: Double
    public let isSystem: Bool
    public let createdAt: String?
    public let sortOrder: Int
    public let excludeFromTotal: Bool
}

// MARK: - CategoriesResponse

public struct CategoriesResponse: Codable, Sendable {
    public let categories: [ExpenseCategory]
    public let totalMonthlyBudget: Double
    public let maxCategories: Int
}

// MARK: - CategoryCreateRequest

public struct CategoryCreateRequest: Codable, Sendable {
    public let displayName: String
    public let icon: String
    public let color: String
    public let monthlyCap: Double

    public init(displayName: String, icon: String, color: String, monthlyCap: Double) {
        self.displayName = displayName
        self.icon = icon
        self.color = color
        self.monthlyCap = monthlyCap
    }
}

// MARK: - CategoryCreateResponse

public struct CategoryCreateResponse: Codable, Sendable {
    public let success: Bool
    public let categoryId: String
    public let message: String
}

// MARK: - CategoryUpdateRequest

public struct CategoryUpdateRequest: Codable, Sendable {
    public var displayName: String?
    public var icon: String?
    public var color: String?
    public var monthlyCap: Double?
    public var sortOrder: Int?
    public var excludeFromTotal: Bool?

    public init(
        displayName: String? = nil,
        icon: String? = nil,
        color: String? = nil,
        monthlyCap: Double? = nil,
        sortOrder: Int? = nil,
        excludeFromTotal: Bool? = nil
    ) {
        self.displayName = displayName
        self.icon = icon
        self.color = color
        self.monthlyCap = monthlyCap
        self.sortOrder = sortOrder
        self.excludeFromTotal = excludeFromTotal
    }
}

// MARK: - CategoryUpdateResponse

public struct CategoryUpdateResponse: Codable, Sendable {
    public let success: Bool
    public let categoryId: String
    public let message: String
}

// MARK: - CategoryDeleteResponse

public struct CategoryDeleteResponse: Codable, Sendable {
    public let success: Bool
    public let categoryId: String
    public let reassignedCount: Int
    public let reassignedTo: String
    public let message: String
}

// MARK: - CategoryReorderRequest

public struct CategoryReorderRequest: Codable, Sendable {
    public let categoryIds: [String]

    public init(categoryIds: [String]) {
        self.categoryIds = categoryIds
    }
}

// MARK: - DefaultCategory

public struct DefaultCategory: Codable, Sendable, Identifiable {
    public var id: String { categoryId }

    public let categoryId: String
    public let displayName: String
    public let icon: String
    public let color: String
    public let description: String
    public let isSystem: Bool
}

// MARK: - CategoryDefaultsResponse

public struct CategoryDefaultsResponse: Codable, Sendable {
    public let defaults: [DefaultCategory]
    public let maxCategories: Int
}

// MARK: - Onboarding

public struct CustomCategoryInput: Codable, Sendable {
    public let displayName: String
    public let icon: String
    public let color: String
    public let monthlyCap: Double

    public init(displayName: String, icon: String, color: String, monthlyCap: Double) {
        self.displayName = displayName
        self.icon = icon
        self.color = color
        self.monthlyCap = monthlyCap
    }
}

public struct OnboardingCompleteRequest: Codable, Sendable {
    public let totalBudget: Double
    public let selectedCategoryIds: [String]
    public let categoryCaps: [String: Double]
    public let customCategories: [CustomCategoryInput]?
    public let excludedCategoryIds: [String]?

    public init(
        totalBudget: Double,
        selectedCategoryIds: [String],
        categoryCaps: [String: Double],
        customCategories: [CustomCategoryInput]?,
        excludedCategoryIds: [String]? = nil
    ) {
        self.totalBudget = totalBudget
        self.selectedCategoryIds = selectedCategoryIds
        self.categoryCaps = categoryCaps
        self.customCategories = customCategories
        self.excludedCategoryIds = excludedCategoryIds
    }
}

public struct OnboardingCompleteResponse: Codable, Sendable {
    public let success: Bool
    public let totalBudget: Double
    public let categoriesCreated: Int
    public let otherCap: Double
    public let message: String
}
