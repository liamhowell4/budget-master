import Foundation

enum HTTPMethod: String, Sendable {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case delete = "DELETE"
}

struct APIEndpoint: Sendable {
    let method: HTTPMethod
    let path: String
    let queryItems: [URLQueryItem]?
    let requiresAuth: Bool

    init(
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
