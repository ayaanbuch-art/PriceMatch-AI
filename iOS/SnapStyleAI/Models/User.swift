import Foundation

struct User: Codable, Identifiable, Sendable {
    let id: Int
    let email: String
    let fullName: String?
    let profileImageUrl: String?
    let authProvider: String
    let subscriptionStatus: String
    let subscriptionExpiresAt: Date?
    let isPremium: Bool
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, email
        case fullName = "full_name"
        case profileImageUrl = "profile_image_url"
        case authProvider = "auth_provider"
        case subscriptionStatus = "subscription_status"
        case subscriptionExpiresAt = "subscription_expires_at"
        case isPremium = "is_premium"
        case createdAt = "created_at"
    }
}

struct AuthResponse: Codable, Sendable {
    let accessToken: String
    let tokenType: String
    let user: User

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case user
    }
}

struct LoginRequest: Codable, Sendable {
    let email: String
    let password: String
}

struct RegisterRequest: Codable, Sendable {
    let email: String
    let password: String
    let fullName: String?

    enum CodingKeys: String, CodingKey {
        case email, password
        case fullName = "full_name"
    }
}
