import SwiftUI

@main
struct SnapStyleAIApp: App {
    @State private var authViewModel = AuthViewModel()

    var body: some Scene {
        WindowGroup {
            if authViewModel.isAuthenticated {
                MainTabView()
                    .environment(authViewModel)
            } else {
                LoginView()
                    .environment(authViewModel)
            }
        }
    }
}

struct MainTabView: View {
    @Environment(AuthViewModel.self) var authViewModel
    @State private var selectedTab = 0

    var body: some View {
        ZStack(alignment: .bottom) {
            TabView(selection: $selectedTab) {
                SearchView()
                    .tag(0)

                RecommendationsView()
                    .tag(1)

                ProfileView()
                    .environment(authViewModel)
                    .tag(2)
            }

            customTabBar
        }
        .ignoresSafeArea(.keyboard)
    }

    private var customTabBar: some View {
        HStack(spacing: 0) {
            tabBarItem(icon: "camera.fill", label: "Discover", tag: 0)
            tabBarItem(icon: "sparkles", label: "For You", tag: 1)
            tabBarItem(icon: "person.fill", label: "Profile", tag: 2)
        }
        .padding(.horizontal, 20)
        .padding(.top, 12)
        .padding(.bottom, 28)
        .background(
            Rectangle()
                .fill(.ultraThinMaterial)
                .overlay(
                    Rectangle()
                        .fill(Color.white.opacity(0.5))
                )
                .shadow(color: Color.black.opacity(0.08), radius: 20, x: 0, y: -5)
                .ignoresSafeArea(edges: .bottom)
        )
    }

    private func tabBarItem(icon: String, label: String, tag: Int) -> some View {
        Button(action: {
            withAnimation(.spring(response: 0.3)) {
                selectedTab = tag
            }
        }) {
            VStack(spacing: 4) {
                ZStack {
                    if selectedTab == tag {
                        Circle()
                            .fill(AppTheme.Colors.accentSoft)
                            .frame(width: 40, height: 40)
                    }

                    Image(systemName: icon)
                        .font(.system(size: selectedTab == tag ? 18 : 20, weight: .medium))
                        .foregroundColor(selectedTab == tag ? AppTheme.Colors.accent : AppTheme.Colors.textTertiary)
                }
                .frame(height: 40)

                Text(label)
                    .font(.system(size: 10, weight: selectedTab == tag ? .semibold : .medium))
                    .foregroundColor(selectedTab == tag ? AppTheme.Colors.accent : AppTheme.Colors.textTertiary)
            }
            .frame(maxWidth: .infinity)
        }
    }
}
