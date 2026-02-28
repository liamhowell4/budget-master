import Combine
import Foundation
import WatchConnectivity
import BudgetMaster

/// Watch-side `TokenProvider` implementation.
///
/// Stores the Firebase token received from the iPhone in `UserDefaults` with a 55-minute TTL.
/// When the token is stale or missing, it requests a fresh one from the phone via WCSession.
@MainActor
final class WatchTokenProvider: NSObject, ObservableObject {

    static let shared = WatchTokenProvider()

    // MARK: - UserDefaults Keys

    private let tokenKey      = "watch.firebase.token"
    private let timestampKey  = "watch.firebase.tokenTimestamp"
    private let tokenTTL: TimeInterval = 55 * 60  // 55 minutes

    // MARK: - Published State

    @Published var hasToken: Bool = false

    private override init() {
        super.init()
        hasToken = (storedToken != nil)
        if WCSession.isSupported() {
            WCSession.default.delegate = self
            WCSession.default.activate()
        }
    }

    // MARK: - Storage

    private var storedToken: String? {
        guard
            let token = UserDefaults.standard.string(forKey: tokenKey),
            let ts    = UserDefaults.standard.object(forKey: timestampKey) as? TimeInterval
        else { return nil }
        let age = Date().timeIntervalSince1970 - ts
        return age < tokenTTL ? token : nil
    }

    private func persist(token: String, timestamp: TimeInterval) {
        UserDefaults.standard.set(token, forKey: tokenKey)
        UserDefaults.standard.set(timestamp, forKey: timestampKey)
        hasToken = true
    }

    // MARK: - Token Request

    private func requestTokenFromPhone() async throws -> String {
        guard WCSession.default.isReachable else {
            throw APIError.noToken
        }
        return try await withCheckedThrowingContinuation { continuation in
            WCSession.default.sendMessage(["requestToken": true]) { [weak self] reply in
                if let token = reply["firebaseToken"] as? String,
                   let timestamp = reply["tokenTimestamp"] as? TimeInterval {
                    Task { @MainActor [weak self] in
                        self?.persist(token: token, timestamp: timestamp)
                    }
                    continuation.resume(returning: token)
                } else {
                    continuation.resume(throwing: APIError.noToken)
                }
            } errorHandler: { error in
                continuation.resume(throwing: APIError.networkError(error))
            }
        }
    }
}

// MARK: - TokenProvider Conformance

extension WatchTokenProvider: TokenProvider {
    /// Returns a valid token, requesting a refresh from the phone if needed.
    func getToken() async throws -> String {
        if let token = storedToken { return token }
        return try await requestTokenFromPhone()
    }
}

// MARK: - WCSessionDelegate

extension WatchTokenProvider: WCSessionDelegate {

    nonisolated func session(
        _ session: WCSession,
        activationDidCompleteWith state: WCSessionActivationState,
        error: Error?
    ) {}

    /// Phone pushed a token update via `updateApplicationContext`.
    nonisolated func session(
        _ session: WCSession,
        didReceiveApplicationContext applicationContext: [String: Any]
    ) {
        guard
            let token = applicationContext["firebaseToken"] as? String,
            let ts    = applicationContext["tokenTimestamp"] as? TimeInterval
        else { return }
        let age = Date().timeIntervalSince1970 - ts
        guard age < 55 * 60 else { return }
        Task { @MainActor [weak self] in self?.persist(token: token, timestamp: ts) }
    }

    /// Phone pushed a token via `sendMessage` (foreground).
    nonisolated func session(
        _ session: WCSession,
        didReceiveMessage message: [String: Any]
    ) {
        guard
            let token = message["firebaseToken"] as? String,
            let ts    = message["tokenTimestamp"] as? TimeInterval
        else { return }
        let age = Date().timeIntervalSince1970 - ts
        guard age < 55 * 60 else { return }
        Task { @MainActor [weak self] in self?.persist(token: token, timestamp: ts) }
    }
}
