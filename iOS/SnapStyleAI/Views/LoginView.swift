import SwiftUI

struct LoginView: View {
    @Environment(AuthViewModel.self) var authViewModel
    @State private var email = ""
    @State private var password = ""
    @State private var fullName = ""
    @State private var isSignUp = false
    @State private var animateBackground = false
    @State private var showContent = false

    var body: some View {
        ZStack {
            backgroundView

            ScrollView(showsIndicators: false) {
                VStack(spacing: 0) {
                    Spacer().frame(height: 80)

                    brandingSection
                        .opacity(showContent ? 1 : 0)
                        .offset(y: showContent ? 0 : 20)

                    Spacer().frame(height: 48)

                    formSection
                        .opacity(showContent ? 1 : 0)
                        .offset(y: showContent ? 0 : 30)

                    Spacer().frame(height: 24)

                    footerSection
                        .opacity(showContent ? 1 : 0)

                    Spacer().frame(height: 40)
                }
                .padding(.horizontal, 28)
            }
        }
        .ignoresSafeArea()
        .onAppear {
            withAnimation(.easeOut(duration: 0.8)) {
                showContent = true
            }
            withAnimation(.easeInOut(duration: 4).repeatForever(autoreverses: true)) {
                animateBackground = true
            }
        }
    }

    // MARK: - Background
    private var backgroundView: some View {
        ZStack {
            AppTheme.Colors.primaryDark
                .ignoresSafeArea()

            Circle()
                .fill(AppTheme.Colors.accent.opacity(0.15))
                .frame(width: 300, height: 300)
                .blur(radius: 80)
                .offset(
                    x: animateBackground ? 50 : -50,
                    y: animateBackground ? -100 : -200
                )

            Circle()
                .fill(AppTheme.Colors.gold.opacity(0.1))
                .frame(width: 250, height: 250)
                .blur(radius: 70)
                .offset(
                    x: animateBackground ? -60 : 80,
                    y: animateBackground ? 200 : 100
                )

            Circle()
                .fill(AppTheme.Colors.primaryLight.opacity(0.2))
                .frame(width: 200, height: 200)
                .blur(radius: 60)
                .offset(
                    x: animateBackground ? 100 : -30,
                    y: animateBackground ? 50 : 150
                )
        }
    }

    // MARK: - Branding
    private var brandingSection: some View {
        VStack(spacing: 16) {
            ZStack {
                Circle()
                    .fill(AppTheme.Gradients.accentGradient)
                    .frame(width: 80, height: 80)
                    .shadow(color: AppTheme.Colors.accent.opacity(0.4), radius: 20, x: 0, y: 8)

                Image(systemName: "camera.aperture")
                    .font(.system(size: 36, weight: .medium))
                    .foregroundColor(.white)
            }

            VStack(spacing: 8) {
                Text("PriceMatch AI")
                    .font(.system(size: 32, weight: .bold, design: .rounded))
                    .foregroundColor(.white)

                Text("Discover fashion. Find deals.\nPowered by AI.")
                    .font(AppTheme.Typography.body)
                    .foregroundColor(.white.opacity(0.6))
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
            }
        }
    }

    // MARK: - Form
    private var formSection: some View {
        VStack(spacing: 16) {
            VStack(spacing: 16) {
                HStack(spacing: 0) {
                    modeTab("Log In", isActive: !isSignUp) {
                        withAnimation(.spring(response: 0.3)) { isSignUp = false }
                    }
                    modeTab("Sign Up", isActive: isSignUp) {
                        withAnimation(.spring(response: 0.3)) { isSignUp = true }
                    }
                }
                .background(Color.white.opacity(0.05))
                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.small))

                if isSignUp {
                    loginTextField("Full Name", text: $fullName, icon: "person", isSecure: false)
                        .transition(.move(edge: .top).combined(with: .opacity))
                }

                loginTextField("Email", text: $email, icon: "envelope", isSecure: false)

                loginTextField("Password", text: $password, icon: "lock", isSecure: true)

                if let error = authViewModel.errorMessage {
                    HStack(spacing: 6) {
                        Image(systemName: "exclamationmark.circle.fill")
                            .font(.system(size: 13))
                        Text(error)
                            .font(AppTheme.Typography.caption)
                    }
                    .foregroundColor(AppTheme.Colors.error)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 4)
                }

                Button(action: {
                    Task {
                        if isSignUp {
                            await authViewModel.register(email: email, password: password, fullName: fullName)
                        } else {
                            await authViewModel.login(email: email, password: password)
                        }
                    }
                }) {
                    HStack(spacing: 8) {
                        if authViewModel.isLoading {
                            ProgressView()
                                .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                .scaleEffect(0.85)
                        } else {
                            Text(isSignUp ? "Create Account" : "Log In")
                                .font(AppTheme.Typography.bodyMedium)
                            Image(systemName: "arrow.right")
                                .font(.system(size: 14, weight: .semibold))
                        }
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .frame(height: 54)
                    .background(AppTheme.Gradients.accentGradient)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
                    .shadow(color: AppTheme.Colors.accent.opacity(0.4), radius: 12, x: 0, y: 6)
                }
                .disabled(authViewModel.isLoading)
                .padding(.top, 4)
            }
            .padding(24)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                    .fill(Color.white.opacity(0.08))
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                            .stroke(Color.white.opacity(0.1), lineWidth: 1)
                    )
            )
        }
        .animation(.spring(response: 0.4), value: isSignUp)
    }

    // MARK: - Footer
    private var footerSection: some View {
        VStack(spacing: 12) {
            HStack(spacing: 16) {
                Rectangle()
                    .fill(Color.white.opacity(0.15))
                    .frame(height: 1)
                Text("or continue with")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(.white.opacity(0.4))
                Rectangle()
                    .fill(Color.white.opacity(0.15))
                    .frame(height: 1)
            }

            Button(action: {}) {
                HStack(spacing: 8) {
                    Image(systemName: "apple.logo")
                        .font(.system(size: 18))
                    Text("Sign in with Apple")
                        .font(AppTheme.Typography.bodyMedium)
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 54)
                .background(Color.white.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.medium)
                        .stroke(Color.white.opacity(0.2), lineWidth: 1)
                )
            }

            Text("By continuing, you agree to our Terms & Privacy Policy")
                .font(.system(size: 11))
                .foregroundColor(.white.opacity(0.3))
                .multilineTextAlignment(.center)
                .padding(.top, 8)
        }
    }

    // MARK: - Helpers
    private func modeTab(_ title: String, isActive: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(AppTheme.Typography.bodyMedium)
                .foregroundColor(isActive ? .white : .white.opacity(0.4))
                .frame(maxWidth: .infinity)
                .frame(height: 44)
                .background(isActive ? Color.white.opacity(0.1) : Color.clear)
                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.small))
        }
    }

    private func loginTextField(_ placeholder: String, text: Binding<String>, icon: String, isSecure: Bool) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 15))
                .foregroundColor(.white.opacity(0.4))
                .frame(width: 20)

            if isSecure {
                SecureField(placeholder, text: text)
                    .font(AppTheme.Typography.body)
                    .foregroundColor(.white)
            } else {
                TextField(placeholder, text: text)
                    .font(AppTheme.Typography.body)
                    .foregroundColor(.white)
                    .autocapitalization(.none)
            }
        }
        .padding(.horizontal, 16)
        .frame(height: 50)
        .background(Color.white.opacity(0.06))
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.small))
        .overlay(
            RoundedRectangle(cornerRadius: AppTheme.Radius.small)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        )
    }
}
