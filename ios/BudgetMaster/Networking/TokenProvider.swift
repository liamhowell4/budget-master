import Foundation

/// Protocol for providing Firebase Auth ID tokens.
/// Decouples APIClient from FirebaseAuth so mocks can be injected for testing.
protocol TokenProvider: Sendable {
    func getToken() async throws -> String
}

/// Concrete implementation using FirebaseAuth.
/// Uncomment and use once FirebaseAuth SDK is added to the project.
///
/// ```swift
/// import FirebaseAuth
///
/// final class FirebaseTokenProvider: TokenProvider {
///     func getToken() async throws -> String {
///         guard let user = Auth.auth().currentUser else {
///             throw APIError.noToken
///         }
///         return try await user.getIDToken()
///     }
/// }
/// ```

/// Stub token provider for development/testing.
/// Replace with FirebaseTokenProvider in production.
final class StubTokenProvider: TokenProvider {
    private let token: String

    init(token: String = "") {
        self.token = token
    }

    func getToken() async throws -> String {
        guard !token.isEmpty else { throw APIError.noToken }
        return token
    }
}
