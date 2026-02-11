import Foundation

// MARK: - Conversation

struct Conversation: Codable, Sendable, Identifiable {
    var id: String { conversationId }

    let conversationId: String
    let createdAt: String?
    let lastActivity: String?
    let messages: [StoredMessage]
    let summary: String?
}

// MARK: - ConversationListItem

struct ConversationListItem: Codable, Sendable, Identifiable {
    var id: String { conversationId }

    let conversationId: String
    let createdAt: String?
    let lastActivity: String?
    let summary: String?
    let messageCount: Int
    let firstMessage: String?
}

// MARK: - ConversationListResponse

struct ConversationListResponse: Codable, Sendable {
    let conversations: [ConversationListItem]
}

// MARK: - ConversationCreateResponse

struct ConversationCreateResponse: Codable, Sendable {
    let conversationId: String
}
