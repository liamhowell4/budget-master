import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authManager: AuthenticationManager
    @Environment(\.appBackgroundTint) private var backgroundTint

    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var displayName = ""
    @State private var isSignUpMode = false
    @State private var showingResetPassword = false
    @FocusState private var focusedField: Field?

    enum Field {
        case email, password, confirmPassword, displayName
    }

    var body: some View {
        ZStack {
            // Use the theme tint when available (authenticated theme context);
            // fall back to the system grouped background when tint is clear
            // (pre-auth context where no theme is injected).
            Group {
                if backgroundTint == .clear {
                    Color(uiColor: .systemGroupedBackground)
                } else {
                    backgroundTint
                }
            }
            .ignoresSafeArea()

            ScrollView {
                VStack(spacing: 32) {
                    // Header
                    VStack(spacing: 12) {
                        Image(systemName: "dollarsign.circle.fill")
                            .font(.system(size: 64))
                            .foregroundStyle(AppTheme.accent)

                        Text("Budget Master")
                            .font(.system(size: 28, weight: .bold))

                        Text(isSignUpMode ? "Create your account" : "Welcome back")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding(.top, 40)

                    // Form wrapped in glass card
                    VStack(spacing: 16) {
                        if isSignUpMode {
                            TextField("Display Name", text: $displayName)
                                .textContentType(.name)
                                .focused($focusedField, equals: .displayName)
                                .padding()
                                .background(Color(uiColor: .systemBackground).opacity(0.6))
                                .cornerRadius(10)
                        }

                        TextField("Email", text: $email)
                            .textContentType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .keyboardType(.emailAddress)
                            .focused($focusedField, equals: .email)
                            .padding()
                            .background(Color(uiColor: .systemBackground).opacity(0.6))
                            .cornerRadius(10)

                        SecureField("Password", text: $password)
                            .textContentType(isSignUpMode ? .newPassword : .password)
                            .focused($focusedField, equals: .password)
                            .padding()
                            .background(Color(uiColor: .systemBackground).opacity(0.6))
                            .cornerRadius(10)

                        // Confirm password — only visible in sign-up mode
                        if isSignUpMode {
                            VStack(alignment: .leading, spacing: 6) {
                                SecureField("Confirm Password", text: $confirmPassword)
                                    .textContentType(.newPassword)
                                    .focused($focusedField, equals: .confirmPassword)
                                    .padding()
                                    .background(Color(uiColor: .systemBackground).opacity(0.6))
                                    .cornerRadius(10)

                                // Inline mismatch hint — only shown when both fields are non-empty
                                if !confirmPassword.isEmpty && password != confirmPassword {
                                    Text("Passwords do not match")
                                        .font(.caption)
                                        .foregroundStyle(.red)
                                        .padding(.leading, 4)
                                        .transition(.opacity.combined(with: .move(edge: .top)))
                                }
                            }
                        }

                        if let error = authManager.errorMessage {
                            Text(error)
                                .font(.caption)
                                .foregroundStyle(.red)
                                .multilineTextAlignment(.center)
                        }

                        // Primary action button
                        Button {
                            Task {
                                if isSignUpMode {
                                    await authManager.signUp(
                                        email: email,
                                        password: password,
                                        displayName: displayName
                                    )
                                } else {
                                    await authManager.signIn(email: email, password: password)
                                }
                            }
                        } label: {
                            if authManager.isLoading {
                                ProgressView()
                                    .progressViewStyle(.circular)
                                    .tint(.white)
                            } else {
                                Text(isSignUpMode ? "Sign Up" : "Sign In")
                                    .fontWeight(.semibold)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 50)
                        .background(isFormValid ? AppTheme.accent : Color(uiColor: .systemGray3))
                        .foregroundStyle(.white)
                        .cornerRadius(10)
                        .disabled(!isFormValid || authManager.isLoading)

                        if !isSignUpMode {
                            Button("Forgot Password?") {
                                showingResetPassword = true
                            }
                            .font(.subheadline)
                            .foregroundStyle(AppTheme.accent)
                        }
                    }
                    .padding(24)
                    .glassCard()
                    .padding(.horizontal, 24)

                    // Social sign-in section — shown for both sign-in and sign-up modes
                    SocialSignInSection()
                        .padding(.horizontal, 24)

                    // Prominent mode-toggle section — full-width outlined button so new users
                    // immediately see the sign-up path without hunting for small secondary text.
                    VStack(spacing: 12) {
                        Text(isSignUpMode ? "Already have an account?" : "New to Budget Master?")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)

                        Button {
                            withAnimation(.spring(duration: 0.3)) {
                                isSignUpMode.toggle()
                                password = ""
                                confirmPassword = ""
                                displayName = ""
                            }
                        } label: {
                            Text(isSignUpMode ? "Sign In Instead" : "Create an Account")
                                .font(.system(size: 16, weight: .semibold))
                                .frame(maxWidth: .infinity)
                                .frame(height: 50)
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(AppTheme.accent)
                        .background(
                            RoundedRectangle(cornerRadius: 10)
                                .strokeBorder(AppTheme.accent, lineWidth: 1.5)
                        )
                        .padding(.horizontal, 24)
                        .accessibilityLabel(isSignUpMode ? "Sign in instead" : "Create an account")
                        .accessibilityHint(isSignUpMode ? "Switch to sign-in form" : "Switch to account creation form")
                    }

                    Spacer(minLength: 32)
                }
                .dismissKeyboardOnTap()
            }
            .scrollDismissesKeyboard(.interactively)
        }
        .alert("Reset Password", isPresented: $showingResetPassword) {
            TextField("Email", text: $email)
            Button("Cancel", role: .cancel) {}
            Button("Send Reset Link") {
                Task { await authManager.resetPassword(email: email) }
            }
        } message: {
            Text("Enter your email address to receive a password reset link.")
        }
    }

    private var isFormValid: Bool {
        if isSignUpMode {
            return !email.isEmpty
                && !password.isEmpty
                && !displayName.isEmpty
                && password.count >= 6
                && password == confirmPassword
        } else {
            return !email.isEmpty && !password.isEmpty
        }
    }
}

// MARK: - Social Sign-In Section

/// Renders the "or continue with" divider plus Apple, Google, and GitHub buttons.
/// Extracted as a subview to keep LoginView lean and to allow independent previewing.
private struct SocialSignInSection: View {
    @EnvironmentObject var authManager: AuthenticationManager

    var body: some View {
        VStack(spacing: 16) {
            // Divider row
            HStack(spacing: 12) {
                Rectangle()
                    .frame(height: 1)
                    .foregroundStyle(Color(uiColor: .separator))

                Text("or continue with")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .fixedSize()

                Rectangle()
                    .frame(height: 1)
                    .foregroundStyle(Color(uiColor: .separator))
            }

            // Sign-in buttons — stacked vertically to give each button full label legibility
            VStack(spacing: 12) {
                SocialButton(
                    label: "Continue with Apple",
                    systemImage: "applelogo",
                    foreground: .white,
                    background: Color(uiColor: .label),
                    border: nil
                ) {
                    Task { await authManager.signInWithApple() }
                }
                .accessibilityLabel("Sign in with Apple")

                SocialButton(
                    label: "Continue with Google",
                    systemImage: nil,
                    customLabel: "G",
                    foreground: Color(uiColor: .label),
                    background: Color(uiColor: .systemBackground),
                    border: Color(uiColor: .separator)
                ) {
                    Task { await authManager.signInWithGoogle() }
                }
                .accessibilityLabel("Sign in with Google")

                SocialButton(
                    label: "Continue with GitHub",
                    systemImage: "chevron.left.forwardslash.chevron.right",
                    foreground: .white,
                    background: Color(red: 36/255, green: 41/255, blue: 47/255),
                    border: nil
                ) {
                    Task { await authManager.signInWithGitHub() }
                }
                .accessibilityLabel("Sign in with GitHub")
            }
        }
        // Disabled as a unit while any auth operation is in flight
        .disabled(authManager.isLoading)
        .opacity(authManager.isLoading ? 0.6 : 1)
        .animation(.easeInOut(duration: 0.2), value: authManager.isLoading)
    }
}

// MARK: - Social Button

/// A single social provider button, parametrized to support both SF Symbol icons
/// and the Google "G" text badge without duplicating layout code.
private struct SocialButton: View {
    let label: String
    /// If non-nil, rendered as a SwiftUI Image(systemName:).
    let systemImage: String?
    /// Rendered as bold text instead of a symbol (used for the Google "G").
    var customLabel: String? = nil
    let foreground: Color
    let background: Color
    /// When non-nil, a 1pt stroke is drawn around the button. Use for light-background buttons.
    let border: Color?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                // Leading icon
                Group {
                    if let systemImage {
                        Image(systemName: systemImage)
                            .font(.system(size: 17, weight: .medium))
                    } else if let customLabel {
                        Text(customLabel)
                            .font(.system(size: 17, weight: .bold))
                    }
                }
                .frame(width: 20)

                Text(label)
                    .font(.system(size: 16, weight: .semibold))
            }
            .foregroundStyle(foreground)
            .frame(maxWidth: .infinity)
            .frame(height: 50)
            .background(background)
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay {
                if let border {
                    RoundedRectangle(cornerRadius: 10)
                        .strokeBorder(border, lineWidth: 1)
                }
            }
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Previews

#Preview("Sign In") {
    LoginView()
        .environmentObject(AuthenticationManager())
}

#Preview("Sign Up") {
    LoginView()
        .environmentObject(AuthenticationManager())
}
