import Foundation

// MARK: - MCPServer

public struct MCPServer: Codable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let path: String
    public let description: String
}

// MARK: - ServerTool

public struct ServerTool: Codable, Sendable {
    public let name: String
    public let description: String?
    public let inputSchema: AnyCodable?

    enum CodingKeys: String, CodingKey {
        case name, description
        case inputSchema = "input_schema"
    }
}

// MARK: - ServerConnectResponse

public struct ServerConnectResponse: Codable, Sendable {
    public let success: Bool
    public let serverId: String
    public let serverName: String
    public let tools: [ServerTool]
}

// MARK: - ServerStatus

public struct ServerStatus: Codable, Sendable {
    public let connected: Bool
    public let serverId: String?
    public let tools: [ServerTool]
}
