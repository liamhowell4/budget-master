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
        NavigationStack {
            VStack(spacing: 0) {
                // Header
                VStack(spacing: 16) {
                    Image(systemName: "dollarsign.circle.fill")
                        .font(.system(size: 80))
                        .foregroundStyle(.green.gradient)
                    
                    Text("Budget Master")
                        .font(.system(size: 34, weight: .bold))
                    
                    Text(isSignUpMode ? "Create your account" : "Welcome back")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 60)
                .padding(.bottom, 40)
                
                // Form
                VStack(spacing: 20) {
                    if isSignUpMode {
                        TextField("Display Name", text: $displayName)
                            .textContentType(.name)
                            .focused($focusedField, equals: .displayName)
                            .padding()
                            .background(Color(.systemGray6))
                            .cornerRadius(10)
                    }
                    
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.emailAddress)
                        .focused($focusedField, equals: .email)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(10)
                    
                    SecureField("Password", text: $password)
                        .textContentType(isSignUpMode ? .newPassword : .password)
                        .focused($focusedField, equals: .password)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(10)
                    
                    // Error message
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
                                await authManager.signUp(email: email, password: password, displayName: displayName)
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
                    .background(isFormValid ? Color.green : Color.gray)
                    .foregroundStyle(.white)
                    .cornerRadius(10)
                    .disabled(!isFormValid || authManager.isLoading)
                    
                    // Forgot password
                    if !isSignUpMode {
                        Button("Forgot Password?") {
                            showingResetPassword = true
                        }
                        .font(.subheadline)
                        .foregroundStyle(.green)
                    }
                }
                .padding(.horizontal, 32)
                
                Spacer()
                
                // Toggle mode
                HStack {
                    Text(isSignUpMode ? "Already have an account?" : "Don't have an account?")
                        .foregroundStyle(.secondary)
                    
                    Button(isSignUpMode ? "Sign In" : "Sign Up") {
                        withAnimation {
                            isSignUpMode.toggle()
                            // Clear fields when switching
                            password = ""
                            displayName = ""
                        }
                    }
                    .fontWeight(.semibold)
                    .foregroundStyle(.green)
                }
                .padding(.bottom, 40)
            }
            .navigationBarHidden(true)
        }
        .alert("Reset Password", isPresented: $showingResetPassword) {
            TextField("Email", text: $email)
            Button("Cancel", role: .cancel) {}
            Button("Send Reset Link") {
                Task {
                    await authManager.resetPassword(email: email)
                }
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
