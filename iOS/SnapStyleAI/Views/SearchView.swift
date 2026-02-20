import SwiftUI
import UIKit

struct SearchView: View {
    @State private var viewModel = SearchViewModel()
    @State private var showImagePicker = false
    @State private var showCamera = false
    @State private var selectedImage: UIImage?
    @State private var showContent = false
    @State private var pulseAnimation = false

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.background
                    .ignoresSafeArea()

                if viewModel.isLoading {
                    analyzingView
                } else if let result = viewModel.searchResult {
                    SearchResultView(result: result, onNewSearch: {
                        withAnimation(.spring(response: 0.4)) {
                            viewModel.searchResult = nil
                            selectedImage = nil
                        }
                    })
                } else {
                    emptyStateView
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("Discover")
                        .font(AppTheme.Typography.title)
                        .foregroundColor(AppTheme.Colors.textPrimary)
                }
            }
            .sheet(isPresented: $showCamera) {
                ImagePicker(image: $selectedImage, sourceType: .camera)
            }
            .sheet(isPresented: $showImagePicker) {
                ImagePicker(image: $selectedImage, sourceType: .photoLibrary)
            }
            .onChange(of: selectedImage) { oldValue, newValue in
                if let image = newValue {
                    Task {
                        await viewModel.searchByImage(image)
                    }
                }
            }
            .task {
                await viewModel.loadUsageStatus()
            }
            .onAppear {
                withAnimation(.easeOut(duration: 0.6)) {
                    showContent = true
                }
                withAnimation(.easeInOut(duration: 2).repeatForever(autoreverses: true)) {
                    pulseAnimation = true
                }
            }
        }
    }

    // MARK: - Empty State
    private var emptyStateView: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: 0) {
                Spacer().frame(height: 40)

                // Hero illustration
                ZStack {
                    Circle()
                        .stroke(AppTheme.Colors.accent.opacity(0.08), lineWidth: 1)
                        .frame(width: 220, height: 220)
                        .scaleEffect(pulseAnimation ? 1.1 : 1.0)

                    Circle()
                        .stroke(AppTheme.Colors.accent.opacity(0.12), lineWidth: 1)
                        .frame(width: 170, height: 170)
                        .scaleEffect(pulseAnimation ? 1.05 : 0.95)

                    ZStack {
                        Circle()
                            .fill(
                                LinearGradient(
                                    colors: [AppTheme.Colors.primaryDark, AppTheme.Colors.primaryMid],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 120, height: 120)
                            .shadow(color: AppTheme.Colors.primaryDark.opacity(0.3), radius: 20, x: 0, y: 10)

                        Image(systemName: "camera.viewfinder")
                            .font(.system(size: 48, weight: .light))
                            .foregroundColor(.white)
                    }
                }
                .padding(.bottom, 32)
                .opacity(showContent ? 1 : 0)
                .offset(y: showContent ? 0 : 20)

                VStack(spacing: 12) {
                    Text("Snap. Discover. Save.")
                        .font(AppTheme.Typography.displayMedium)
                        .foregroundColor(AppTheme.Colors.textPrimary)

                    Text("Take a photo of any clothing item and our AI\nwill find you the best deals instantly")
                        .font(AppTheme.Typography.body)
                        .foregroundColor(AppTheme.Colors.textSecondary)
                        .multilineTextAlignment(.center)
                        .lineSpacing(4)
                }
                .padding(.bottom, 36)
                .opacity(showContent ? 1 : 0)
                .offset(y: showContent ? 0 : 15)

                // Action buttons
                VStack(spacing: 12) {
                    Button(action: { showCamera = true }) {
                        HStack(spacing: 10) {
                            Image(systemName: "camera.fill")
                                .font(.system(size: 18, weight: .medium))
                            Text("Take Photo")
                                .font(AppTheme.Typography.bodyMedium)
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(AppTheme.Gradients.accentGradient)
                        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
                        .shadow(color: AppTheme.Colors.accent.opacity(0.3), radius: 12, x: 0, y: 6)
                    }

                    Button(action: { showImagePicker = true }) {
                        HStack(spacing: 10) {
                            Image(systemName: "photo.on.rectangle.angled")
                                .font(.system(size: 18, weight: .medium))
                            Text("Choose from Library")
                                .font(AppTheme.Typography.bodyMedium)
                        }
                        .foregroundColor(AppTheme.Colors.accent)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(AppTheme.Colors.accentSoft)
                        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
                    }
                }
                .padding(.horizontal, 24)
                .opacity(showContent ? 1 : 0)
                .offset(y: showContent ? 0 : 10)

                if let usage = viewModel.usageStatus, !usage.isPremium {
                    HStack(spacing: 8) {
                        Image(systemName: "sparkle")
                            .font(.system(size: 12))
                            .foregroundColor(AppTheme.Colors.gold)
                        Text("\(usage.searchesRemaining) free searches remaining today")
                            .font(AppTheme.Typography.caption)
                            .foregroundColor(AppTheme.Colors.textSecondary)
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(AppTheme.Colors.goldSoft)
                    .clipShape(Capsule())
                    .padding(.top, 24)
                }

                // Feature highlights
                VStack(spacing: 16) {
                    featureRow(icon: "sparkles", title: "AI-Powered", subtitle: "Advanced vision analysis")
                    featureRow(icon: "tag.fill", title: "Best Prices", subtitle: "Compare across 100+ stores")
                    featureRow(icon: "bolt.fill", title: "Instant Results", subtitle: "Get matches in seconds")
                }
                .padding(.horizontal, 24)
                .padding(.top, 40)
                .padding(.bottom, 120)
            }
        }
    }

    // MARK: - Analyzing View
    private var analyzingView: some View {
        VStack(spacing: 24) {
            Spacer()

            ZStack {
                Circle()
                    .stroke(AppTheme.Colors.accent.opacity(0.15), lineWidth: 3)
                    .frame(width: 100, height: 100)

                Circle()
                    .trim(from: 0, to: 0.7)
                    .stroke(
                        AppTheme.Gradients.accentGradient,
                        style: StrokeStyle(lineWidth: 3, lineCap: .round)
                    )
                    .frame(width: 100, height: 100)
                    .rotationEffect(.degrees(pulseAnimation ? 360 : 0))
                    .animation(.linear(duration: 1.5).repeatForever(autoreverses: false), value: pulseAnimation)

                Image(systemName: "sparkles")
                    .font(.system(size: 32, weight: .medium))
                    .foregroundColor(AppTheme.Colors.accent)
                    .scaleEffect(pulseAnimation ? 1.1 : 0.9)
            }

            VStack(spacing: 8) {
                Text("Analyzing your style...")
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(AppTheme.Colors.textPrimary)

                Text("Our AI is identifying the item and\nfinding the best matches for you")
                    .font(AppTheme.Typography.body)
                    .foregroundColor(AppTheme.Colors.textSecondary)
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
            }

            Spacer()
        }
    }

    // MARK: - Helpers
    private func featureRow(icon: String, title: String, subtitle: String) -> some View {
        HStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(AppTheme.Colors.accent)
                .frame(width: 40, height: 40)
                .background(AppTheme.Colors.accentSoft)
                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.small))

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(AppTheme.Typography.bodyMedium)
                    .foregroundColor(AppTheme.Colors.textPrimary)
                Text(subtitle)
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textSecondary)
            }

            Spacer()
        }
        .padding(16)
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
        .shadow(color: Color.black.opacity(0.03), radius: 8, x: 0, y: 2)
    }
}

