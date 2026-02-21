import Foundation

public enum HTTPMethod: String, Sendable {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case delete = "DELETE"
}

public struct APIEndpoint: Sendable {
    public let method: HTTPMethod
    public let path: String
    public let queryItems: [URLQueryItem]?
    public let requiresAuth: Bool

    public init(
        method: HTTPMethod = .get,
        path: String,
        queryItems: [URLQueryItem]? = nil,
        requiresAuth: Bool = true
    ) {
        self.method = method
        self.path = path
        self.queryItems = queryItems
        self.requiresAuth = requiresAuth
    }
}
