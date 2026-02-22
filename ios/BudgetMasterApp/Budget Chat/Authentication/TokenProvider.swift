import Foundation

/// Protocol for providing authentication tokens to API clients
public protocol TokenProvider {
    /// Get the current authentication token
    func getToken() async throws -> String
    
    /// Force refresh the authentication token
    func refreshToken() async throws -> String
}
