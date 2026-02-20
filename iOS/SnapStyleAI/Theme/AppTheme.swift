import SwiftUI

// MARK: - PriceMatch AI Design System
// A luxury fashion-forward design system with rich gradients,
// elegant typography, and premium feel

struct AppTheme {

    // MARK: - Brand Colors
    struct Colors {
        // Primary gradient - deep fashion-forward palette
        static let primaryDark = Color(hex: "1A1A2E")
        static let primaryMid = Color(hex: "16213E")
        static let primaryLight = Color(hex: "0F3460")

        // Accent - warm rose gold / coral
        static let accent = Color(hex: "E94560")
        static let accentLight = Color(hex: "FF6B6B")
        static let accentSoft = Color(hex: "E94560").opacity(0.15)

        // Secondary accent - luxe gold
        static let gold = Color(hex: "D4A574")
        static let goldLight = Color(hex: "E8C89E")
        static let goldSoft = Color(hex: "D4A574").opacity(0.15)

        // Neutrals
        static let background = Color(hex: "FAFAFA")
        static let cardBackground = Color.white
        static let surfaceElevated = Color(hex: "F5F5F7")
        static let textPrimary = Color(hex: "1A1A2E")
        static let textSecondary = Color(hex: "6B7280")
        static let textTertiary = Color(hex: "9CA3AF")
        static let divider = Color(hex: "E5E7EB")

        // Status colors
        static let success = Color(hex: "10B981")
        static let warning = Color(hex: "F59E0B")
        static let error = Color(hex: "EF4444")

        // Match badge gradient
        static let matchHigh = Color(hex: "10B981")
        static let matchMedium = Color(hex: "F59E0B")
        static let matchLow = Color(hex: "EF4444")
    }

    // MARK: - Gradients
    struct Gradients {
        static let primaryGradient = LinearGradient(
            colors: [Colors.primaryDark, Colors.primaryMid, Colors.primaryLight],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )

        static let accentGradient = LinearGradient(
            colors: [Colors.accent, Colors.accentLight],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )

        static let goldGradient = LinearGradient(
            colors: [Colors.gold, Colors.goldLight],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )

        static let heroGradient = LinearGradient(
            colors: [
                Colors.primaryDark,
                Colors.primaryMid.opacity(0.95),
                Colors.accent.opacity(0.3)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )

        static let cardShimmer = LinearGradient(
            colors: [
                Color.white.opacity(0.0),
                Color.white.opacity(0.3),
                Color.white.opacity(0.0)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )

        static let subtleGradient = LinearGradient(
            colors: [Colors.background, Colors.surfaceElevated],
            startPoint: .top,
            endPoint: .bottom
        )
    }

    // MARK: - Typography
    struct Typography {
        static let displayLarge = Font.system(size: 34, weight: .bold, design: .rounded)
        static let displayMedium = Font.system(size: 28, weight: .bold, design: .rounded)
        static let headline = Font.system(size: 22, weight: .semibold, design: .rounded)
        static let title = Font.system(size: 18, weight: .semibold, design: .rounded)
        static let body = Font.system(size: 16, weight: .regular)
        static let bodyMedium = Font.system(size: 16, weight: .medium)
        static let caption = Font.system(size: 13, weight: .medium)
        static let captionSmall = Font.system(size: 11, weight: .semibold)
        static let price = Font.system(size: 18, weight: .bold, design: .rounded)
        static let priceSmall = Font.system(size: 14, weight: .semibold, design: .rounded)
        static let badge = Font.system(size: 11, weight: .bold, design: .rounded)
    }

    // MARK: - Spacing
    struct Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 20
        static let xxl: CGFloat = 24
        static let xxxl: CGFloat = 32
        static let huge: CGFloat = 48
    }

    // MARK: - Corner Radius
    struct Radius {
        static let small: CGFloat = 8
        static let medium: CGFloat = 12
        static let large: CGFloat = 16
        static let xl: CGFloat = 20
        static let xxl: CGFloat = 24
        static let pill: CGFloat = 100
    }

    // MARK: - Shadows
    struct Shadows {
        static func card() -> some View {
            Color.black.opacity(0.06)
        }

        static let cardRadius: CGFloat = 12
        static let cardX: CGFloat = 0
        static let cardY: CGFloat = 4

