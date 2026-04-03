import Foundation
import SwiftUI
import BudgetMaster

// MARK: - Response Models

struct BudgetAPIResponse: Codable {
    let year: Int
    let month: Int
    let month_name: String
    let categories: [BudgetCategoryAPI]
    let total_spending: Double
    let total_cap: Double
    let total_percentage: Double
    let total_remaining: Double
    let excluded_categories: [String]?
    let period_type: String?
    let period_start: String?
    let period_end: String?
    let period_label: String?
    let days_in_period: Int?
    let days_elapsed: Int?
    let monthly_total_cap: Double?
}

struct BudgetCategoryAPI: Codable {
    let category: String
    let spending: Double
    let cap: Double
    let percentage: Double
    let remaining: Double
    let emoji: String
}

struct ExpensesAPIResponse: Codable {
    let year: Int
    let month: Int
    let count: Int
    let expenses: [APIExpense]
}

struct APIExpense: Codable, Identifiable {
    let id: String          // Firestore document ID — returned as "id" by the backend
    let expense_name: String
    let amount: Double
    let date: APIDate
    let category: String
}

struct PendingExpense: Codable, Identifiable {
    var id: String { pending_id }
    let pending_id: String
    let template_id: String?
    let expense_name: String
    let amount: Double
    let date: APIDate
    let category: String
}

struct PendingExpensesResponse: Codable {
    let pending_expenses: [PendingExpense]
}

struct APIDate: Codable {
    let day: Int
    let month: Int
    let year: Int
}

struct CategoriesAPIResponse: Codable {
    let categories: [APICategory]
    let total_monthly_budget: Double?
}

struct APICategory: Codable {
    let category_id: String
    let display_name: String
    let icon: String
    let monthly_cap: Double?
    let color: String?
}

struct ConversationListResponse: Codable {
    let conversations: [ConversationSummary]
}

struct ConversationSummary: Codable {
    let conversation_id: String
    let summary: String?
    let last_activity: String?
}

struct ConversationDetail {
    let conversation_id: String
    let messages: [ConversationMessage]
    let summary: String?
    let deleted_expense_ids: [String]
}

struct RawContentBlock {
    enum BlockType { case text, toolCall }
    let type: BlockType
    let text: String?           // for .text blocks
    let toolName: String?       // for .toolCall blocks
    let toolResultJSON: String? // for .toolCall blocks
}

struct ConversationMessage {
    let role: String
    let content: String
    let timestamp: String?
    let toolCalls: [RawToolCall]
    /// Ordered content blocks preserving the interleaving of text and tool calls.
    /// When present, should be used instead of content + toolCalls for rendering.
    let contentBlocks: [RawContentBlock]?
}

struct RawToolCall {
    let name: String
    let resultJSON: String
}

struct RecurringExpenseAPI: Codable, Identifiable {
    var id: String { template_id }
    let template_id: String
    let expense_name: String
    let amount: Double
    let category: String
    let frequency: String
    let day_of_month: Int?
    let day_of_week: Int?
    let last_of_month: Bool?
    let active: Bool
}

struct RecurringExpensesAPIResponse: Codable {
    let recurring_expenses: [RecurringExpenseAPI]
}

struct MCPExpenseResponse: Codable {
    let success: Bool
    let message: String
    let expense_id: String?
    let expense_name: String?
    let amount: Double?
    let category: String?
    let budget_warning: String?
    let conversation_id: String?
}

// MARK: - SSE Events

enum SSEEvent {
    case conversationId(String)
    case text(String)
    case toolStart(id: String, tool: String)
    case toolEnd(id: String, tool: String, resultJSON: String)
    case done
    case error(String)
}

// MARK: - API Errors

enum APIError: LocalizedError {
    case unauthorized
    case serverError(Int, String)
    case decodingError(Error)
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "Not authenticated. Please sign in again."
        case .serverError(let code, let msg):
            return "Server error \(code): \(msg)"
        case .decodingError(let err):
            return "Failed to decode response: \(err.localizedDescription)"
        case .networkError(let err):
            return "Network error: \(err.localizedDescription)"
        }
    }
}

// MARK: - APIService

