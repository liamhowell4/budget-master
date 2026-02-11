import Foundation

// MARK: - ChatRequest

struct ChatRequest: Codable, Sendable {
    let message: String
    let conversationId: String?

    enum CodingKeys: String, CodingKey {
        case message
        case conversationId = "conversation_id"
    }
}

// MARK: - ChatStreamEvent

/// Events received from the SSE `/chat/stream` endpoint.
/// Uses `@unchecked Sendable` because tool args/results contain `Any` from JSON parsing.
enum ChatStreamEvent: @unchecked Sendable {
    case conversationId(String)
    case toolStart(id: String, name: String, args: [String: Any])
    case toolEnd(id: String, name: String, result: Any)
    case text(String)
    case done
    case error(String)
}

// MARK: - ToolCall (stored in conversation history)

struct ToolCallStored: Codable, Sendable {
    let id: String
    let name: String
    let args: AnyCodable?
    let result: AnyCodable?
}

// MARK: - StoredMessage

struct StoredMessage: Codable, Sendable {
    let role: String
    let content: String
    let timestamp: String?
    let toolCalls: [ToolCallStored]?

    enum CodingKeys: String, CodingKey {
        case role, content, timestamp
        case toolCalls = "tool_calls"
    }
}
