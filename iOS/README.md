# PriceMatch AI - iOS App

SwiftUI iOS application for PriceMatch AI fashion discovery.

## Requirements

- Xcode 15.0+
- iOS 16.0+
- Swift 5.9+

## Setup

1. Open the project in Xcode:
```bash
cd iOS
open SnapStyleAI.xcodeproj
```

2. Update the API base URL in `Services/APIService.swift`:
```swift
private let baseURL = "https://your-backend-url.com"  // Change from localhost
```

3. Configure your App ID and signing in Xcode:
   - Select the project in Xcode
   - Go to "Signing & Capabilities"
   - Select your development team
   - Update Bundle Identifier

4. Add required capabilities:
   - Camera usage
   - Photo Library usage

5. Update `Info.plist` with usage descriptions:
   - `NSCameraUsageDescription`: "Take photos of clothing to find similar items"
   - `NSPhotoLibraryUsageDescription`: "Choose photos from your library to search"

## Project Structure

```
SnapStyleAI/
├── Models/               # Data models
│   ├── User.swift
│   └── SearchModels.swift
├── Services/             # Networking and utilities
│   ├── APIService.swift
│   └── KeychainHelper.swift
├── ViewModels/           # MVVM view models
│   ├── AuthViewModel.swift
│   └── SearchViewModel.swift
├── Views/                # SwiftUI views
│   ├── LoginView.swift
│   ├── SearchView.swift
│   ├── ProductCard.swift
│   ├── RecommendationsView.swift
│   ├── ProfileView.swift
│   └── ImagePicker.swift
└── SnapStyleAIApp.swift  # App entry point
```

## Features

### MVP Features ✅
- [x] Email/password authentication
- [x] Apple Sign-In (TODO: Implement Apple SDK)
- [x] Camera integration for clothing search
- [x] Visual search with AI analysis
- [x] Depop-style product grid
- [x] Similarity percentage display
- [x] Personalized recommendations
- [x] Favorites
- [x] Search history
- [x] Usage limits (free tier)
- [x] Profile management

### Post-MVP Features
- [ ] Subscription/paywall with StoreKit 2
- [ ] Apple IAP integration
- [ ] Push notifications
- [ ] Share functionality
- [ ] Deep linking
- [ ] AI Chatbot
- [ ] Wardrobe analyzer

## Running the App

1. Make sure backend is running (see backend/README.md)
2. Select a simulator or device in Xcode
3. Press Cmd+R to build and run

## Building for Production

1. Update base URL to production backend
2. Configure Apple Sign-In:
   - Enable "Sign in with Apple" capability
   - Configure service ID in Apple Developer Portal
3. Set up StoreKit for subscriptions:
   - Create subscription products in App Store Connect
   - Configure pricing ($3.49/month, $39.99/year)
   - Set up subscription groups
4. Configure analytics (Firebase, Mixpanel)
5. Set up crash reporting (Crashlytics, Sentry)
6. Create App Store assets:
   - Screenshots (all device sizes)
   - App icon
   - App description
   - Keywords
7. Submit to App Store

## Testing

- Run on multiple device sizes (iPhone SE, iPhone 15 Pro Max)
- Test camera on physical device
- Test free tier limits (5 searches/day)
- Test network error handling
- Test offline mode

## Notes

- Camera only works on physical devices (not simulator)
- Update API base URL before deploying
- Add proper error handling for production
- Implement analytics tracking
- Add loading states everywhere
- Handle edge cases (no internet, server errors, etc.)