        static let elevatedRadius: CGFloat = 20
        static let elevatedX: CGFloat = 0
        static let elevatedY: CGFloat = 8
    }
}

// MARK: - Color Extension for Hex

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Reusable View Components

struct GlassCard<Content: View>: View {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    var body: some View {
        content
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.large)
                    .fill(Color.white)
                    .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 4)
            )
    }
}

struct AccentButton: View {
    let title: String
    let icon: String?
    let isLoading: Bool
    let action: () -> Void

    init(_ title: String, icon: String? = nil, isLoading: Bool = false, action: @escaping () -> Void) {
        self.title = title
        self.icon = icon
        self.isLoading = isLoading
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: AppTheme.Spacing.sm) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                        .scaleEffect(0.85)
                } else {
                    if let icon = icon {
                        Image(systemName: icon)
                            .font(.system(size: 16, weight: .semibold))
                    }
                    Text(title)
                        .font(AppTheme.Typography.bodyMedium)
                }
            }
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .frame(height: 54)
            .background(AppTheme.Gradients.accentGradient)
            .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
            .shadow(color: AppTheme.Colors.accent.opacity(0.3), radius: 8, x: 0, y: 4)
        }
        .disabled(isLoading)
    }
}

struct SecondaryButton: View {
    let title: String
    let icon: String?
    let action: () -> Void

    init(_ title: String, icon: String? = nil, action: @escaping () -> Void) {
        self.title = title
        self.icon = icon
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: AppTheme.Spacing.sm) {
                if let icon = icon {
                    Image(systemName: icon)
                        .font(.system(size: 16, weight: .medium))
                }
                Text(title)
                    .font(AppTheme.Typography.bodyMedium)
            }
            .foregroundColor(AppTheme.Colors.accent)
            .frame(maxWidth: .infinity)
            .frame(height: 54)
            .background(AppTheme.Colors.accentSoft)
            .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
        }
    }
}

struct StyledTextField: View {
    let placeholder: String
    @Binding var text: String
    var isSecure: Bool = false
    var icon: String? = nil
    var keyboardType: UIKeyboardType = .default
    var autocapitalization: UITextAutocapitalizationType = .sentences

    var body: some View {
        HStack(spacing: AppTheme.Spacing.md) {
            if let icon = icon {
                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundColor(AppTheme.Colors.textTertiary)
                    .frame(width: 20)
            }

            if isSecure {
                SecureField(placeholder, text: $text)
                    .font(AppTheme.Typography.body)
            } else {
                TextField(placeholder, text: $text)
                    .font(AppTheme.Typography.body)
                    .keyboardType(keyboardType)
                    .autocapitalization(autocapitalization)
            }
        }
        .padding(.horizontal, AppTheme.Spacing.lg)
        .frame(height: 54)
        .background(AppTheme.Colors.surfaceElevated)
        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.medium))
    }
}

struct MatchBadge: View {
    let percentage: Int

    private var color: Color {
        if percentage >= 90 { return AppTheme.Colors.matchHigh }
        if percentage >= 80 { return AppTheme.Colors.matchMedium }
        return AppTheme.Colors.matchLow
    }

    var body: some View {
        Text("\(percentage)% match")
            .font(AppTheme.Typography.badge)
            .foregroundColor(.white)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(
                Capsule()
                    .fill(color)
            )
    }
}

struct SectionHeader: View {
    let title: String
    var subtitle: String? = nil
    var action: (() -> Void)? = nil
    var actionLabel: String = "See All"

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(AppTheme.Colors.textPrimary)
                if let subtitle = subtitle {
                    Text(subtitle)
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.textSecondary)
                }
            }
            Spacer()
            if let action = action {
                Button(action: action) {
                    Text(actionLabel)
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.accent)
                }
            }
        }
    }
}

struct ShimmerView: View {
    @State private var phase: CGFloat = 0

    var body: some View {
        LinearGradient(
            colors: [
                Color.gray.opacity(0.1),
                Color.gray.opacity(0.2),
                Color.gray.opacity(0.1)
            ],
            startPoint: .init(x: phase - 1, y: 0.5),
            endPoint: .init(x: phase, y: 0.5)
        )
        .onAppear {
            withAnimation(.linear(duration: 1.5).repeatForever(autoreverses: false)) {
                phase = 2
            }
        }
    }
}

// MARK: - View Modifiers

struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(AppTheme.Colors.cardBackground)
            .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.large))
            .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 4)
    }
}

extension View {
    func cardStyle() -> some View {
        modifier(CardStyle())
    }
}
