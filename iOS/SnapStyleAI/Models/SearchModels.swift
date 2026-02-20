import Foundation

struct GeminiAnalysis: Codable, Sendable {
    let itemType: String
    let style: String
    let detailedDescription: String
    let colors: [String]
    let material: String?
    let keyFeatures: [String]
    let estimatedBrandTier: String
    let seasonOccasion: String
    let searchTerms: [String]
    let priceEstimate: String

    enum CodingKeys: String, CodingKey {
        case itemType = "item_type"
        case style
        case detailedDescription = "detailed_description"
        case colors, material
        case keyFeatures = "key_features"
        case estimatedBrandTier = "estimated_brand_tier"
        case seasonOccasion = "season_occasion"
        case searchTerms = "search_terms"
        case priceEstimate = "price_estimate"
    }
}

struct Product: Codable, Identifiable, Sendable {
    let id: String
    let title: String
    let description: String
    let price: Double
    let originalPrice: Double?
    let currency: String
    let imageUrl: String
    let merchant: String
    let affiliateLink: String
    let similarityPercentage: Int
    let brand: String?
    let category: String?

    enum CodingKeys: String, CodingKey {
        case id, title, description, price
        case originalPrice = "original_price"
        case currency
        case imageUrl = "image_url"
        case merchant
        case affiliateLink = "affiliate_link"
        case similarityPercentage = "similarity_percentage"
        case brand, category
    }
}

struct SearchResult: Codable, Identifiable, Sendable {
    let id: Int
    let imageUrl: String
    let analysis: GeminiAnalysis
    let products: [Product]
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case imageUrl = "image_url"
        case analysis, products
        case createdAt = "created_at"
    }
}

struct UsageStatus: Codable, Sendable {
    let searchesToday: Int
    let searchesRemaining: Int
    let limit: Int
    let isPremium: Bool

    enum CodingKeys: String, CodingKey {
        case searchesToday = "searches_today"
        case searchesRemaining = "searches_remaining"
        case limit
        case isPremium = "is_premium"
    }
}
