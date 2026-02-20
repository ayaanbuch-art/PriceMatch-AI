import Foundation
import UIKit

@MainActor
class APIService {
    static let shared = APIService()

    private let baseURL = "http://localhost:8000"
    private var accessToken: String?

    private init() {
        self.accessToken = KeychainHelper.shared.getToken()
    }

    private let jsonDecoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        return decoder
    }()

    private let jsonEncoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()

    func setToken(_ token: String) {
        self.accessToken = token
        KeychainHelper.shared.saveToken(token)
    }

    func clearToken() {
        self.accessToken = nil
        KeychainHelper.shared.deleteToken()
    }

    // MARK: - Authentication

    func register(email: String, password: String, fullName: String?) async throws -> AuthResponse {
        let request = RegisterRequest(email: email, password: password, fullName: fullName)
        return try await post("/api/auth/register", body: request)
    }

    func login(email: String, password: String) async throws -> AuthResponse {
        let request = LoginRequest(email: email, password: password)
        return try await post("/api/auth/login", body: request)
    }

    func getCurrentUser() async throws -> User {
        return try await get("/api/auth/me")
    }

    // MARK: - Search

    func searchByImage(_ image: UIImage) async throws -> SearchResult {
        guard let imageData = image.jpegData(compressionQuality: 0.8) else {
            throw APIError.invalidImage
        }

        return try await uploadImage("/api/search/image", imageData: imageData, filename: "photo.jpg")
    }

    func getSearchHistory(skip: Int = 0, limit: Int = 20) async throws -> [SearchResult] {
        struct Response: Codable {
            let searches: [SearchResult]
            let total: Int
        }
        let response: Response = try await get("/api/search/history?skip=\(skip)&limit=\(limit)")
        return response.searches
    }

    // MARK: - Favorites

    func addFavorite(productId: String, productData: [String: Any]) async throws {
        struct FavoriteRequest: Codable {
            let productId: String
            let productData: [String: AnyCodable]

            enum CodingKeys: String, CodingKey {
                case productId = "product_id"
                case productData = "product_data"
            }
        }

        let productDataCodable = productData.mapValues { AnyCodable($0) }
        let request = FavoriteRequest(productId: productId, productData: productDataCodable)
        let _: EmptyResponse = try await post("/api/favorites", body: request)
    }

    func removeFavorite(productId: String) async throws {
        let _: EmptyResponse = try await delete("/api/favorites/\(productId)")
    }

    func getFavorites() async throws -> [Product] {
        struct Favorite: Codable {
            let productData: Product

            enum CodingKeys: String, CodingKey {
                case productData = "product_data"
            }
        }
        let favorites: [Favorite] = try await get("/api/favorites")
        return favorites.map { $0.productData }
    }

    // MARK: - Recommendations

    func getRecommendations(limit: Int = 20) async throws -> [Product] {
        return try await get("/api/recommendations?limit=\(limit)")
    }

    // MARK: - Subscription

    func getUsageStatus() async throws -> UsageStatus {
        return try await get("/api/subscription/usage")
    }

    // MARK: - Generic Request Methods

    private func get<T: Decodable>(_ path: String) async throws -> T {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        return try jsonDecoder.decode(T.self, from: data)
    }

    private func post<T: Encodable, R: Decodable>(_ path: String, body: T) async throws -> R {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        request.httpBody = try jsonEncoder.encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        return try jsonDecoder.decode(R.self, from: data)
    }

    private func delete<R: Decodable>(_ path: String) async throws -> R {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"

        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        return try jsonDecoder.decode(R.self, from: data)
    }

    private func uploadImage<R: Decodable>(_ path: String, imageData: Data, filename: String) async throws -> R {
        guard let url = URL(string: baseURL + path) else {
            throw APIError.invalidURL
        }

        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        if let token = accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            throw APIError.httpError(httpResponse.statusCode)
        }

        return try jsonDecoder.decode(R.self, from: data)
    }
}

// MARK: - Helper Types

enum APIError: LocalizedError {
    case invalidURL
    case invalidImage
    case invalidResponse
    case httpError(Int)
    case decodingError

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidImage:
            return "Invalid image"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .decodingError:
            return "Failed to decode response"
        }
    }
}

struct EmptyResponse: Codable, Sendable {}

struct AnyCodable: Codable, Sendable {
    private let stringValue: String?
    private let intValue: Int?
    private let doubleValue: Double?
    private let boolValue: Bool?

    init(_ value: Any) {
        if let s = value as? String {
            stringValue = s; intValue = nil; doubleValue = nil; boolValue = nil
        } else if let i = value as? Int {
            stringValue = nil; intValue = i; doubleValue = nil; boolValue = nil
        } else if let d = value as? Double {
            stringValue = nil; intValue = nil; doubleValue = d; boolValue = nil
        } else if let b = value as? Bool {
            stringValue = nil; intValue = nil; doubleValue = nil; boolValue = b
        } else {
            stringValue = "\(value)"; intValue = nil; doubleValue = nil; boolValue = nil
        }
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let s = try? container.decode(String.self) {
            stringValue = s; intValue = nil; doubleValue = nil; boolValue = nil
        } else if let i = try? container.decode(Int.self) {
            stringValue = nil; intValue = i; doubleValue = nil; boolValue = nil
        } else if let d = try? container.decode(Double.self) {
            stringValue = nil; intValue = nil; doubleValue = d; boolValue = nil
        } else if let b = try? container.decode(Bool.self) {
            stringValue = nil; intValue = nil; doubleValue = nil; boolValue = b
        } else {
            stringValue = ""; intValue = nil; doubleValue = nil; boolValue = nil
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let s = stringValue {
            try container.encode(s)
        } else if let i = intValue {
            try container.encode(i)
        } else if let d = doubleValue {
            try container.encode(d)
        } else if let b = boolValue {
            try container.encode(b)
        }
    }
}
