import Foundation

// MARK: - MCPServer

struct MCPServer: Codable, Sendable, Identifiable {
    let id: String
    let name: String
    let path: String
    let description: String
}

// MARK: - ServerTool

struct ServerTool: Codable, Sendable {
    let name: String
    let description: String?
    let inputSchema: AnyCodable?

    enum CodingKeys: String, CodingKey {
        case name, description
        case inputSchema = "input_schema"
    }
}

// MARK: - ServerConnectResponse

struct ServerConnectResponse: Codable, Sendable {
    let success: Bool
    let serverId: String
    let serverName: String
    let tools: [ServerTool]
}

// MARK: - ServerStatus

struct ServerStatus: Codable, Sendable {
    let connected: Bool
    let serverId: String?
    let tools: [ServerTool]
}