// MARK: - Search Result View

struct SearchResultView: View {
    let result: SearchResult
    var onNewSearch: (() -> Void)?

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 0) {
                imageAnalysisSection

                analysisCard
                    .padding(.horizontal, 16)
                    .padding(.top, 20)

                productsSection
                    .padding(.top, 24)

                Spacer().frame(height: 120)
            }
        }
        .overlay(alignment: .top) {
            if onNewSearch != nil {
                HStack {
                    Spacer()
                    Button(action: { onNewSearch?() }) {
                        HStack(spacing: 6) {
                            Image(systemName: "camera.fill")
                                .font(.system(size: 13, weight: .semibold))
                            Text("New Search")
                                .font(AppTheme.Typography.caption)
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(AppTheme.Colors.primaryDark.opacity(0.85))
                        .clipShape(Capsule())
                        .shadow(color: Color.black.opacity(0.15), radius: 8, x: 0, y: 4)
                    }
                    .padding(.trailing, 16)
                    .padding(.top, 8)
                }
            }
        }
    }

    // MARK: - Image Analysis Hero
    private var imageAnalysisSection: some View {
        ZStack(alignment: .bottomLeading) {
            AsyncImage(url: URL(string: result.imageUrl)) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                case .failure:
                    ZStack {
                        AppTheme.Colors.surfaceElevated
                        Image(systemName: "photo")
                            .font(.system(size: 40))
                            .foregroundColor(AppTheme.Colors.textTertiary)
                    }
                case .empty:
                    ShimmerView()
                @unknown default:
                    AppTheme.Colors.surfaceElevated
                }
            }
            .frame(height: 280)
            .clipped()

            LinearGradient(
                colors: [.clear, Color.black.opacity(0.6)],
                startPoint: .center,
                endPoint: .bottom
            )

            VStack(alignment: .leading, spacing: 4) {
                Text(result.analysis.itemType.uppercased())
                    .font(AppTheme.Typography.badge)
                    .tracking(1.5)
                    .foregroundColor(.white.opacity(0.7))

                Text(result.analysis.style)
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(.white)
            }
            .padding(20)
        }
    }

    // MARK: - Analysis Card
    private var analysisCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 8) {
                Image(systemName: "sparkles")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(AppTheme.Colors.accent)
                Text("AI Analysis")
                    .font(AppTheme.Typography.title)
                    .foregroundColor(AppTheme.Colors.textPrimary)
            }

            Text(result.analysis.detailedDescription)
                .font(AppTheme.Typography.body)
                .foregroundColor(AppTheme.Colors.textSecondary)
                .lineSpacing(4)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(result.analysis.colors, id: \.self) { color in
                        Text(color)
                            .font(AppTheme.Typography.badge)
                            .foregroundColor(AppTheme.Colors.primaryDark)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(AppTheme.Colors.surfaceElevated)
                            .clipShape(Capsule())
                    }

                    if let material = result.analysis.material {
                        Text(material)
                            .font(AppTheme.Typography.badge)
                            .foregroundColor(AppTheme.Colors.gold)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(AppTheme.Colors.goldSoft)
                            .clipShape(Capsule())
                    }
                }
            }

            HStack {
                Image(systemName: "tag.fill")
                    .font(.system(size: 12))
                    .foregroundColor(AppTheme.Colors.success)
                Text("Estimated value: \(result.analysis.priceEstimate)")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textSecondary)
            }
        }
        .padding(20)
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.large))
        .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 4)
    }

    // MARK: - Products Section
    private var productsSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            SectionHeader(
                title: "Similar Items",
                subtitle: "\(result.products.count) matches found"
            )
            .padding(.horizontal, 16)

            LazyVGrid(
                columns: [
                    GridItem(.flexible(), spacing: 12),
                    GridItem(.flexible(), spacing: 12)
                ],
                spacing: 16
            ) {
                ForEach(result.products) { product in
                    ProductCard(product: product)
                }
            }
            .padding(.horizontal, 16)
        }
    }
}
