import SwiftUI

struct RecommendationsView: View {
    @State private var recommendations: [Product] = []
    @State private var isLoading = false
    @State private var showContent = false

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.background
                    .ignoresSafeArea()

                if isLoading {
                    loadingView
                } else if recommendations.isEmpty {
                    emptyStateView
                } else {
                    contentView
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("For You")
                        .font(AppTheme.Typography.title)
                        .foregroundColor(AppTheme.Colors.textPrimary)
                }
            }
            .task {
                await loadRecommendations()
            }
            .onAppear {
                withAnimation(.easeOut(duration: 0.6)) {
                    showContent = true
                }
            }
        }
    }

    // MARK: - Content View
    private var contentView: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 24) {
                // Header card
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        Image(systemName: "sparkles")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(AppTheme.Colors.accent)
                        Text("Curated For You")
                            .font(AppTheme.Typography.title)
                            .foregroundColor(AppTheme.Colors.textPrimary)
                    }
                    Text("Based on your searches and style preferences")
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.textSecondary)
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)

                // Products grid
                LazyVGrid(
                    columns: [
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12)
                    ],
                    spacing: 16
                ) {
                    ForEach(recommendations) { product in
                        ProductCard(product: product)
                            .transition(.scale.combined(with: .opacity))
                    }
                }
                .padding(.horizontal, 16)

                Spacer().frame(height: 120)
            }
        }
    }

    // MARK: - Empty State
    private var emptyStateView: some View {
        VStack(spacing: 24) {
            Spacer()

            ZStack {
                Circle()
                    .fill(AppTheme.Colors.accentSoft)
                    .frame(width: 120, height: 120)

                Image(systemName: "sparkles")
                    .font(.system(size: 48, weight: .light))
                    .foregroundColor(AppTheme.Colors.accent)
            }
            .opacity(showContent ? 1 : 0)
            .scaleEffect(showContent ? 1 : 0.8)

            VStack(spacing: 12) {
                Text("Your Style Feed")
                    .font(AppTheme.Typography.displayMedium)
                    .foregroundColor(AppTheme.Colors.textPrimary)

                Text("Start discovering fashion items to get\npersonalized recommendations just for you")
                    .font(AppTheme.Typography.body)
                    .foregroundColor(AppTheme.Colors.textSecondary)
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
            }
            .opacity(showContent ? 1 : 0)
            .offset(y: showContent ? 0 : 15)

            Spacer()
        }
        .padding(.horizontal, 32)
    }

    // MARK: - Loading View
    private var loadingView: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: 24) {
                HStack(spacing: 8) {
                    ShimmerView()
                        .frame(width: 100, height: 16)
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)

                LazyVGrid(
                    columns: [
                        GridItem(.flexible(), spacing: 12),
                        GridItem(.flexible(), spacing: 12)
                    ],
                    spacing: 16
                ) {
                    ForEach(0..<6, id: \.self) { _ in
                        VStack(alignment: .leading, spacing: 8) {
                            ShimmerView()
                                .frame(height: 180)
                                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.large))
                            ShimmerView()
                                .frame(height: 14)
                                .clipShape(RoundedRectangle(cornerRadius: 4))
                            ShimmerView()
                                .frame(width: 80, height: 12)
                                .clipShape(RoundedRectangle(cornerRadius: 4))
                            ShimmerView()
                                .frame(width: 60, height: 16)
                                .clipShape(RoundedRectangle(cornerRadius: 4))
                        }
                        .padding(8)
                        .cardStyle()
                    }
                }
                .padding(.horizontal, 16)
            }
        }
    }

    func loadRecommendations() async {
        isLoading = true
        do {
            recommendations = try await APIService.shared.getRecommendations()
        } catch {
            print("Error loading recommendations: \(error)")
        }
        isLoading = false
    }
}
