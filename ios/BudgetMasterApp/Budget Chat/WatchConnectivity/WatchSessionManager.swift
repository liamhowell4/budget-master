import Foundation
import WatchConnectivity
import FirebaseAuth

/// iOS-side WCSession manager.
/// Activates WCSession on launch, sends the Firebase token to the Watch on activation
/// and on sign-in, and handles `requestToken` messages from the Watch.
@MainActor
final class WatchSessionManager: NSObject, ObservableObject {

    static let shared = WatchSessionManager()

    private override init() {
        super.init()
        guard WCSession.isSupported() else { return }
        WCSession.default.delegate = self
        WCSession.default.activate()
    }

    // MARK: - Token Delivery

    /// Fetch a fresh Firebase token and send it to the Watch via both
    /// `updateApplicationContext` (background) and `sendMessage` (foreground).
    func sendTokenToWatch() {
        guard WCSession.default.activationState == .activated else { return }

        Task {
            guard let user = Auth.auth().currentUser else { return }
            do {
                let token = try await user.getIDToken(forcingRefresh: false)
                let payload: [String: Any] = [
                    "firebaseToken": token,
                    "tokenTimestamp": Date().timeIntervalSince1970
                ]
                try? WCSession.default.updateApplicationContext(payload)
                if WCSession.default.isReachable {
                    WCSession.default.sendMessage(payload, replyHandler: nil, errorHandler: nil)
                }
            } catch {
                NSLog("WatchSessionManager: failed to fetch token — \(error.localizedDescription)")
            }
        }
    }
}

// MARK: - WCSessionDelegate

extension WatchSessionManager: WCSessionDelegate {

    nonisolated func session(
        _ session: WCSession,
        activationDidCompleteWith activationState: WCSessionActivationState,
        error: Error?
    ) {
        guard activationState == .activated else { return }
        Task { @MainActor in self.sendTokenToWatch() }
    }

    nonisolated func sessionDidBecomeInactive(_ session: WCSession) {}

    nonisolated func sessionDidDeactivate(_ session: WCSession) {
        WCSession.default.activate()
    }

    // Watch sent a fire-and-forget requestToken message
    nonisolated func session(_ session: WCSession, didReceiveMessage message: [String: Any]) {
        guard message["requestToken"] as? Bool == true else { return }
        Task { @MainActor in self.sendTokenToWatch() }
    }

    // Watch sent a requestToken message and expects a reply with the token
    nonisolated func session(
        _ session: WCSession,
        didReceiveMessage message: [String: Any],
        replyHandler: @escaping ([String: Any]) -> Void
    ) {
        guard message["requestToken"] as? Bool == true else { return }
        Task { @MainActor in
            guard let user = Auth.auth().currentUser else {
                replyHandler(["error": "notAuthenticated"])
                return
            }
            do {
                let token = try await user.getIDToken(forcingRefresh: true)
                replyHandler([
                    "firebaseToken": token,
                    "tokenTimestamp": Date().timeIntervalSince1970
                ])
            } catch {
                replyHandler(["error": error.localizedDescription])
            }
        }
    }
}
