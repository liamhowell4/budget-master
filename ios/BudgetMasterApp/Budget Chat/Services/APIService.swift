import Foundation
import SwiftUI

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
}

struct ConversationMessage {
    let role: String
    let content: String
    let timestamp: String?
    let toolCalls: [RawToolCall]
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

    private var baseURL: String {
        AppConfiguration.shared.apiBaseURL
    }

    // MARK: Auth

    func authHeaders() async throws -> [String: String] {
        let token = try await tokenProvider.getToken()
        return [
            "Authorization": "Bearer \(token)",
            "Content-Type": "application/json"
        ]
    }

    private func tokenHeader() async throws -> String {
        try await tokenProvider.getToken()
    }

    // MARK: Budget

    func fetchBudget(year: Int? = nil, month: Int? = nil) async throws -> BudgetAPIResponse {
        let headers = try await authHeaders()
        var urlString = "\(baseURL)/budget"
        var queryItems: [String] = []
        if let year { queryItems.append("year=\(year)") }
        if let month { queryItems.append("month=\(month)") }
        if !queryItems.isEmpty { urlString += "?" + queryItems.joined(separator: "&") }
        guard let url = URL(string: urlString) else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        do {
            return try JSONDecoder().decode(BudgetAPIResponse.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: Expenses

    func fetchExpenses(year: Int, month: Int, category: String? = nil) async throws -> [APIExpense] {
        let headers = try await authHeaders()
        var urlString = "\(baseURL)/expenses?year=\(year)&month=\(month)"
        if let category { urlString += "&category=\(category)" }
        guard let url = URL(string: urlString) else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        do {
            let decoded = try JSONDecoder().decode(ExpensesAPIResponse.self, from: data)
            return decoded.expenses
        } catch {
            throw APIError.decodingError(error)
        }
    }

    func deleteExpense(id: String) async throws {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/expenses/\(id)") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)
    }

    func updateExpense(
        id: String,
        name: String?,
        amount: Double?,
        category: String?,
        date: [String: Int]?
    ) async throws {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/expenses/\(id)") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        var body: [String: Any] = [:]
        if let name = name { body["expense_name"] = name }
        if let amount = amount { body["amount"] = amount }
        if let category = category { body["category"] = category }
        if let date = date { body["date"] = date }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)
    }

    // MARK: MCP Expense

    func addExpenseViaMCP(text: String) async throws -> String {
        let token = try await tokenHeader()
        guard let url = URL(string: "\(baseURL)/mcp/process_expense") else {
            throw APIError.networkError(URLError(.badURL))
        }

        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"text\"\r\n\r\n".data(using: .utf8)!)
        body.append(text.data(using: .utf8)!)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        let decoded = try JSONDecoder().decode(MCPExpenseResponse.self, from: data)
        return decoded.message
    }

    // MARK: Multipart Expense Processing

    func processExpenseMultipart(
        text: String? = nil,
        imageData: Data? = nil,
        audioData: Data? = nil,
        conversationId: String? = nil
    ) async throws -> MCPExpenseResponse {
        let token = try await tokenHeader()
        guard let url = URL(string: "\(baseURL)/mcp/process_expense") else {
            throw APIError.networkError(URLError(.badURL))
        }

        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        if let text = text {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"text\"\r\n\r\n".data(using: .utf8)!)
            body.append(text.data(using: .utf8)!)
            body.append("\r\n".data(using: .utf8)!)
        }

        if let imageData = imageData {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"image\"; filename=\"receipt.jpg\"\r\n".data(using: .utf8)!)
            body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
            body.append(imageData)
            body.append("\r\n".data(using: .utf8)!)
        }

