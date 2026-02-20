# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PriceMatch AI is an AI-powered fashion discovery and shopping assistant iOS app that helps users find affordable alternatives to clothing and shoes, get personalized style advice, and manage their wardrobe.

### MVP Features (Phase 1)

1. **Visual Search** - Take photos of clothing/shoes and find similar or cheaper alternatives using Google Gemini Vision
2. **Thorough Product Descriptions** - Detailed analysis of each item including style, material, features, and price comparison
3. **Personalized Recommendations** - Track user preferences and search history to suggest clothing they'll love
4. **Affiliate Shopping** - Direct purchase links with affiliate marketing integration
5. **User Accounts** - Save search history, favorites, and personalized feed
6. **Subscription Model** - Stripe integration: $3.49/month or $39.99/year

### Future Features (Post-MVP)

- **AI Fashion Chatbot** - Versatile assistant for fashion advice, trend insights, and influencer recommendations
- **Smart Wardrobe** - Photograph wardrobe and get AI-generated outfit suggestions by occasion

### Directory Structure

- `backend/` - Backend API services (user auth, data storage, Google Gemini integration, affiliate links)
- `iOS/` - SwiftUI iOS application with camera, image processing, and UI
- `prompts/` - Google Gemini prompt templates for fashion queries, image analysis, and wardrobe suggestions
- `docs/` - API documentation, architecture diagrams, and user guides
- `antigravity/` - Project planning, feature specifications, and design documents

**Note:** This is a greenfield project currently in the planning phase.

## Development Commands

### Backend
*To be added as backend is implemented:*
- Setup: Environment configuration, Google Gemini API keys, Stripe keys
- Run: Development server startup
- Test: API endpoint testing, integration tests
- Database: Migration and seeding commands

### iOS
*To be added as iOS app is implemented:*
- Build: Xcode build commands or SwiftUI preview
- Run: Simulator/device deployment
- Test: XCTest suite execution
- Archive: App Store build preparation

### Common
- Linting: Swift and backend code formatting
- Deploy: Staging and production deployment procedures

## Architecture

### Backend API
**MVP Endpoints:**
- `/auth` - User registration, login, session management
- `/search/image` - Visual search with clothing/shoe images
- `/recommendations` - Personalized clothing suggestions based on user history
- `/products` - Product data with affiliate links
- `/subscription` - Stripe payment processing

**Future Endpoints:**
- `/chat` - Fashion chatbot interactions (post-MVP)
- `/wardrobe` - Wardrobe analysis (post-MVP)

### iOS App (MVP)
- Architecture: MVVM pattern with SwiftUI
- Camera integration for clothing/shoe capture
- Image preprocessing before sending to backend
- Depop-style product grid (thumbnail, detailed description, similarity %, price)
- User profile and search history management
- Personalized recommendations feed
- Subscription paywall and management

### AI Integration (MVP)
- Google Gemini Vision API for image analysis and similarity matching
- Custom prompts in `/prompts` directory for:
  - Detailed clothing identification (style, brand, material, features)
  - Price/quality comparison analysis
  - Search query generation for product matching
  - Thorough item descriptions for results

**Post-MVP:**
- Google Gemini for conversational fashion chatbot
- Wardrobe outfit generation

### Data Flow (MVP)
1. User captures image → iOS app → Backend → Google Gemini Vision → Detailed analysis → Product matching → Results with thorough descriptions, similarity %, and affiliate links
2. User browsing patterns → Backend analytics → Recommendation engine → Personalized "For You" feed
3. User favorites/saves → Stored preferences → Enhanced recommendations over time

## Important Notes

### API Keys & Security
- Google Gemini API keys must be stored securely (environment variables, never in code)
- Stripe API keys (test and production) require secure handling
- User data and search history must comply with privacy regulations
- Affiliate marketing disclosure required in UI per FTC guidelines

### Key Technical Decisions to Make
- Backend framework: Node.js/Express, Python/Flask, or Swift Vapor
- Database: PostgreSQL, MongoDB, or Firebase for user data and history
- Image storage: AWS S3, Google Cloud Storage, or Firebase Storage
- Caching strategy for product results and AI responses
- Rate limiting for Google Gemini API calls to manage costs

### MVP Product Requirements
- Results must show detailed descriptions with similarity percentage (like Depop)
- Visual search with thorough AI-generated item analysis
- Each result includes: thumbnail, brand, style, material, features, price comparison, similarity %
- Subscription paywall: $3.49/month or $39.99/year
- Affiliate link tracking and attribution
- Free tier: 5-10 searches/day
- Premium tier: Unlimited searches + personalized recommendations

### MVP Development Priorities
1. User authentication and data persistence
2. Google Gemini Vision integration for image analysis
3. Visual search with detailed product descriptions
4. iOS UI with camera functionality and Depop-style results grid
5. Affiliate marketing integration with click tracking
6. Stripe subscription integration
7. Recommendation engine based on user history
8. Polish and App Store launch

### Post-MVP Features
- AI Fashion Chatbot with Google Gemini
- Smart Wardrobe analyzer with outfit suggestions
