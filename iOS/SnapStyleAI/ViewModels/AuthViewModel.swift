import Foundation
import SwiftUI
import Observation

@MainActor
@Observable
class AuthViewModel {
    var user: User?
    var isAuthenticated = false
    var isLoading = false
    var errorMessage: String?

    init() {
        checkAuthStatus()
    }

    func checkAuthStatus() {
        if KeychainHelper.shared.getToken() != nil {
            Task {
                do {
                    user = try await APIService.shared.getCurrentUser()
                    isAuthenticated = true
                } catch {
                    APIService.shared.clearToken()
                    isAuthenticated = false
                }
            }
        }
    }

    func login(email: String, password: String) async {
        isLoading = true
        errorMessage = nil

        do {
            let response = try await APIService.shared.login(email: email, password: password)
            APIService.shared.setToken(response.accessToken)
            user = response.user
            isAuthenticated = true
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func register(email: String, password: String, fullName: String?) async {
        isLoading = true
        errorMessage = nil

        do {
            let response = try await APIService.shared.register(email: email, password: password, fullName: fullName)
            APIService.shared.setToken(response.accessToken)
            user = response.user
            isAuthenticated = true
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func logout() {
        APIService.shared.clearToken()
        user = nil
        isAuthenticated = false
    }
}
