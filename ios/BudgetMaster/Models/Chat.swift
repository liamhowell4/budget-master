import Foundation

// MARK: - ChatRequest

public struct ChatRequest: Codable, Sendable {
    public let message: String
    public let conversationId: String?

    public init(message: String, conversationId: String? = nil) {
        self.message = message
        self.conversationId = conversationId
    }

    enum CodingKeys: String, CodingKey {
        case message
        case conversationId = "conversation_id"
    }
}

// MARK: - ChatStreamEvent

/// Events received from the SSE `/chat/stream` endpoint.
/// Uses `@unchecked Sendable` because tool args/results contain `Any` from JSON parsing.
public enum ChatStreamEvent: @unchecked Sendable {
    case conversationId(String)
    case toolStart(id: String, name: String, args: [String: Any])
    case toolEnd(id: String, name: String, result: Any)
    case text(String)
    case done
    case error(String)
}

// MARK: - ToolCall (stored in conversation history)

public struct ToolCallStored: Codable, Sendable {
    public let id: String
    public let name: String
    public let args: AnyCodable?
    public let result: AnyCodable?
}

// MARK: - StoredMessage

public struct StoredMessage: Codable, Sendable {
    public let role: String
    public let content: String
    public let timestamp: String?
    public let toolCalls: [ToolCallStored]?

    enum CodingKeys: String, CodingKey {
        case role, content, timestamp
        case toolCalls = "tool_calls"
    }
}
