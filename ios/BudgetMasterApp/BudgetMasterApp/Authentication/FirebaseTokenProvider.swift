import Foundation
import FirebaseAuth

/// Firebase implementation of TokenProvider protocol
/// This class integrates with Firebase Authentication to provide ID tokens for API requests
public final class FirebaseTokenProvider: TokenProvider {
    
    public init() {}
    
    public func getToken() async throws -> String {
        guard let currentUser = Auth.auth().currentUser else {
            throw TokenProviderError.notAuthenticated
        }
        
        // Force refresh to ensure token is valid
        let token = try await currentUser.getIDToken(forcingRefresh: false)
        return token
    }
    
    public func refreshToken() async throws -> String {
        guard let currentUser = Auth.auth().currentUser else {
            throw TokenProviderError.notAuthenticated
        }
        
        // Force refresh the token
        let token = try await currentUser.getIDToken(forcingRefresh: true)
        return token
    }
}

// MARK: - Errors

public enum TokenProviderError: LocalizedError {
    case notAuthenticated
    case tokenRefreshFailed
    
    public var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "User is not authenticated. Please sign in."
        case .tokenRefreshFailed:
            return "Failed to refresh authentication token."
        }
    }
}
