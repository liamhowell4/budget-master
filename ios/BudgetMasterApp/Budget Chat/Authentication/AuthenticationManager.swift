import Foundation
import FirebaseAuth
import FirebaseCore
import GoogleSignIn
import AuthenticationServices
import CryptoKit
import UIKit

/// Manages Firebase Authentication state and provides user authentication
@MainActor
class AuthenticationManager: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    @Published var errorMessage: String?
    @Published var isLoading = true // true until Firebase resolves the initial auth state

    private var authStateHandle: AuthStateDidChangeListenerHandle?

    // Held across the async Apple Sign-In flow; must survive from request → delegate callback
    private var currentNonce: String?

    init() {
        print("🔐 AuthenticationManager: init() called")
        setupAuthStateListener()

        // Safety timeout: if Firebase doesn't respond in 5 seconds, stop loading
        Task {
            try? await Task.sleep(nanoseconds: 5_000_000_000) // 5 seconds
            if isLoading {
                print("⚠️ AuthenticationManager: Timeout reached, forcing isLoading = false")
                self.isLoading = false
            }
        }
    }

    deinit {
        if let handle = authStateHandle {
            Auth.auth().removeStateDidChangeListener(handle)
        }
    }

    private func setupAuthStateListener() {
        print("🔐 AuthenticationManager: setting up Firebase auth state listener...")
        authStateHandle = Auth.auth().addStateDidChangeListener { [weak self] _, user in
            print("🔐 AuthenticationManager: auth state changed — user: \(user?.uid ?? "nil")")
            Task { @MainActor in
                self?.isAuthenticated = user != nil
                if let user = user {
                    self?.currentUser = User(
                        id: user.uid,
                        email: user.email ?? "",
                        displayName: user.displayName
                    )
                } else {
                    self?.currentUser = nil
                }
                // Mark initial auth resolution complete
                print("🔐 AuthenticationManager: isLoading = false, isAuthenticated = \(self?.isAuthenticated ?? false)")
                self?.isLoading = false
            }
        }
    }

    // MARK: - Email / Password Authentication

    func signIn(email: String, password: String) async {
        isLoading = true
        errorMessage = nil

        do {
            let result = try await Auth.auth().signIn(withEmail: email, password: password)
            currentUser = User(
                id: result.user.uid,
                email: result.user.email ?? "",
                displayName: result.user.displayName
            )
            isAuthenticated = true
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func signUp(email: String, password: String, displayName: String) async {
        isLoading = true
        errorMessage = nil

        do {
            let result = try await Auth.auth().createUser(withEmail: email, password: password)

            // Update display name
            let changeRequest = result.user.createProfileChangeRequest()
            changeRequest.displayName = displayName
            try await changeRequest.commitChanges()

            currentUser = User(
                id: result.user.uid,
                email: result.user.email ?? "",
                displayName: displayName
            )
            isAuthenticated = true
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    // MARK: - Google Sign-In

    func signInWithGoogle() async {
        isLoading = true
        errorMessage = nil

        guard let clientID = FirebaseApp.app()?.options.clientID else {
            errorMessage = "Google Sign-In configuration error."
            isLoading = false
            return
        }

        let config = GIDConfiguration(clientID: clientID)
        GIDSignIn.sharedInstance.configuration = config

        // Locate the root view controller to present the Google sign-in sheet from
        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene,
              let rootVC = windowScene.windows.first?.rootViewController else {
            errorMessage = "Unable to locate root view controller."
            isLoading = false
            return
        }

        do {
            let result = try await GIDSignIn.sharedInstance.signIn(withPresenting: rootVC)
            guard let idToken = result.user.idToken?.tokenString else {
                errorMessage = "Google Sign-In failed: missing ID token."
                isLoading = false
                return
            }
            let accessToken = result.user.accessToken.tokenString
            let credential = GoogleAuthProvider.credential(withIDToken: idToken, accessToken: accessToken)
            try await Auth.auth().signIn(with: credential)
            // Auth state listener will update isAuthenticated and currentUser
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }

    // MARK: - Apple Sign-In

    func signInWithApple() async {
        isLoading = true
        errorMessage = nil

        let nonce = randomNonceString()
        currentNonce = nonce

        let appleIDProvider = ASAuthorizationAppleIDProvider()
        let request = appleIDProvider.createRequest()
        request.requestedScopes = [.fullName, .email]
        request.nonce = sha256(nonce)

        // Bridge the delegate-based ASAuthorizationController into async/await using a continuation
        do {
            let credential = try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<ASAuthorizationAppleIDCredential, Error>) in
                let delegate = AppleSignInCoordinator(continuation: continuation)
                let controller = ASAuthorizationController(authorizationRequests: [request])
                controller.delegate = delegate
                controller.presentationContextProvider = delegate
                // Retain the delegate for the duration of the presentation
                objc_setAssociatedObject(controller, &AppleSignInCoordinator.associatedKey, delegate, .OBJC_ASSOCIATION_RETAIN)
                controller.performRequests()
            }

            guard let rawNonce = currentNonce else {
                errorMessage = "Apple Sign-In failed: nonce mismatch."
                isLoading = false
                return
            }

            guard let idTokenData = credential.identityToken,
                  let idTokenString = String(data: idTokenData, encoding: .utf8) else {
                errorMessage = "Apple Sign-In failed: missing identity token."
                isLoading = false
                return
            }

            let firebaseCredential = OAuthProvider.appleCredential(
                withIDToken: idTokenString,
                rawNonce: rawNonce,
                fullName: credential.fullName
            )
            try await Auth.auth().signIn(with: firebaseCredential)
            // Auth state listener will update isAuthenticated and currentUser
        } catch {
            // ASAuthorizationError.canceled means the user dismissed — don't surface as error
            let nsError = error as NSError
            if nsError.domain == ASAuthorizationError.errorDomain,
               nsError.code == ASAuthorizationError.canceled.rawValue {
                isLoading = false
                return
            }
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }

    // MARK: - GitHub Sign-In

    func signInWithGitHub() async {
        isLoading = true
        errorMessage = nil

        let provider = OAuthProvider(providerID: "github.com")
        provider.scopes = ["user:email"]

        do {
            // credential(with:) uses ASWebAuthenticationSession internally when passed nil
            let authCredential = try await provider.credential(with: nil)
            try await Auth.auth().signIn(with: authCredential)
            // Auth state listener will update isAuthenticated and currentUser
        } catch {
            // ASWebAuthenticationSession cancellation — don't surface as error
            let nsError = error as NSError
            if nsError.domain == ASAuthorizationError.errorDomain,
               nsError.code == ASAuthorizationError.canceled.rawValue {
                isLoading = false
                return
            }
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }

    // MARK: - Profile Management

    /// The authentication provider for the current user (password, google.com, apple.com, github.com)
    var authProvider: String {
        Auth.auth().currentUser?.providerData.first?.providerID ?? "unknown"
    }

    func updateDisplayName(_ name: String) async throws {
        guard let firebaseUser = Auth.auth().currentUser else {
            throw AuthenticationError.notAuthenticated
        }
        let changeRequest = firebaseUser.createProfileChangeRequest()
        changeRequest.displayName = name
        try await changeRequest.commitChanges()

        // Update local state
        currentUser = User(
            id: firebaseUser.uid,
            email: firebaseUser.email ?? "",
            displayName: name
        )
    }

    func updatePassword(currentPassword: String, newPassword: String) async throws {
        guard let firebaseUser = Auth.auth().currentUser,
              let email = firebaseUser.email else {
            throw AuthenticationError.notAuthenticated
        }

        // Re-authenticate before changing password
        let credential = EmailAuthProvider.credential(withEmail: email, password: currentPassword)
        try await firebaseUser.reauthenticate(with: credential)

        // Update password
        try await firebaseUser.updatePassword(to: newPassword)
    }

    func signOut() {
        do {
            try Auth.auth().signOut()
            GIDSignIn.sharedInstance.signOut()
            isAuthenticated = false
            currentUser = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func resetPassword(email: String) async {
        isLoading = true
        errorMessage = nil

        do {
            try await Auth.auth().sendPasswordReset(withEmail: email)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    /// Get the current Firebase ID token for API authentication
    func getIdToken() async throws -> String {
        guard let firebaseUser = Auth.auth().currentUser else {
            throw AuthenticationError.notAuthenticated
        }
        return try await firebaseUser.getIDToken()
    }

    // MARK: - Apple Sign-In Nonce Helpers

    /// Generates a cryptographically random nonce string of the given byte length.
    private func randomNonceString(length: Int = 32) -> String {
        var randomBytes = [UInt8](repeating: 0, count: length)
        let errorCode = SecRandomCopyBytes(kSecRandomDefault, randomBytes.count, &randomBytes)
        if errorCode != errSecSuccess {
            fatalError("Unable to generate nonce: SecRandomCopyBytes failed with OSStatus \(errorCode).")
        }
        let charset: [Character] = Array("0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._")
        let nonce = randomBytes.map { byte in
            // Pick a random character from the charset using the random byte
            charset[Int(byte) % charset.count]
        }
        return String(nonce)
    }

    /// Returns a SHA-256 hash of the input string, as a lowercase hex string.
    private func sha256(_ input: String) -> String {
        let inputData = Data(input.utf8)
        let hashedData = SHA256.hash(data: inputData)
        return hashedData.compactMap { String(format: "%02x", $0) }.joined()
    }
}

// MARK: - Apple Sign-In Coordinator

/// A helper class that bridges ASAuthorizationControllerDelegate to an async continuation.
/// It is retained by the ASAuthorizationController for the duration of the presentation
/// via objc_setAssociatedObject so neither the controller nor the coordinator is prematurely
/// deallocated before the callback fires.
private final class AppleSignInCoordinator: NSObject,
                                             ASAuthorizationControllerDelegate,
                                             ASAuthorizationControllerPresentationContextProviding {

    // Key used for objc_setAssociatedObject retention
    static var associatedKey: UInt8 = 0

    private let continuation: CheckedContinuation<ASAuthorizationAppleIDCredential, Error>

    init(continuation: CheckedContinuation<ASAuthorizationAppleIDCredential, Error>) {
        self.continuation = continuation
    }

    // MARK: ASAuthorizationControllerDelegate

    func authorizationController(
        controller: ASAuthorizationController,
        didCompleteWithAuthorization authorization: ASAuthorization
    ) {
        guard let appleCredential = authorization.credential as? ASAuthorizationAppleIDCredential else {
            continuation.resume(throwing: AuthenticationError.invalidCredential)
            return
        }
        continuation.resume(returning: appleCredential)
    }

    func authorizationController(
        controller: ASAuthorizationController,
        didCompleteWithError error: Error
    ) {
        continuation.resume(throwing: error)
    }

    // MARK: ASAuthorizationControllerPresentationContextProviding

    func presentationAnchor(for controller: ASAuthorizationController) -> ASPresentationAnchor {
        // Walk connected scenes from most-active to least-active and return the key window.
        // UIWindowScene.keyWindow (iOS 15+) is the correct, non-deprecated API.
        // We never return a bare UIWindow() — a detached window with no scene will itself
        // trigger ASAuthorizationError 1000 because AuthenticationServices cannot present
        // its sheet from a window that has no scene attachment.
        let scenes = UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }

        // Prefer the foreground-active scene with a key window.
        if let window = scenes
            .first(where: { $0.activationState == .foregroundActive })?
            .keyWindow {
            return window
        }

        // Fall back to any foreground scene that has a key window (covers foreground-inactive).
        if let window = scenes
            .first(where: { $0.activationState == .foregroundInactive })?
            .keyWindow {
            return window
        }

        // Last resort: any scene's key window. This should never be reached in practice,
        // but is safer than constructing a detached UIWindow().
        if let window = scenes.compactMap({ $0.keyWindow }).first {
            return window
        }

        // Absolute fallback — construct a window attached to the first available scene
        // so AuthenticationServices can at least derive a scene from the window's windowScene.
        if let scene = scenes.first {
            let fallback = UIWindow(windowScene: scene)
            return fallback
        }

        // This path is unreachable in a running app — there are always connected scenes.
        fatalError("No connected UIWindowScenes found")
    }
}

// MARK: - User Model

struct User: Identifiable, Codable {
    let id: String
    let email: String
    let displayName: String?
}

// MARK: - Errors

enum AuthenticationError: LocalizedError {
    case notAuthenticated
    case invalidCredential

    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "User is not authenticated"
        case .invalidCredential:
            return "Invalid credential received from Apple."
        }
    }
}
