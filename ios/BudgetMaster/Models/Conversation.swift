import Foundation

// MARK: - Conversation

public struct Conversation: Codable, Sendable, Identifiable {
    public var id: String { conversationId }

    public let conversationId: String
    public let createdAt: String?
    public let lastActivity: String?
    public let messages: [StoredMessage]
    public let summary: String?
}

// MARK: - ConversationListItem

public struct ConversationListItem: Codable, Sendable, Identifiable {
    public var id: String { conversationId }

    public let conversationId: String
    public let createdAt: String?
    public let lastActivity: String?
    public let summary: String?
    public let messageCount: Int
    public let firstMessage: String?
}

// MARK: - ConversationListResponse

public struct ConversationListResponse: Codable, Sendable {
    public let conversations: [ConversationListItem]
}

// MARK: - ConversationCreateResponse

public struct ConversationCreateResponse: Codable, Sendable {
    public let conversationId: String
}