actor APIService {
    private let tokenProvider = FirebaseTokenProvider()
    private let decoder = JSONDecoder()

    private func syncClientConfiguration() async throws {
        guard let url = URL(string: AppConfiguration.shared.resolvedBaseURL) else {
            throw APIError.networkError(URLError(.badURL))
        }

        await BudgetMaster.APIClient.shared.setBaseURL(url)
        await BudgetMaster.APIClient.shared.setTokenProvider(tokenProvider)
    }

    private func mapBudgetMasterError(_ error: BudgetMaster.APIError) -> APIError {
        switch error {
        case .invalidURL:
            return .networkError(URLError(.badURL))
        case .unauthorized:
            return .unauthorized
        case .serverError(let code, let message):
            return .serverError(code, message ?? "Unknown server error")
        case .decodingFailed(let error):
            return .decodingError(error)
        case .networkError(let error):
            return .networkError(error)
        case .badRequest(let message):
            return .serverError(400, message)
        case .notFound:
            return .serverError(404, "Not found")
        case .noToken:
            return .unauthorized
        case .sseParsingError(let message):
            return .serverError(500, message)
        }
    }

    private func requestData(
        method: BudgetMaster.HTTPMethod = .get,
        path: String,
        queryItems: [URLQueryItem]? = nil,
        requiresAuth: Bool = true
    ) async throws -> Data {
        try await syncClientConfiguration()

        let endpoint = BudgetMaster.APIEndpoint(
            method: method,
            path: path,
            queryItems: queryItems,
            requiresAuth: requiresAuth
        )

        do {
            return try await BudgetMaster.APIClient.shared.responseData(for: endpoint)
        } catch let error as BudgetMaster.APIError {
            throw mapBudgetMasterError(error)
        } catch {
            throw APIError.networkError(error)
        }
    }

    private func requestData<Body: Encodable & Sendable>(
        method: BudgetMaster.HTTPMethod,
        path: String,
        queryItems: [URLQueryItem]? = nil,
        body: Body,
        requiresAuth: Bool = true
    ) async throws -> Data {
        try await syncClientConfiguration()

        let endpoint = BudgetMaster.APIEndpoint(
            method: method,
            path: path,
            queryItems: queryItems,
            requiresAuth: requiresAuth
        )

        do {
            return try await BudgetMaster.APIClient.shared.responseData(for: endpoint, body: body)
        } catch let error as BudgetMaster.APIError {
            throw mapBudgetMasterError(error)
        } catch {
            throw APIError.networkError(error)
        }
    }

    // MARK: Budget

    func fetchBudget(year: Int? = nil, month: Int? = nil, periodOffset: Int? = nil) async throws -> BudgetAPIResponse {
        var queryItems: [URLQueryItem] = []
        if let periodOffset {
            queryItems.append(URLQueryItem(name: "period_offset", value: "\(periodOffset)"))
        } else {
            if let year { queryItems.append(URLQueryItem(name: "year", value: "\(year)")) }
            if let month { queryItems.append(URLQueryItem(name: "month", value: "\(month)")) }
        }
        let data = try await requestData(
            path: "/budget",
            queryItems: queryItems.isEmpty ? nil : queryItems
        )

        do {
            return try decoder.decode(BudgetAPIResponse.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: Expenses

    func fetchExpenses(year: Int, month: Int, category: String? = nil) async throws -> [APIExpense] {
        var queryItems = [
            URLQueryItem(name: "year", value: "\(year)"),
            URLQueryItem(name: "month", value: "\(month)"),
        ]
        if let category {
            queryItems.append(URLQueryItem(name: "category", value: category))
        }

        let data = try await requestData(path: "/expenses", queryItems: queryItems)

        do {
            let decoded = try decoder.decode(ExpensesAPIResponse.self, from: data)
            return decoded.expenses
        } catch {
            throw APIError.decodingError(error)
        }
    }

    func deleteExpense(id: String) async throws {
        _ = try await requestData(method: .delete, path: "/expenses/\(id)")
    }

    func updateExpense(
        id: String,
        name: String?,
        amount: Double?,
        category: String?,
        date: [String: Int]?
    ) async throws {
        var body: [String: BudgetMaster.AnyCodable] = [:]
        if let name = name { body["expense_name"] = BudgetMaster.AnyCodable(name) }
        if let amount = amount { body["amount"] = BudgetMaster.AnyCodable(amount) }
        if let category = category { body["category"] = BudgetMaster.AnyCodable(category) }
        if let date = date {
            body["date"] = BudgetMaster.AnyCodable(date.mapValues { $0 as Any })
        }

        _ = try await requestData(
            method: .put,
            path: "/expenses/\(id)",
            body: body
        )
    }

    // MARK: Direct Expense Creation

    func createExpense(
        name: String,
        amount: Double,
        category: String,
        date: Date
    ) async throws {
        let cal = Calendar.current
        let body: [String: BudgetMaster.AnyCodable] = [
            "expense_name": BudgetMaster.AnyCodable(name),
            "amount": BudgetMaster.AnyCodable(amount),
            "category": BudgetMaster.AnyCodable(category),
            "date": BudgetMaster.AnyCodable([
                "day": cal.component(.day, from: date),
                "month": cal.component(.month, from: date),
                "year": cal.component(.year, from: date),
            ] as [String: Any]),
        ]

        _ = try await requestData(method: .post, path: "/expenses", body: body)
    }

    // MARK: MCP Expense

    func addExpenseViaMCP(text: String) async throws -> String {
        return try await processExpenseMultipart(text: text).message
    }

    // MARK: Multipart Expense Processing

    func processExpenseMultipart(
        text: String? = nil,
        imageData: Data? = nil,
        audioData: Data? = nil,
        conversationId: String? = nil
    ) async throws -> MCPExpenseResponse {
        try await syncClientConfiguration()

        do {
            let response = try await BudgetMaster.ChatService.processExpense(
                text: text,
                imageData: imageData,
                imageMimeType: imageData == nil ? nil : "image/jpeg",
                audioData: audioData,
                audioFileName: audioData == nil ? nil : "voice.m4a",
                conversationId: conversationId
            )

            return MCPExpenseResponse(
                success: response.success,
                message: response.message,
                expense_id: response.expenseId,
                expense_name: response.expenseName,
                amount: response.amount,
                category: response.category,
                budget_warning: response.budgetWarning,
                conversation_id: response.conversationId
            )
        } catch let error as BudgetMaster.APIError {
            throw mapBudgetMasterError(error)
        } catch {
            throw APIError.networkError(error)
        }
    }

    // MARK: Categories

    func fetchCategories() async throws -> [APICategory] {
        let data = try await requestData(path: "/categories")

        do {
            let decoded = try decoder.decode(CategoriesAPIResponse.self, from: data)
            return decoded.categories
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: Conversations

    func fetchConversations(limit: Int = 10) async throws -> [ConversationSummary] {
        let data = try await requestData(
            path: "/conversations",
            queryItems: [URLQueryItem(name: "limit", value: "\(limit)")]
        )

        do {
            return try decoder.decode(ConversationListResponse.self, from: data).conversations
        } catch {
            throw APIError.decodingError(error)
        }
    }

    func fetchConversation(id: String) async throws -> ConversationDetail {
        let data = try await requestData(path: "/conversations/\(id)")

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw APIError.decodingError(NSError(domain: "parse", code: 0))
        }

        let conversationId = json["conversation_id"] as? String ?? id
        let summary = json["summary"] as? String
        let rawMessages = json["messages"] as? [[String: Any]] ?? []

        let messages: [ConversationMessage] = rawMessages.compactMap { raw in
            guard let role = raw["role"] as? String,
                  let content = raw["content"] as? String else { return nil }
            let timestamp = raw["timestamp"] as? String
            var toolCalls: [RawToolCall] = []
            if let tc = raw["tool_calls"] as? [[String: Any]] {
                toolCalls = tc.compactMap { call in
                    guard let name = call["name"] as? String ?? call["tool"] as? String else { return nil }
                    var resultJSON = "{}"
                    if let result = call["result"],
                       (result is [String: Any] || result is [Any]),
                       let d = try? JSONSerialization.data(withJSONObject: result),
                       let s = String(data: d, encoding: .utf8) { resultJSON = s }
                    return RawToolCall(name: name, resultJSON: resultJSON)
                }
            }

            // Parse ordered content_blocks if present (new format)
            var contentBlocks: [RawContentBlock]?
            if let rawBlocks = raw["content_blocks"] as? [[String: Any]], !rawBlocks.isEmpty {
                contentBlocks = rawBlocks.compactMap { block in
                    let blockType = block["type"] as? String
                    if blockType == "text", let text = block["text"] as? String {
                        return RawContentBlock(type: .text, text: text, toolName: nil, toolResultJSON: nil)
                    } else if blockType == "tool_call", let name = block["name"] as? String {
                        var resultJSON = "{}"
                        if let result = block["result"],
                           (result is [String: Any] || result is [Any]),
                           let d = try? JSONSerialization.data(withJSONObject: result),
                           let s = String(data: d, encoding: .utf8) { resultJSON = s }
                        return RawContentBlock(type: .toolCall, text: nil, toolName: name, toolResultJSON: resultJSON)
                    }
                    return nil
                }
            }

            return ConversationMessage(role: role, content: content, timestamp: timestamp, toolCalls: toolCalls, contentBlocks: contentBlocks)
        }

        let deletedExpenseIds = json["deleted_expense_ids"] as? [String] ?? []
        return ConversationDetail(conversation_id: conversationId, messages: messages, summary: summary, deleted_expense_ids: deletedExpenseIds)
    }

    func verifyExpenses(ids: [String]) async throws -> [String] {
        let data = try await requestData(
            method: .post,
            path: "/expenses/verify",
            body: ["expense_ids": BudgetMaster.AnyCodable(ids)]
        )

        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let existingIds = json["existing_ids"] as? [String] else {
            return []
        }
        return existingIds
    }

    func markExpenseDeleted(conversationId: String, expenseId: String) async throws {
        _ = try await requestData(
            method: .post,
            path: "/conversations/\(conversationId)/deleted-expenses",
            body: ["expense_id": BudgetMaster.AnyCodable(expenseId)]
        )
    }

    func deleteConversation(id: String) async throws {
        _ = try await requestData(method: .delete, path: "/conversations/\(id)")
    }

    // MARK: Pending Expenses

    func fetchPending() async throws -> [PendingExpense] {
        let data = try await requestData(path: "/pending")

        do {
            return try decoder.decode(PendingExpensesResponse.self, from: data).pending_expenses
        } catch {
            throw APIError.decodingError(error)
        }
    }

    func confirmPending(id: String) async throws {
        _ = try await requestData(
            method: .post,
            path: "/pending/\(id)/confirm",
            body: [String: String]()
        )
    }

    func skipPending(id: String) async throws {
        _ = try await requestData(method: .delete, path: "/pending/\(id)")
    }

    // MARK: Recurring Expenses

    func deleteRecurring(id: String) async throws {
        _ = try await requestData(method: .delete, path: "/recurring/\(id)")
    }

    func fetchRecurring() async throws -> [RecurringExpenseAPI] {
        let data = try await requestData(path: "/recurring")

        do {
            return try decoder.decode(RecurringExpensesAPIResponse.self, from: data).recurring_expenses
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: Feedback

    func submitFeedback(type: String, message: String, userEmail: String) async throws {
        let data = try await requestData(
            method: .post,
            path: "/feedback",
            body: [
                "type": BudgetMaster.AnyCodable(type),
                "message": BudgetMaster.AnyCodable(message),
                "user_email": BudgetMaster.AnyCodable(userEmail),
            ]
        )

        // Expect { "status": "ok" } — no further decoding needed beyond a success check.
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              json["status"] as? String == "ok" else {
            let raw = String(data: data, encoding: .utf8) ?? "Unknown response"
            throw APIError.serverError(200, raw)
        }
    }

    // MARK: Server Connection

    func ensureServerConnected() async throws {
        try await syncClientConfiguration()
    }
}

// MARK: - Color Hex Extension

extension Color {
    init?(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        guard Scanner(string: hex).scanHexInt64(&int) else { return nil }
        let r, g, b: Double
        switch hex.count {
        case 6:
            r = Double((int >> 16) & 0xFF) / 255
            g = Double((int >> 8) & 0xFF) / 255
            b = Double(int & 0xFF) / 255
        default:
            return nil
        }
        self.init(red: r, green: g, blue: b)
    }
}

// MARK: - SSE Streaming (nonisolated extension)

extension APIService {
    func streamChat(
        message: String,
        conversationId: String?,
        modelOverride: String? = nil,
        onEvent: @escaping @MainActor (SSEEvent) -> Void
    ) async throws {
        try await syncClientConfiguration()

        do {
            let stream = BudgetMaster.ChatService.streamChat(
                message: message,
                conversationId: conversationId,
                modelOverride: modelOverride
            )

            for try await event in stream {
                let mapped: SSEEvent
                switch event {
                case .conversationId(let id):
                    mapped = .conversationId(id)
                case .text(let content):
                    mapped = .text(content)
                case .toolStart(let id, let name, _):
                    mapped = .toolStart(id: id, tool: name)
                case .toolEnd(let id, let name, let result):
                    var resultJSON = "{}"
                    if let dict = result as? [String: Any],
                       let data = try? JSONSerialization.data(withJSONObject: dict),
                       let json = String(data: data, encoding: .utf8) {
                        resultJSON = json
                    } else if let array = result as? [Any],
                              let data = try? JSONSerialization.data(withJSONObject: array),
                              let json = String(data: data, encoding: .utf8) {
                        resultJSON = json
                    } else if let string = result as? String {
                        resultJSON = string
                    }
                    mapped = .toolEnd(id: id, tool: name, resultJSON: resultJSON)
                case .done:
                    mapped = .done
                case .error(let message):
                    mapped = .error(message)
                }

                await MainActor.run { onEvent(mapped) }
            }
        } catch let error as BudgetMaster.APIError {
            throw mapBudgetMasterError(error)
        }
    }
}
