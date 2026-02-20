import SwiftUI

struct ProfileView: View {
    @Environment(AuthViewModel.self) var authViewModel
    @State private var usageStatus: UsageStatus?
    @State private var showContent = false

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.background
                    .ignoresSafeArea()

                ScrollView(showsIndicators: false) {
                    VStack(spacing: 20) {
                        // Profile header card
                        profileHeaderCard
                            .opacity(showContent ? 1 : 0)
                            .offset(y: showContent ? 0 : 15)

                        // Subscription card
                        subscriptionCard
                            .opacity(showContent ? 1 : 0)
                            .offset(y: showContent ? 0 : 10)

                        // Quick actions
                        quickActionsSection
                            .opacity(showContent ? 1 : 0)

                        // Settings section
                        settingsSection
                            .opacity(showContent ? 1 : 0)

                        // Logout
                        logoutButton
                            .opacity(showContent ? 1 : 0)

                        Spacer().frame(height: 120)
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 16)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("Profile")
                        .font(AppTheme.Typography.title)
                        .foregroundColor(AppTheme.Colors.textPrimary)
                }
            }
            .task {
                await loadUsageStatus()
            }
            .onAppear {
                withAnimation(.easeOut(duration: 0.6)) {
                    showContent = true
                }
            }
        }
    }

    // MARK: - Profile Header
    private var profileHeaderCard: some View {
        VStack(spacing: 16) {
            if let user = authViewModel.user {
                // Avatar
                ZStack {
                    Circle()
                        .fill(AppTheme.Gradients.heroGradient)
                        .frame(width: 80, height: 80)

                    Text(initials(for: user))
                        .font(.system(size: 28, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                }
                .shadow(color: AppTheme.Colors.primaryDark.opacity(0.2), radius: 12, x: 0, y: 6)

                VStack(spacing: 4) {
                    Text(user.fullName ?? "Fashionista")
                        .font(AppTheme.Typography.headline)
                        .foregroundColor(AppTheme.Colors.textPrimary)

                    Text(user.email)
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.textSecondary)
                }

                // Member since
                HStack(spacing: 4) {
                    Image(systemName: "calendar")
                        .font(.system(size: 11))
                    Text("Member since \(user.createdAt, style: .date)")
                        .font(.system(size: 11, weight: .medium))
                }
                .foregroundColor(AppTheme.Colors.textTertiary)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 24)
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.xl))
        .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 4)
    }

    // MARK: - Subscription Card
    private var subscriptionCard: some View {
        VStack(spacing: 0) {
            if let user = authViewModel.user {
                if user.isPremium {
                    // Premium member card
                    HStack(spacing: 16) {
                        ZStack {
                            Circle()
                                .fill(AppTheme.Gradients.goldGradient)
                                .frame(width: 48, height: 48)
                            Image(systemName: "crown.fill")
                                .font(.system(size: 20))
                                .foregroundColor(.white)
                        }

                        VStack(alignment: .leading, spacing: 4) {
                            Text("Premium Member")
                                .font(AppTheme.Typography.bodyMedium)
                                .foregroundColor(AppTheme.Colors.textPrimary)
                            Text("Unlimited searches & exclusive features")
                                .font(AppTheme.Typography.caption)
                                .foregroundColor(AppTheme.Colors.textSecondary)
                        }

                        Spacer()
                    }
                    .padding(20)
                } else {
                    // Free tier card with upgrade CTA
                    VStack(spacing: 16) {
                        HStack(spacing: 16) {
                            ZStack {
                                Circle()
                                    .fill(AppTheme.Colors.accentSoft)
                                    .frame(width: 48, height: 48)
                                Image(systemName: "sparkle")
                                    .font(.system(size: 20))
                                    .foregroundColor(AppTheme.Colors.accent)
                            }

                            VStack(alignment: .leading, spacing: 4) {
                                Text("Free Plan")
                                    .font(AppTheme.Typography.bodyMedium)
                                    .foregroundColor(AppTheme.Colors.textPrimary)

                                if let usage = usageStatus {
                                    HStack(spacing: 4) {
                                        Text("\(usage.searchesRemaining)")
                                            .font(AppTheme.Typography.bodyMedium)
                                            .foregroundColor(AppTheme.Colors.accent)
                                        Text("of \(usage.limit) searches remaining")
                                            .font(AppTheme.Typography.caption)
                                            .foregroundColor(AppTheme.Colors.textSecondary)
                                    }
                                }
                            }

                            Spacer()
                        }

                        // Usage progress bar
                        if let usage = usageStatus {
                            GeometryReader { geo in
                                ZStack(alignment: .leading) {
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(AppTheme.Colors.surfaceElevated)
                                        .frame(height: 6)

                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(AppTheme.Gradients.accentGradient)
                                        .frame(
                                            width: geo.size.width * CGFloat(usage.searchesRemaining) / CGFloat(max(usage.limit, 1)),
                                            height: 6
                                        )
                                }
                            }
                            .frame(height: 6)
                        }

                        // Upgrade button
                        Button(action: {}) {
                            HStack(spacing: 8) {
                                Image(systemName: "crown.fill")
                                    .font(.system(size: 14))
                                Text("Upgrade to Premium")
                                    .font(AppTheme.Typography.bodyMedium)
                            }
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 48)
                            .background(AppTheme.Gradients.goldGradient)
                            .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
                        }
                    }
                    .padding(20)
                }
            }
        }
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.xl))
        .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 4)
    }

    // MARK: - Quick Actions
    private var quickActionsSection: some View {
        HStack(spacing: 12) {
            quickActionCard(icon: "heart.fill", label: "Favorites", color: AppTheme.Colors.accent)
            quickActionCard(icon: "clock.fill", label: "History", color: AppTheme.Colors.primaryLight)
            quickActionCard(icon: "chart.bar.fill", label: "Stats", color: AppTheme.Colors.success)
        }
    }

    private func quickActionCard(icon: String, label: String, color: Color) -> some View {
        VStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 22, weight: .medium))
                .foregroundColor(color)

            Text(label)
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textSecondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 20)
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.large))
        .shadow(color: Color.black.opacity(0.04), radius: 8, x: 0, y: 2)
    }

    // MARK: - Settings
    private var settingsSection: some View {
        VStack(spacing: 0) {
            settingsRow(icon: "bell.fill", title: "Notifications", color: AppTheme.Colors.accent, showDivider: true)
            settingsRow(icon: "lock.fill", title: "Privacy", color: AppTheme.Colors.primaryLight, showDivider: true)
            settingsRow(icon: "questionmark.circle.fill", title: "Help & Support", color: AppTheme.Colors.success, showDivider: true)
            settingsRow(icon: "info.circle.fill", title: "About", color: AppTheme.Colors.textSecondary, showDivider: false)
        }
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.xl))
        .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 4)
    }

    private func settingsRow(icon: String, title: String, color: Color, showDivider: Bool) -> some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(color)
                    .frame(width: 32, height: 32)
                    .background(color.opacity(0.12))
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                Text(title)
                    .font(AppTheme.Typography.body)
                    .foregroundColor(AppTheme.Colors.textPrimary)

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(AppTheme.Colors.textTertiary)
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 14)

            if showDivider {
                Divider()
                    .padding(.leading, 66)
            }
        }
    }

    // MARK: - Logout
    private var logoutButton: some View {
        Button(action: {
            authViewModel.logout()
        }) {
            HStack(spacing: 8) {
                Image(systemName: "rectangle.portrait.and.arrow.right")
                    .font(.system(size: 15, weight: .medium))
                Text("Log Out")
                    .font(AppTheme.Typography.bodyMedium)
            }
            .foregroundColor(AppTheme.Colors.error)
            .frame(maxWidth: .infinity)
            .frame(height: 52)
            .background(AppTheme.Colors.error.opacity(0.08))
            .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
        }
    }

    // MARK: - Helpers
    private func initials(for user: User) -> String {
        if let name = user.fullName, !name.isEmpty {
            let parts = name.split(separator: " ")
            let first = parts.first?.prefix(1) ?? ""
            let last = parts.count > 1 ? parts.last?.prefix(1) ?? "" : ""
            return "\(first)\(last)".uppercased()
        }
        return String(user.email.prefix(1)).uppercased()
    }

    func loadUsageStatus() async {
        do {
            usageStatus = try await APIService.shared.getUsageStatus()
        } catch {
            print("Error loading usage: \(error)")
        }
    }
}
