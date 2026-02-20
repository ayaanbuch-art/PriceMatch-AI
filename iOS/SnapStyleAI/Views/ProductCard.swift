import SwiftUI

struct ProductCard: View {
    let product: Product
    @State private var isFavorited = false

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Product Image with overlay elements
            ZStack(alignment: .topTrailing) {
                AsyncImage(url: URL(string: product.imageUrl)) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                    case .failure:
                        ZStack {
                            AppTheme.Colors.surfaceElevated
                            Image(systemName: "photo")
                                .font(.system(size: 24))
                                .foregroundColor(AppTheme.Colors.textTertiary)
                        }
                    case .empty:
                        ShimmerView()
                    @unknown default:
                        AppTheme.Colors.surfaceElevated
                    }
                }
                .frame(height: 180)
                .clipped()

                // Favorite button
                Button(action: {
                    withAnimation(.spring(response: 0.3)) {
                        isFavorited.toggle()
                    }
                }) {
                    Image(systemName: isFavorited ? "heart.fill" : "heart")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(isFavorited ? AppTheme.Colors.accent : .white)
                        .frame(width: 32, height: 32)
                        .background(.ultraThinMaterial)
                        .clipShape(Circle())
                }
                .padding(8)

                // Match badge - bottom left
                VStack {
                    Spacer()
                    HStack {
                        MatchBadge(percentage: product.similarityPercentage)
                            .padding(8)
                        Spacer()
                    }
                }
            }

            // Product info
            VStack(alignment: .leading, spacing: 6) {
                Text(product.title)
                    .font(AppTheme.Typography.caption)
                    .fontWeight(.medium)
                    .foregroundColor(AppTheme.Colors.textPrimary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)

                Text(product.merchant)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(AppTheme.Colors.textTertiary)
                    .textCase(.uppercase)
                    .tracking(0.5)

                HStack(spacing: 6) {
                    Text("$\(product.price, specifier: "%.2f")")
                        .font(AppTheme.Typography.priceSmall)
                        .foregroundColor(AppTheme.Colors.accent)

                    if let original = product.originalPrice, original > product.price {
                        Text("$\(original, specifier: "%.2f")")
                            .font(.system(size: 12))
                            .strikethrough()
                            .foregroundColor(AppTheme.Colors.textTertiary)

                        let discount = Int(((original - product.price) / original) * 100)
                        Text("-\(discount)%")
                            .font(AppTheme.Typography.badge)
                            .foregroundColor(AppTheme.Colors.success)
                    }
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
        }
        .background(AppTheme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.large))
        .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 4)
    }
}
