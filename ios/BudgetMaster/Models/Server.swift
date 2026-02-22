import Foundation

// MARK: - MCPServer

public struct MCPServer: Codable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let path: String
    public let description: String
}

// MARK: - ServerTool

/// JSON keys: "name", "description", "input_schema"
/// `APIClient` decodes with `convertFromSnakeCase`: "input_schema" → "inputSchema".
/// Swift property `inputSchema` matches; no custom CodingKeys needed.
public struct ServerTool: Codable, Sendable {
    public let name: String
    public let description: String?
    public let inputSchema: AnyCodable?
}

// MARK: - ServerConnectResponse

/// JSON keys: "success", "server_id", "server_name", "tools"
/// convertFromSnakeCase: "server_id" → "serverId", "server_name" → "serverName"
public struct ServerConnectResponse: Codable, Sendable {
    public let success: Bool
    public let serverId: String
    public let serverName: String
    public let tools: [ServerTool]
}

// MARK: - ServerStatus

/// JSON keys: "connected", "server_id", "tools"
/// convertFromSnakeCase: "server_id" → "serverId"
public struct ServerStatus: Codable, Sendable {
    public let connected: Bool
    public let serverId: String?
    public let tools: [ServerTool]
}
