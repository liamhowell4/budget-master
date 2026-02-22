import SwiftUI
import FirebaseAuth

struct ProfileTab: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @Environment(\.appAccent) private var appAccent

    @State private var displayName: String = ""
    @State private var isEditingName = false
    @State private var isSavingName = false
    @State private var nameSaveSuccess = false

    // Password change
    @State private var showPasswordChange = false
    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var isChangingPassword = false
    @State private var passwordError: String?
    @State private var passwordSuccess = false

    @State private var errorMessage: String?

    private var email: String {
        authManager.currentUser?.email ?? "Not available"
    }

    private var provider: String {
        authManager.authProvider
    }

    private var providerLabel: String {
        switch provider {
        case "password": return "Email"
        case "google.com": return "Google"
        case "apple.com": return "Apple"
        case "github.com": return "GitHub"
        default: return "Unknown"
        }
    }

    private var providerIcon: String {
        switch provider {
        case "password": return "envelope.fill"
        case "google.com": return "globe"
        case "apple.com": return "apple.logo"
        case "github.com": return "chevron.left.forwardslash.chevron.right"
        default: return "person.fill"
        }
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Profile header
                profileHeader

                // Account info section
                accountInfoSection

                // Display name section
                displayNameSection

                // Password change (email auth only)
                if provider == "password" {
                    passwordSection
                }

                // Sign out
                signOutSection
            }
            .padding()
        }
        .onAppear {
            displayName = authManager.currentUser?.displayName ?? ""
        }
    }

    // MARK: - Profile Header

    private var profileHeader: some View {
        VStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(appAccent.opacity(0.15))
                    .frame(width: 80, height: 80)

                Text(initials)
                    .font(.title)
                    .fontWeight(.bold)
                    .foregroundStyle(appAccent)
            }

            if let name = authManager.currentUser?.displayName, !name.isEmpty {
                Text(name)
                    .font(.title3)
                    .fontWeight(.semibold)
            }

            Text(email)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
    }

    private var initials: String {
        let name = authManager.currentUser?.displayName ?? authManager.currentUser?.email ?? "?"
        let parts = name.split(separator: " ")
        if parts.count >= 2 {
            return String(parts[0].prefix(1) + parts[1].prefix(1)).uppercased()
        }
        return String(name.prefix(2)).uppercased()
    }

    // MARK: - Account Info

    private var accountInfoSection: some View {
        VStack(spacing: 0) {
            infoRow(label: "Email", value: email)
            Divider().padding(.leading, 16)
            HStack {
                Text("Auth Provider")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Spacer()
                HStack(spacing: 6) {
                    Image(systemName: providerIcon)
                        .font(.caption)
                    Text(providerLabel)
                        .font(.subheadline)
                        .fontWeight(.medium)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(appAccent.opacity(0.1))
                .clipShape(Capsule())
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
        .glassCard()
    }

    private func infoRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
                .lineLimit(1)
                .truncationMode(.middle)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }

    // MARK: - Display Name

    private var displayNameSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Display Name")
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundStyle(.secondary)
                .padding(.horizontal, 4)

            HStack(spacing: 12) {
                TextField("Enter your name", text: $displayName)
                    .font(.body)
                    .padding(12)
                    .background(Color(uiColor: .secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 10))

                Button {
                    Task { await saveName() }
                } label: {
                    if isSavingName {
                        ProgressView()
                            .progressViewStyle(.circular)
                            .tint(.white)
                            .frame(width: 44, height: 44)
                    } else {
                        Image(systemName: nameSaveSuccess ? "checkmark" : "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundStyle(nameSaveSuccess ? .green : appAccent)
                            .frame(width: 44, height: 44)
                    }
                }
                .disabled(isSavingName || displayName.trimmingCharacters(in: .whitespaces).isEmpty)
            }

            if let errorMessage {
                Text(errorMessage)
                    .font(.caption)
                    .foregroundStyle(.red)
            }
        }
        .padding()
        .glassCard()
    }

    private func saveName() async {
        let trimmed = displayName.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }

        isSavingName = true
        errorMessage = nil

        do {
            try await authManager.updateDisplayName(trimmed)
            nameSaveSuccess = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                nameSaveSuccess = false
            }
        } catch {
            errorMessage = error.localizedDescription
        }

        isSavingName = false
    }

    // MARK: - Password Change

    private var passwordSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Button {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                    showPasswordChange.toggle()
                    if !showPasswordChange {
                        resetPasswordFields()
                    }
                }
            } label: {
                HStack {
                    Image(systemName: "lock.fill")
                        .foregroundStyle(appAccent)
                    Text("Change Password")
                        .font(.subheadline)
                        .fontWeight(.medium)
                    Spacer()
                    Image(systemName: showPasswordChange ? "chevron.up" : "chevron.down")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .buttonStyle(.plain)

            if showPasswordChange {
                VStack(spacing: 12) {
                    SecureField("Current Password", text: $currentPassword)
                        .textContentType(.password)
                        .padding(12)
                        .background(Color(uiColor: .secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10))

                    SecureField("New Password", text: $newPassword)
                        .textContentType(.newPassword)
                        .padding(12)
                        .background(Color(uiColor: .secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10))

                    SecureField("Confirm New Password", text: $confirmPassword)
                        .textContentType(.newPassword)
                        .padding(12)
                        .background(Color(uiColor: .secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 10))

                    if let passwordError {
                        Text(passwordError)
                            .font(.caption)
                            .foregroundStyle(.red)
                    }

                    if passwordSuccess {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.circle.fill")
                            Text("Password updated successfully")
                        }
                        .font(.caption)
                        .foregroundStyle(.green)
                    }

                    Button {
                        Task { await changePassword() }
                    } label: {
                        if isChangingPassword {
                            ProgressView()
                                .progressViewStyle(.circular)
                                .tint(.white)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                                .background(appAccent)
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                        } else {
                            Text("Update Password")
                                .font(.subheadline)
                                .fontWeight(.semibold)
                                .foregroundStyle(.white)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                                .background(canChangePassword ? appAccent : Color(uiColor: .systemGray3))
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                        }
                    }
                    .disabled(!canChangePassword || isChangingPassword)
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
        .padding()
        .glassCard()
    }

    private var canChangePassword: Bool {
        !currentPassword.isEmpty
        && newPassword.count >= 6
        && newPassword == confirmPassword
    }

    private func changePassword() async {
        isChangingPassword = true
        passwordError = nil
        passwordSuccess = false

        do {
            try await authManager.updatePassword(
                currentPassword: currentPassword,
                newPassword: newPassword
            )
            passwordSuccess = true
            resetPasswordFields()
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
                passwordSuccess = false
                showPasswordChange = false
            }
        } catch {
            passwordError = error.localizedDescription
        }

        isChangingPassword = false
    }

    private func resetPasswordFields() {
        currentPassword = ""
        newPassword = ""
        confirmPassword = ""
        passwordError = nil
    }

    // MARK: - Sign Out

    private var signOutSection: some View {
        Button(role: .destructive) {
            authManager.signOut()
        } label: {
            HStack {
                Image(systemName: "rectangle.portrait.and.arrow.right")
                Text("Sign Out")
                    .fontWeight(.medium)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
        }
        .glassCard()
    }
}
