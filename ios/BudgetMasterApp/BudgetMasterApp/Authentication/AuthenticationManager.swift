import Foundation
import FirebaseAuth
import Combine

/// Manages Firebase Authentication state and provides user authentication
@MainActor
class AuthenticationManager: ObservableObject {
    @Published var isAuthenticated = false
    @Published var currentUser: User?
    @Published var errorMessage: String?
    @Published var isLoading = false
    
    private var authStateHandle: AuthStateDidChangeListenerHandle?
    private var cancellables = Set<AnyCancellable>()
    
    init() {
        setupAuthStateListener()
    }
    
    deinit {
        if let handle = authStateHandle {
            Auth.auth().removeStateDidChangeListener(handle)
        }
    }
    
    private func setupAuthStateListener() {
        authStateHandle = Auth.auth().addStateDidChangeListener { [weak self] _, user in
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
            }
        }
    }
    
    // MARK: - Authentication Methods
    
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
    
    func signOut() {
        do {
            try Auth.auth().signOut()
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
    
    var errorDescription: String? {
        switch self {
        case .notAuthenticated:
            return "User is not authenticated"
        }
    }
}
