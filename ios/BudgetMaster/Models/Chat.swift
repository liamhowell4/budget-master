import Foundation

// MARK: - ChatRequest

/// Encoded via `APIClient` with `keyEncodingStrategy = .convertToSnakeCase`.
/// Property names are camelCase; the strategy converts them to snake_case automatically.
/// `conversationId` encodes as `"conversation_id"`, which is what the backend expects.
public struct ChatRequest: Codable, Sendable {
    public let message: String
    public let conversationId: String?

    public init(message: String, conversationId: String? = nil) {
        self.message = message
        self.conversationId = conversationId
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

/// JSON keys: "role", "content", "timestamp", "tool_calls"
/// `APIClient` decodes with `convertFromSnakeCase`: "tool_calls" → "toolCalls".
/// Swift property `toolCalls` matches; no custom CodingKeys needed.
public struct StoredMessage: Codable, Sendable {
    public let role: String
    public let content: String
    public let timestamp: String?
    public let toolCalls: [ToolCallStored]?
}
