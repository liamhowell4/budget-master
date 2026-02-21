import SwiftUI

struct LoginView: View {
    @EnvironmentObject var authManager: AuthenticationManager

    @State private var email = ""
    @State private var password = ""
    @State private var displayName = ""
    @State private var isSignUpMode = false
    @State private var showingResetPassword = false
    @FocusState private var focusedField: Field?

    enum Field {
        case email, password, displayName
    }

    var body: some View {
        ZStack {
            Color(uiColor: .systemGroupedBackground)
                .ignoresSafeArea()

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

                // Toggle sign in / sign up
                HStack {
                    Text(isSignUpMode ? "Already have an account?" : "Don't have an account?")
                        .foregroundStyle(.secondary)

                    Button(isSignUpMode ? "Sign In" : "Sign Up") {
                        withAnimation {
                            isSignUpMode.toggle()
                            password = ""
                            displayName = ""
                        }
                    }
                    .fontWeight(.semibold)
                    .foregroundStyle(AppTheme.accent)
                }

                Spacer()
            }
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
            return !email.isEmpty && !password.isEmpty && !displayName.isEmpty && password.count >= 6
        } else {
            return !email.isEmpty && !password.isEmpty
        }
    }
}

#Preview("Sign In") {
    LoginView()
        .environmentObject(AuthenticationManager())
}

#Preview("Sign Up") {
    LoginView()
        .environmentObject(AuthenticationManager())
}