        if let audioData = audioData {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"audio\"; filename=\"voice.m4a\"\r\n".data(using: .utf8)!)
            body.append("Content-Type: audio/mp4\r\n\r\n".data(using: .utf8)!)
            body.append(audioData)
            body.append("\r\n".data(using: .utf8)!)
        }

        if let conversationId = conversationId {
            body.append("--\(boundary)\r\n".data(using: .utf8)!)
            body.append("Content-Disposition: form-data; name=\"conversation_id\"\r\n\r\n".data(using: .utf8)!)
            body.append(conversationId.data(using: .utf8)!)
            body.append("\r\n".data(using: .utf8)!)
        }

        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        do {
            return try JSONDecoder().decode(MCPExpenseResponse.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: Categories

    func fetchCategories() async throws -> [APICategory] {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/categories") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        do {
            let decoded = try JSONDecoder().decode(CategoriesAPIResponse.self, from: data)
            return decoded.categories
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: Conversations

    func fetchConversations(limit: Int = 10) async throws -> [ConversationSummary] {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/conversations?limit=\(limit)") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        do {
            return try JSONDecoder().decode(ConversationListResponse.self, from: data).conversations
        } catch {
            throw APIError.decodingError(error)
        }
    }

    func fetchConversation(id: String) async throws -> ConversationDetail {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/conversations/\(id)") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

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
                       let d = try? JSONSerialization.data(withJSONObject: result),
                       let s = String(data: d, encoding: .utf8) { resultJSON = s }
                    return RawToolCall(name: name, resultJSON: resultJSON)
                }
            }
            return ConversationMessage(role: role, content: content, timestamp: timestamp, toolCalls: toolCalls)
        }

        return ConversationDetail(conversation_id: conversationId, messages: messages, summary: summary)
    }

    func deleteConversation(id: String) async throws {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/conversations/\(id)") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }
        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)
    }

    // MARK: Pending Expenses

    func fetchPending() async throws -> [PendingExpense] {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/pending") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        do {
            return try JSONDecoder().decode(PendingExpensesResponse.self, from: data).pending_expenses
        } catch {
            throw APIError.decodingError(error)
        }
    }

    func confirmPending(id: String) async throws {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/pending/\(id)/confirm") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)
    }

    func skipPending(id: String) async throws {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/pending/\(id)") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)
    }

    // MARK: Recurring Expenses

    func deleteRecurring(id: String) async throws {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/recurring/\(id)") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)
    }

    func fetchRecurring() async throws -> [RecurringExpenseAPI] {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/recurring") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        do {
            return try JSONDecoder().decode(RecurringExpensesAPIResponse.self, from: data).recurring_expenses
        } catch {
            throw APIError.decodingError(error)
        }
    }

    // MARK: Feedback

    func submitFeedback(type: String, message: String, userEmail: String) async throws {
        let headers = try await authHeaders()
        guard let url = URL(string: "\(baseURL)/feedback") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        headers.forEach { request.setValue($1, forHTTPHeaderField: $0) }

        let body: [String: Any] = [
            "type": type,
            "message": message,
            "user_email": userEmail
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)

        // Expect { "status": "ok" } — no further decoding needed beyond a success check.
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              json["status"] as? String == "ok" else {
            let raw = String(data: data, encoding: .utf8) ?? "Unknown response"
            throw APIError.serverError(200, raw)
        }
    }

    // MARK: Server Connection

    func ensureServerConnected() async throws {
        let token = try await tokenHeader()
        guard let url = URL(string: "\(baseURL)/connect/expense-server") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let (data, response) = try await URLSession.shared.data(for: request)
        try checkResponse(response, data: data)
    }

    // MARK: Chat Stream Request Builder

    func makeChatStreamRequest(message: String, conversationId: String?, modelOverride: String? = nil) async throws -> URLRequest {
        let token = try await tokenHeader()
        guard let url = URL(string: "\(baseURL)/chat/stream") else {
            throw APIError.networkError(URLError(.badURL))
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        var body: [String: Any] = ["message": message]
        if let conversationId = conversationId {
            body["conversation_id"] = conversationId
        }
        if let modelOverride = modelOverride {
            body["model_override"] = modelOverride
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        return request
    }

    // MARK: Private Helpers

    private func checkResponse(_ response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else { return }
        if http.statusCode == 401 {
            throw APIError.unauthorized
        }
        if http.statusCode >= 400 {
            let message = String(data: data, encoding: .utf8) ?? "Unknown error"
            throw APIError.serverError(http.statusCode, message)
        }
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
    nonisolated func streamChat(
        message: String,
        conversationId: String?,
        modelOverride: String? = nil,
        onEvent: @escaping @MainActor (SSEEvent) -> Void
    ) async throws {
        let request = try await makeChatStreamRequest(message: message, conversationId: conversationId, modelOverride: modelOverride)

        let (bytes, response) = try await URLSession.shared.bytes(for: request)

        if let http = response as? HTTPURLResponse, http.statusCode >= 400 {
            await MainActor.run { onEvent(.error("HTTP \(http.statusCode)")) }
            return
        }

        for try await line in bytes.lines {
            guard line.hasPrefix("data: ") else { continue }
            let payload = String(line.dropFirst(6))

            if payload == "[DONE]" {
                await MainActor.run { onEvent(.done) }
                break
            }

            if payload.hasPrefix("[ERROR]") {
                let msg = String(payload.dropFirst(7)).trimmingCharacters(in: .whitespaces)
                await MainActor.run { onEvent(.error(msg)) }
                break
            }

            guard
                let jsonData = payload.data(using: .utf8),
                let json = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any],
                let type = json["type"] as? String
            else { continue }

            let event: SSEEvent
            switch type {
            case "conversation_id":
                let id = json["conversation_id"] as? String ?? ""
                event = .conversationId(id)
            case "text":
                let content = json["content"] as? String ?? ""
                event = .text(content)
            case "tool_start":
                let id = json["id"] as? String ?? UUID().uuidString
                let tool = json["name"] as? String ?? ""
                event = .toolStart(id: id, tool: tool)
            case "tool_end":
                let id = json["id"] as? String ?? UUID().uuidString
                let tool = json["name"] as? String ?? ""
                var resultJSON = "{}"
                if let result = json["result"],
                   let d = try? JSONSerialization.data(withJSONObject: result),
                   let s = String(data: d, encoding: .utf8) { resultJSON = s }
                event = .toolEnd(id: id, tool: tool, resultJSON: resultJSON)
            default:
                continue
            }

            await MainActor.run { onEvent(event) }
        }
    }
}
