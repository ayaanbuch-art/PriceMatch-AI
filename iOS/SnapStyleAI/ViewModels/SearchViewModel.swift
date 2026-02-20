import Foundation
import UIKit
import Observation

@MainActor
@Observable
class SearchViewModel {
    var searchResult: SearchResult?
    var searchHistory: [SearchResult] = []
    var isLoading = false
    var errorMessage: String?
    var usageStatus: UsageStatus?

    func searchByImage(_ image: UIImage) async {
        isLoading = true
        errorMessage = nil

        do {
            searchResult = try await APIService.shared.searchByImage(image)
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func loadSearchHistory() async {
        do {
            searchHistory = try await APIService.shared.getSearchHistory()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadUsageStatus() async {
        do {
            usageStatus = try await APIService.shared.getUsageStatus()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
